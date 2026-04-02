#!/usr/bin/env python3
"""
Review Gate 2.0 - Advanced MCP Server with Cursor Integration
Author: Lakshman Turlapati
Provides popup chat, quick input, and file picker tools that automatically trigger Cursor extension.

Requirements:
- mcp>=1.9.2 (latest stable version)
- Python 3.8+
"""

import asyncio
import json
import sys
import logging
import os
import time
import uuid
import glob
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

# Speech-to-text imports
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    ListToolsRequest,
    TextContent,
    Tool,
    CallToolResult,
    Resource,
    ImageContent,
    EmbeddedResource,
)

# Cross-platform temp directory helper
def get_temp_path(filename: str) -> str:
    """Get cross-platform temporary file path"""
    # Use /tmp/ for macOS and Linux, system temp for Windows
    if os.name == 'nt':  # Windows
        temp_dir = tempfile.gettempdir()
    else:  # macOS and Linux
        temp_dir = '/tmp'
    return os.path.join(temp_dir, filename)


SESSION_FILE_NAMES = {
    "trigger": "review_gate_trigger_{trigger_id}.json",
    "ack": "review_gate_ack_{trigger_id}.json",
    "response": "review_gate_response_{trigger_id}.json",
    "speech_trigger": "review_gate_speech_trigger_{trigger_id}.json",
    "speech_response": "review_gate_speech_response_{trigger_id}.json",
}


def _session_file(kind: str, trigger_id: str) -> Path:
    """Return the canonical session-scoped IPC path for a trigger."""
    return Path(get_temp_path(SESSION_FILE_NAMES[kind].format(trigger_id=trigger_id)))


def _session_glob(kind: str) -> str:
    """Return a glob pattern for session-scoped IPC files of a given kind."""
    return str(_session_file(kind, "*"))


def _session_trigger_id_from_path(kind: str, file_path: Path) -> Optional[str]:
    """Extract a trigger_id from a session-scoped file path."""
    template = SESSION_FILE_NAMES[kind]
    prefix, suffix = template.split("{trigger_id}")
    file_name = file_path.name

    if not file_name.startswith(prefix) or (suffix and not file_name.endswith(suffix)):
        return None

    end_index = len(file_name) - len(suffix) if suffix else len(file_name)
    return file_name[len(prefix):end_index]


def _audio_file_matches_trigger(audio_file: str, trigger_id: str) -> bool:
    """Validate that an audio file belongs to the same trigger-scoped speech session."""
    return Path(audio_file).name.startswith(f"review_gate_audio_{trigger_id}_")

# Configure logging with immediate flush
log_file_path = get_temp_path('review_gate_v2.log')

# Create handlers separately to handle Windows file issues
handlers = []
try:
    # File handler - may fail on Windows if file is locked
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    handlers.append(file_handler)
except Exception as e:
    # If file logging fails, just use stderr
    print(f"Warning: Could not create log file: {e}", file=sys.stderr)

# Always add stderr handler
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.INFO)
handlers.append(stderr_handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)
logger.info(f"🔧 Log file path: {log_file_path}")

# Force immediate log flushing
for handler in logger.handlers:
    if hasattr(handler, 'flush'):
        handler.flush()

class ReviewGateServer:
    def __init__(self):
        self.server = Server("review-gate-v2")
        self.setup_handlers()
        self.shutdown_requested = False
        self.shutdown_reason = ""
        self._last_attachments = []
        self._last_session_outcome = {"status": "idle", "message": ""}
        self._last_acknowledgement_outcome = {"status": "idle", "message": ""}
        self._whisper_model = None
        
        # Initialize Whisper model with comprehensive error handling
        self._whisper_error = None
        if WHISPER_AVAILABLE:
            self._whisper_model = self._initialize_whisper_model()
        else:
            logger.warning("⚠️ Faster-Whisper not available - speech-to-text will be disabled")
            logger.warning("💡 To enable speech features, install: pip install faster-whisper")
            self._whisper_error = "faster-whisper package not installed"
            
        # Start speech trigger monitoring
        self._start_speech_monitoring()
        
        logger.info("🚀 Review Gate 2.0 server initialized by Lakshman Turlapati for Cursor integration")
        # Ensure log is written immediately
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()

    def _initialize_whisper_model(self):
        """Initialize Whisper model with comprehensive error handling and fallbacks"""
        try:
            logger.info("🎤 Loading Faster-Whisper model for speech-to-text...")
            
            # Try different model configurations in order of preference
            model_configs = [
                {"model": "base", "device": "cpu", "compute_type": "int8"},
                {"model": "tiny", "device": "cpu", "compute_type": "int8"},
                {"model": "base", "device": "cpu", "compute_type": "float32"},
                {"model": "tiny", "device": "cpu", "compute_type": "float32"},
            ]
            
            for i, config in enumerate(model_configs):
                try:
                    logger.info(f"🔄 Attempting to load {config['model']} model (attempt {i+1}/{len(model_configs)})")
                    model = WhisperModel(config['model'], device=config['device'], compute_type=config['compute_type'])
                    
                    # Test the model with a quick inference to ensure it works
                    logger.info(f"✅ Successfully loaded {config['model']} model with {config['compute_type']}")
                    logger.info(f"📊 Model info - Device: {config['device']}, Compute: {config['compute_type']}")
                    return model
                    
                except Exception as model_error:
                    logger.warning(f"⚠️ Failed to load {config['model']} model: {model_error}")
                    if i == len(model_configs) - 1:
                        # This was the last attempt
                        raise model_error
                    continue
            
        except ImportError as import_error:
            error_msg = f"faster-whisper import failed: {import_error}"
            logger.error(f"❌ {error_msg}")
            self._whisper_error = error_msg
            return None
            
        except Exception as e:
            error_msg = f"Whisper model initialization failed: {e}"
            logger.error(f"❌ {error_msg}")
            
            # Check for common issues and provide specific guidance
            if "CUDA" in str(e):
                logger.error("💡 CUDA issue detected - make sure you have CPU-only version")
                logger.error("💡 Try: pip uninstall faster-whisper && pip install faster-whisper")
                error_msg += " (CUDA compatibility issue)"
            elif "Visual Studio" in str(e) or "MSVC" in str(e):
                logger.error("💡 Visual C++ issue detected on Windows")
                logger.error("💡 Install Visual Studio Build Tools or use pre-built wheels")
                error_msg += " (Visual C++ dependency missing)"
            elif "Permission" in str(e):
                logger.error("💡 Permission issue - check file access and antivirus")
                error_msg += " (Permission denied)"
            elif "disk space" in str(e).lower() or "no space" in str(e).lower():
                logger.error("💡 Disk space issue - whisper models require storage")
                error_msg += " (Insufficient disk space)"
            
            self._whisper_error = error_msg
            return None

    def _clear_last_attachments(self):
        """Reset attachment state for any non-response outcome."""
        self._last_attachments = []

    def _set_session_outcome(self, status: str, message: str = "", **extra: Any) -> Dict[str, Any]:
        outcome = {"status": status, "message": message, **extra}
        self._last_session_outcome = outcome
        if status != "response":
            self._clear_last_attachments()
        return outcome

    def _set_acknowledgement_outcome(self, status: str, message: str = "", **extra: Any) -> Dict[str, Any]:
        outcome = {"status": status, "message": message, **extra}
        self._last_acknowledgement_outcome = outcome
        return outcome

    def _format_session_outcome_text(self, outcome: Optional[Dict[str, Any]], default_timeout_message: str) -> str:
        outcome = outcome or {}
        status = str(outcome.get("status", "error")).strip().lower()
        message = str(outcome.get("message") or "").strip()
        event_type = str(outcome.get("event_type") or "").strip()

        if status == "busy":
            prefix = "BUSY"
            if not message:
                message = "Review Gate popup is already handling another active session."
        elif status == "timeout":
            prefix = "TIMEOUT"
            if not message:
                message = default_timeout_message
        else:
            prefix = "ERROR"
            if not message:
                if status == "cancelled":
                    message = "Review Gate popup was cancelled before the user responded."
                else:
                    message = "Review Gate popup failed before the user response could be collected."

        if event_type and event_type.startswith("SESSION_") and event_type not in message:
            message = f"{message} ({event_type})"

        return f"{prefix}: {message}"

    def _cleanup_stale_session_files(self, max_age_seconds: int = 600) -> int:
        """Remove abandoned session-owned IPC files before they can be reused."""
        cutoff = time.time() - max_age_seconds
        removed_count = 0

        for kind in SESSION_FILE_NAMES:
            for temp_file in glob.glob(_session_glob(kind)):
                temp_path = Path(temp_file)
                try:
                    if not temp_path.exists() or temp_path.stat().st_mtime >= cutoff:
                        continue

                    temp_path.unlink()
                    removed_count += 1
                    logger.info(f"🧹 Removed stale {kind} file: {temp_path.name}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Could not clean up stale {kind} file {temp_path}: {cleanup_error}")

        audio_pattern = os.path.join(get_temp_path(""), "review_gate_audio_*.wav")
        for audio_file in glob.glob(audio_pattern):
            audio_path = Path(audio_file)
            try:
                if not audio_path.exists() or audio_path.stat().st_mtime >= cutoff:
                    continue

                audio_path.unlink()
                removed_count += 1
                logger.info(f"🧹 Removed stale audio file: {audio_path.name}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Could not clean up stale audio file {audio_path}: {cleanup_error}")

        return removed_count

    def setup_handlers(self):
        """Set up MCP request handlers"""
        
        @self.server.list_tools()
        async def list_tools():
            """List available Review Gate tools for Cursor Agent"""
            logger.info("🔧 Cursor Agent requesting available tools")
            tools = [
                Tool(
                    name="review_gate_chat",
                    description="Open Review Gate chat popup in Cursor for feedback and reviews. Use this when you need user input, feedback, or review from the human user. The popup will appear in Cursor and wait for user response for up to 5 minutes.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message to display in the Review Gate popup - this is what the user will see",
                                "default": "Please provide your review or feedback:"
                            },
                            "title": {
                                "type": "string", 
                                "description": "Title for the Review Gate popup window",
                                "default": "Review Gate V2 - ゲート"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context about what needs review (code, implementation, etc.)",
                                "default": ""
                            },
                            "urgent": {
                                "type": "boolean",
                                "description": "Whether this is an urgent review request",
                                "default": False
                            }
                        }
                    }
                )
            ]
            logger.info(f"✅ Listed {len(tools)} Review Gate tools for Cursor Agent")
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Handle tool calls from Cursor Agent with immediate activation"""
            logger.info(f"🎯 CURSOR AGENT CALLED TOOL: {name}")
            logger.info(f"📋 Tool arguments: {arguments}")
            
            # Add processing delay to ensure proper handling
            await asyncio.sleep(0.5)  # Wait 500ms for proper processing
            logger.info(f"⚙️ Processing tool call: {name}")
            
            # Immediately log that we're processing
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            try:
                if name == "review_gate_chat":
                    return await self._handle_review_gate_chat(arguments)
                else:
                    logger.error(f"❌ Unknown tool: {name}")
                    # Wait before returning error
                    await asyncio.sleep(1.0)  # Wait 1 second before error response
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"💥 Tool call error for {name}: {e}")
                # Wait before returning error
                await asyncio.sleep(1.0)  # Wait 1 second before error response
                return [TextContent(type="text", text=f"ERROR: Tool {name} failed: {str(e)}")]

    async def _handle_unified_review_gate(self, args: dict) -> list[TextContent]:
        """Handle unified Review Gate tool for all user interaction needs"""
        message = args.get("message", "Please provide your input:")
        title = args.get("title", "Review Gate ゲート v2")
        context = args.get("context", "")
        mode = args.get("mode", "chat")
        urgent = args.get("urgent", False)
        timeout = args.get("timeout", 300)  # Default 5 minutes
        
        logger.info(f"🎯 UNIFIED Review Gate activated - Mode: {mode}")
        logger.info(f"📝 Title: {title}")
        logger.info(f"📄 Message: {message}")
        logger.info(f"⏱️ Timeout: {timeout}s")
        
        # Create trigger file for Cursor extension IMMEDIATELY
        trigger_id = f"unified_{mode}_{int(time.time() * 1000)}"
        
        # Adapt the tool name based on mode for compatibility
        tool_name = "review_gate"
        if mode == "quick":
            tool_name = "quick_review"
        elif mode == "file":
            tool_name = "file_review"
        elif mode == "ingest":
            tool_name = "ingest_text"
        elif mode == "confirm":
            tool_name = "shutdown_mcp"
        
        # Force immediate trigger creation
        success = await self._trigger_cursor_popup_immediately({
            "tool": tool_name,
            "message": message,
            "title": title,
            "context": context,
            "urgent": urgent,
            "mode": mode,
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True,
            "unified_tool": True
        })
        
        if success:
            logger.info(f"🔥 UNIFIED POPUP TRIGGERED - waiting for user input (trigger_id: {trigger_id}, mode: {mode})")
            
            # Wait for user input with specified timeout
            user_input = await self._wait_for_user_input(trigger_id, timeout=timeout)
            
            if user_input:
                # Return user input directly to MCP client with mode context
                logger.info(f"✅ RETURNING USER INPUT TO MCP CLIENT: {user_input[:100]}...")
                result_message = f"✅ User Response (Mode: {mode})\n\n"
                result_message += f"💬 Input: {user_input}\n"
                result_message += f"📝 Request: {message}\n"
                result_message += f"📍 Context: {context}\n"
                result_message += f"⚙️ Mode: {mode}\n"
                result_message += f"🚨 Urgent: {urgent}\n\n"
                result_message += f"🎯 User interaction completed successfully via unified Review Gate tool."
                
                return [TextContent(type="text", text=result_message)]
            else:
                response = f"TIMEOUT: No user input received within {timeout} seconds (Mode: {mode})"
                logger.warning(f"⚠️ Unified Review Gate timed out waiting for user input after {timeout} seconds")
                return [TextContent(type="text", text=response)]
        else:
            response = f"ERROR: Failed to trigger unified Review Gate popup (Mode: {mode})"
            return [TextContent(type="text", text=response)]

    async def _handle_review_gate_chat(self, args: dict) -> list[TextContent]:
        """Handle Review Gate chat popup and wait for user input with 5 minute timeout"""
        message = args.get("message", "Please provide your review or feedback:")
        title = args.get("title", "Review Gate V2 - ゲート")
        context = args.get("context", "")
        urgent = args.get("urgent", False)
        self._clear_last_attachments()
        self._set_session_outcome("pending")
        self._set_acknowledgement_outcome("pending")
        
        logger.info(f"💬 ACTIVATING Review Gate chat popup IMMEDIATELY for Cursor Agent")
        logger.info(f"📝 Title: {title}")
        logger.info(f"📄 Message: {message}")
        
        # Create trigger file for Cursor extension IMMEDIATELY
        trigger_id = f"review_{int(time.time() * 1000)}"  # Use milliseconds for uniqueness
        
        # Force immediate trigger creation with enhanced debugging
        success = await self._trigger_cursor_popup_immediately({
            "tool": "review_gate_chat",
            "message": message,
            "title": title,
            "context": context,
            "urgent": urgent,
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True
        })
        
        try:
            if success:
                logger.info(f"🔥 POPUP TRIGGERED IMMEDIATELY - waiting for user input (trigger_id: {trigger_id})")
                
                # Wait for extension acknowledgement first
                ack_received = await self._wait_for_extension_acknowledgement(trigger_id, timeout=30)
                if ack_received:
                    logger.info("📨 Extension acknowledged popup activation")
                else:
                    response = self._format_session_outcome_text(
                        self._last_acknowledgement_outcome,
                        "Review Gate popup was not acknowledged by the Cursor extension within 30 seconds."
                    )
                    logger.warning(f"⚠️ Review Gate acknowledgement failed: {response}")
                    return [TextContent(type="text", text=response)]
                
                # Wait for user input from the popup with 5 MINUTE timeout
                logger.info("⏳ Waiting for user input for up to 5 minutes...")
                user_input = await self._wait_for_user_input(trigger_id, timeout=300)  # 5 MINUTE timeout
                
                if user_input:
                    # Return user input directly to MCP client
                    logger.info(f"✅ RETURNING USER REVIEW TO MCP CLIENT: {user_input[:100]}...")
                    
                    # Check for images in the last response data
                    response_content = [TextContent(type="text", text=f"User Response: {user_input}")]
                    
                    # If we have stored attachment data, include images
                    if hasattr(self, '_last_attachments') and self._last_attachments:
                        for attachment in self._last_attachments:
                            if attachment.get('mimeType', '').startswith('image/'):
                                try:
                                    image_content = ImageContent(
                                        type="image",
                                        data=attachment['base64Data'],
                                        mimeType=attachment['mimeType']
                                    )
                                    response_content.append(image_content)
                                    logger.info(f"📸 Added image to response: {attachment.get('fileName', 'unknown')}")
                                except Exception as e:
                                    logger.error(f"❌ Error adding image to response: {e}")
                    
                    return response_content

                response = self._format_session_outcome_text(
                    self._last_session_outcome,
                    "No user input received for review gate within 5 minutes."
                )
                logger.warning(f"⚠️ Review Gate session finished without a response: {response}")
                return [TextContent(type="text", text=response)]

            response = f"ERROR: Failed to trigger Review Gate popup"
            logger.error("❌ Failed to trigger Review Gate popup")
            return [TextContent(type="text", text=response)]
        finally:
            self._cleanup_stale_session_files()

    async def _handle_get_user_input(self, args: dict) -> list[TextContent]:
        """Retrieve user input for a specific session-scoped response file"""
        timeout = args.get("timeout", 10)
        trigger_id = str(args.get("trigger_id", "")).strip()

        if not trigger_id:
            logger.warning("⚠️ get_user_input called without trigger_id")
            return [TextContent(type="text", text="ERROR: trigger_id is required for session-scoped user input retrieval.")]
        
        logger.info(f"🔍 CHECKING for user input (timeout: {timeout}s, trigger_id: {trigger_id})")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                user_input = await self._wait_for_user_input(trigger_id, timeout=1)
                if user_input:
                    logger.info(f"✅ RETRIEVED USER INPUT: {user_input[:100]}...")

                    result_message = f"✅ User Input Retrieved\n\n"
                    result_message += f"💬 User Response: {user_input}\n"
                    result_message += f"📁 Source File: {_session_file('response', trigger_id).name}\n"
                    result_message += f"⏰ Retrieved at: {datetime.now().isoformat()}\n\n"
                    result_message += f"🎯 User input successfully captured from Review Gate."

                    return [TextContent(type="text", text=result_message)]

                session_outcome = self._last_session_outcome
                if session_outcome.get("status") in {"busy", "cancelled", "error"}:
                    response = self._format_session_outcome_text(
                        session_outcome,
                        f"No user input found within {timeout} seconds."
                    )
                    return [TextContent(type="text", text=response)]
                
                # Short sleep to avoid excessive CPU usage
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Error in get_user_input loop: {e}")
                await asyncio.sleep(1)
        
        # No input found within timeout
        no_input_message = f"⏰ No user input found within {timeout} seconds\n\n"
        no_input_message += f"🔍 Checked file: {_session_file('response', trigger_id)}\n"
        no_input_message += f"💡 User may not have provided input yet, or the popup may not be active.\n\n"
        no_input_message += f"🎯 Try calling this tool again after the user provides input."
        
        logger.warning(f"⏰ No user input found within {timeout} seconds")
        return [TextContent(type="text", text=no_input_message)]

    async def _handle_quick_review(self, args: dict) -> list[TextContent]:
        """Handle quick review request and wait for response with immediate activation"""
        prompt = args.get("prompt", "Quick feedback needed:")
        context = args.get("context", "")
        
        logger.info(f"⚡ ACTIVATING Quick Review IMMEDIATELY for Cursor Agent: {prompt}")
        
        # Create trigger for quick input IMMEDIATELY
        trigger_id = f"quick_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately({
            "tool": "quick_review",
            "prompt": prompt,
            "context": context,
            "title": "Quick Review - Review Gate v2",
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True
        })
        
        if success:
            logger.info(f"🔥 QUICK POPUP TRIGGERED - waiting for user input (trigger_id: {trigger_id})")
            
            # Wait for quick user input
            user_input = await self._wait_for_user_input(trigger_id, timeout=90)  # 1.5 minute timeout for quick review
            
            if user_input:
                # Return user input directly to MCP client
                logger.info(f"✅ RETURNING QUICK REVIEW TO MCP CLIENT: {user_input}")
                return [TextContent(type="text", text=user_input)]
            else:
                response = f"TIMEOUT: No quick review input received within 1.5 minutes"
                logger.warning("⚠️ Quick review timed out")
                return [TextContent(type="text", text=response)]
        else:
            response = f"ERROR: Failed to trigger quick review popup"
            return [TextContent(type="text", text=response)]

    async def _handle_file_review(self, args: dict) -> list[TextContent]:
        """Handle file review request and wait for file selection with immediate activation"""
        instruction = args.get("instruction", "Please select file(s) for review:")
        file_types = args.get("file_types", ["*"])
        
        logger.info(f"📁 ACTIVATING File Review IMMEDIATELY for Cursor Agent: {instruction}")
        
        # Create trigger for file picker IMMEDIATELY
        trigger_id = f"file_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately({
            "tool": "file_review",
            "instruction": instruction,
            "file_types": file_types,
            "title": "File Review - Review Gate v2",
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True
        })
        
        if success:
            logger.info(f"🔥 FILE POPUP TRIGGERED - waiting for selection (trigger_id: {trigger_id})")
            
            # Wait for file selection
            user_input = await self._wait_for_user_input(trigger_id, timeout=90)  # 1.5 minute timeout
            
            if user_input:
                response = f"📁 File Review completed!\n\n**Selected Files:** {user_input}\n\n**Instruction:** {instruction}\n**Allowed Types:** {', '.join(file_types)}\n\nYou can now proceed to analyze the selected files."
                logger.info(f"✅ FILES SELECTED: {user_input}")
            else:
                response = f"⏰ File Review timed out.\n\n**Instruction:** {instruction}\n\nNo files selected within 1.5 minutes. Try again or proceed with current workspace files."
                logger.warning("⚠️ File review timed out")
        else:
            response = f"⚠️ File Review trigger failed. Manual activation may be needed."
        
        logger.info("🏁 File review processing complete")
        return [TextContent(type="text", text=response)]

    async def _handle_ingest_text(self, args: dict) -> list[TextContent]:
        """
        Handle text ingestion with immediate activation and user input capture
        """
        text_content = args.get("text_content", "")
        source = args.get("source", "extension")
        context = args.get("context", "")
        processing_mode = args.get("processing_mode", "immediate")
        
        logger.info(f"🚀 ACTIVATING ingest_text IMMEDIATELY for Cursor Agent: {text_content[:100]}...")
        logger.info(f"📍 Source: {source}, Context: {context}, Mode: {processing_mode}")
        
        # Create trigger for ingest_text IMMEDIATELY (consistent with other tools)
        trigger_id = f"ingest_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately({
            "tool": "ingest_text",
            "text_content": text_content,
            "source": source,
            "context": context,
            "processing_mode": processing_mode,
            "title": "Text Ingestion - Review Gate v2",
            "message": f"Text to process: {text_content}",
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True
        })
        
        if success:
            logger.info(f"🔥 INGEST POPUP TRIGGERED - waiting for user input (trigger_id: {trigger_id})")
            
            # Wait for user input with appropriate timeout
            user_input = await self._wait_for_user_input(trigger_id, timeout=120)  # 2 minute timeout
            
            if user_input:
                # Return the user input for further processing
                result_message = f"✅ Text ingestion completed!\n\n"
                result_message += f"📝 Original Text: {text_content}\n"
                result_message += f"💬 User Response: {user_input}\n"
                result_message += f"📍 Source: {source}\n"
                result_message += f"💭 Context: {context}\n"
                result_message += f"⚙️ Processing Mode: {processing_mode}\n\n"
                result_message += f"🎯 The text has been processed and user feedback collected successfully."
                
                logger.info(f"✅ INGEST SUCCESS: User provided feedback for text ingestion")
                return [TextContent(type="text", text=result_message)]
            else:
                result_message = f"⏰ Text ingestion timed out.\n\n"
                result_message += f"📝 Text Content: {text_content}\n"
                result_message += f"📍 Source: {source}\n\n"
                result_message += f"No user response received within 2 minutes. The text content is noted but no additional processing occurred."
                
                logger.warning("⚠️ Text ingestion timed out")
                return [TextContent(type="text", text=result_message)]
        else:
            result_message = f"⚠️ Text ingestion trigger failed.\n\n"
            result_message += f"📝 Text Content: {text_content}\n"
            result_message += f"Manual activation may be needed."
            
            logger.error("❌ Failed to trigger text ingestion popup")
            return [TextContent(type="text", text=result_message)]

    async def _handle_shutdown_mcp(self, args: dict) -> list[TextContent]:
        """Handle shutdown_mcp request and wait for confirmation with immediate activation"""
        reason = args.get("reason", "Task completed successfully")
        immediate = args.get("immediate", False)
        cleanup = args.get("cleanup", True)
        
        logger.info(f"🛑 ACTIVATING shutdown_mcp IMMEDIATELY for Cursor Agent: {reason}")
        
        # Create trigger for shutdown_mcp IMMEDIATELY
        trigger_id = f"shutdown_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately({
            "tool": "shutdown_mcp",
            "reason": reason,
            "immediate": immediate,
            "cleanup": cleanup,
            "title": "Shutdown - Review Gate v2",
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True
        })
        
        if success:
            logger.info(f"🛑 SHUTDOWN TRIGGERED - waiting for confirmation (trigger_id: {trigger_id})")
            
            # Wait for confirmation
            user_input = await self._wait_for_user_input(trigger_id, timeout=60)  # 1 minute timeout for shutdown confirmation
            
            if user_input:
                # Check if user confirmed shutdown
                if user_input.upper().strip() in ['CONFIRM', 'YES', 'Y', 'SHUTDOWN', 'PROCEED']:
                    self.shutdown_requested = True
                    self.shutdown_reason = f"User confirmed: {user_input.strip()}"
                    response = f"🛑 shutdown_mcp CONFIRMED!\n\n**User Confirmation:** {user_input}\n\n**Reason:** {reason}\n**Immediate:** {immediate}\n**Cleanup:** {cleanup}\n\n✅ MCP server will now shut down gracefully..."
                    logger.info(f"✅ SHUTDOWN CONFIRMED BY USER: {user_input[:100]}...")
                    logger.info(f"🛑 Server shutdown initiated - reason: {self.shutdown_reason}")
                else:
                    response = f"💡 shutdown_mcp CANCELLED - Alternative instructions received!\n\n**User Response:** {user_input}\n\n**Original Reason:** {reason}\n\nShutdown cancelled. User provided alternative instructions instead of confirmation."
                    logger.info(f"💡 SHUTDOWN CANCELLED - user provided alternative: {user_input[:100]}...")
            else:
                response = f"⏰ shutdown_mcp timed out.\n\n**Reason:** {reason}\n\nNo response received within 1 minute. Shutdown cancelled due to timeout."
                logger.warning("⚠️ Shutdown timed out - shutdown cancelled")
        else:
            response = f"⚠️ shutdown_mcp trigger failed. Manual activation may be needed."
        
        logger.info("🏁 shutdown_mcp processing complete")
        return [TextContent(type="text", text=response)]

    async def _wait_for_extension_acknowledgement(self, trigger_id: str, timeout: int = 30) -> bool:
        """Wait for extension acknowledgement that popup was activated"""
        ack_file = _session_file("ack", trigger_id)
        self._set_acknowledgement_outcome("pending")
        
        logger.info(f"🔍 Monitoring for extension acknowledgement: {ack_file}")
        
        start_time = time.time()
        check_interval = 0.1  # Check every 100ms for fast response
        
        while time.time() - start_time < timeout:
            try:
                if ack_file.exists():
                    try:
                        data = json.loads(ack_file.read_text())
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid acknowledgement JSON for {trigger_id}: {e}")
                        try:
                            ack_file.unlink()
                        except Exception:
                            pass
                        await asyncio.sleep(check_interval)
                        continue

                    ack_trigger_id = data.get("trigger_id", "")
                    if ack_trigger_id and ack_trigger_id != trigger_id:
                        logger.warning(f"⚠️ Removing mismatched acknowledgement envelope for {ack_trigger_id}")
                        try:
                            ack_file.unlink()
                        except Exception:
                            pass
                        await asyncio.sleep(check_interval)
                        continue

                    ack_status = str(data.get("status", "")).strip().lower()
                    ack_message = str(data.get("message") or "").strip()
                    acknowledged = bool(data.get("acknowledged", False))

                    try:
                        ack_file.unlink()
                        logger.info(f"🧹 Acknowledgement file cleaned up")
                    except Exception:
                        pass
                    
                    if ack_status in {"busy", "cancelled", "error"}:
                        if not ack_message:
                            if ack_status == "busy":
                                ack_message = "Review Gate popup is already handling another active session."
                            elif ack_status == "cancelled":
                                ack_message = "Review Gate popup was cancelled before it could be acknowledged."
                            else:
                                ack_message = "Review Gate popup acknowledgement failed."

                        self._set_acknowledgement_outcome(
                            ack_status,
                            ack_message,
                            owner_trigger_id=data.get("owner_trigger_id"),
                            event_type=str(data.get("event_type") or "").strip()
                        )
                        logger.warning(f"⚠️ Extension rejected popup activation for {trigger_id}: {ack_message}")
                        return False

                    if acknowledged:
                        self._set_acknowledgement_outcome("acknowledged", ack_message)
                        logger.info(f"📨 EXTENSION ACKNOWLEDGED popup activation for trigger {trigger_id}")
                        return True

                    if ack_status:
                        self._set_acknowledgement_outcome(
                            "error",
                            ack_message or f"Extension returned acknowledgement status '{ack_status}'."
                        )
                        return False
                    
                # Check frequently for faster response
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error reading acknowledgement file: {e}")
                await asyncio.sleep(0.5)
        
        logger.warning(f"⏰ TIMEOUT waiting for extension acknowledgement (trigger_id: {trigger_id})")
        self._set_acknowledgement_outcome(
            "timeout",
            f"Review Gate popup was not acknowledged by the Cursor extension within {timeout} seconds."
        )
        return False

    async def _wait_for_user_input(self, trigger_id: str, timeout: int = 120) -> Optional[str]:
        """Wait for user input from the Cursor extension popup for a single session file."""
        response_patterns = [_session_file("response", trigger_id)]
        self._set_session_outcome("pending")
        
        logger.info(f"👁️ Monitoring for response files: {[str(p) for p in response_patterns]}")
        logger.info(f"🔍 Trigger ID: {trigger_id}")
        
        start_time = time.time()
        check_interval = 0.1  # Check every 100ms for faster response
        
        while time.time() - start_time < timeout:
            try:
                # Check all possible response file patterns
                for response_file in response_patterns:
                    if response_file.exists():
                        try:
                            file_content = response_file.read_text().strip()
                            logger.info(f"📄 Found response file {response_file}: {file_content[:200]}...")
                            
                            # Handle JSON format
                            if file_content.startswith('{'):
                                try:
                                    data = json.loads(file_content)
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ JSON decode error in {response_file}: {e}")
                                    self._last_attachments = []
                                    try:
                                        response_file.unlink()
                                    except Exception:
                                        pass
                                    continue

                                user_input = data.get("user_input", data.get("response", data.get("message", ""))).strip()
                                attachments = data.get("attachments", [])
                                
                                # Also check if trigger_id matches (if specified)
                                response_trigger_id = data.get("trigger_id", "")
                                if response_trigger_id and response_trigger_id != trigger_id:
                                    logger.warning(f"⚠️ Removing mismatched response envelope: expected {trigger_id}, got {response_trigger_id}")
                                    self._last_attachments = []
                                    try:
                                        response_file.unlink()
                                        logger.info(f"🧹 Removed mismatched response file: {response_file}")
                                    except Exception as cleanup_error:
                                        logger.warning(f"⚠️ Cleanup error for mismatched response: {cleanup_error}")
                                    continue

                                response_status = str(data.get("status", "")).strip().lower()
                                event_type = str(data.get("event_type", "")).strip()
                                response_message = str(data.get("message") or data.get("error") or "").strip()

                                if not response_status and event_type == "SESSION_BUSY":
                                    response_status = "busy"
                                elif not response_status and event_type == "SESSION_CANCELLED":
                                    response_status = "cancelled"

                                if response_status in {"busy", "cancelled", "error"}:
                                    if not response_message:
                                        if response_status == "busy":
                                            response_message = "Review Gate popup is already handling another active session."
                                        elif response_status == "cancelled":
                                            response_message = "Review Gate popup was closed before the user responded."
                                        else:
                                            response_message = "Review Gate popup reported an error before the user responded."

                                    self._set_session_outcome(
                                        response_status,
                                        response_message,
                                        event_type=event_type,
                                        owner_trigger_id=data.get("owner_trigger_id"),
                                        source_file=str(response_file)
                                    )
                                    try:
                                        response_file.unlink()
                                        logger.info(f"🧹 Response outcome file cleaned up: {response_file}")
                                    except Exception as cleanup_error:
                                        logger.warning(f"⚠️ Cleanup error for response outcome: {cleanup_error}")
                                    return None
                                
                                # Process attachments if present
                                if attachments:
                                    logger.info(f"📎 Found {len(attachments)} attachments")
                                    # Store attachments for use in response
                                    self._last_attachments = attachments
                                    attachment_descriptions = []
                                    for att in attachments:
                                        if att.get('mimeType', '').startswith('image/'):
                                            attachment_descriptions.append(f"Image: {att.get('fileName', 'unknown')}")
                                    
                                    if attachment_descriptions:
                                        user_input += f"\n\nAttached: {', '.join(attachment_descriptions)}"
                                else:
                                    self._clear_last_attachments()
                                    
                            # Handle plain text format
                            else:
                                user_input = file_content
                                attachments = []
                                self._clear_last_attachments()
                            
                            # Clean up response file immediately
                            try:
                                response_file.unlink()
                                logger.info(f"🧹 Response file cleaned up: {response_file}")
                            except Exception as cleanup_error:
                                logger.warning(f"⚠️ Cleanup error: {cleanup_error}")
                            
                            if user_input:
                                self._set_session_outcome("response", "User response received", source_file=str(response_file))
                                logger.info(f"🎉 RECEIVED USER INPUT for trigger {trigger_id}: {user_input[:100]}...")
                                return user_input
                            else:
                                self._clear_last_attachments()
                                logger.warning(f"⚠️ Empty user input in file: {response_file}")
                                
                        except Exception as e:
                            self._clear_last_attachments()
                            logger.error(f"❌ Error processing response file {response_file}: {e}")
                
                # Check more frequently for faster response
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in wait loop: {e}")
                await asyncio.sleep(0.5)
        
        self._set_session_outcome("timeout", f"No user input received within {timeout} seconds.")
        logger.warning(f"⏰ TIMEOUT waiting for user input (trigger_id: {trigger_id})")
        return None

    async def _trigger_cursor_popup_immediately(self, data: dict) -> bool:
        """Create trigger file for Cursor extension with immediate activation and enhanced debugging"""
        try:
            self._cleanup_stale_session_files()
            # Add delay before creating trigger to ensure readiness
            await asyncio.sleep(0.1)  # Wait 100ms before trigger creation
            
            trigger_id = data.get("trigger_id")
            if not trigger_id:
                logger.error("❌ Trigger data missing trigger_id")
                return False

            trigger_file = _session_file("trigger", trigger_id)
            for kind in ("ack", "response", "trigger"):
                session_path = _session_file(kind, trigger_id)
                if session_path.exists():
                    try:
                        session_path.unlink()
                        logger.info(f"🧹 Removed stale {kind} file for trigger {trigger_id}")
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ Could not remove stale {kind} file {session_path}: {cleanup_error}")
            
            trigger_data = {
                "timestamp": datetime.now().isoformat(),
                "system": "review-gate-v2",
                "editor": "cursor",
                "data": data,
                "pid": os.getpid(),
                "active_window": True,
                "mcp_integration": True,
                "immediate_activation": True
            }
            
            logger.info(f"🎯 CREATING trigger file with data: {json.dumps(trigger_data, indent=2)}")
            
            # Write trigger file with immediate flush
            trigger_file.write_text(json.dumps(trigger_data, indent=2))
            
            # Verify file was written successfully
            if not trigger_file.exists():
                logger.error(f"❌ Failed to create trigger file: {trigger_file}")
                return False
                
            try:
                file_size = trigger_file.stat().st_size
                if file_size == 0:
                    logger.error(f"❌ Trigger file is empty: {trigger_file}")
                    return False
            except FileNotFoundError:
                # File may have been consumed by the extension already - this is OK
                logger.info(f"✅ Trigger file was consumed immediately by extension: {trigger_file}")
                file_size = len(json.dumps(trigger_data, indent=2))
            
            # Force file system sync with retry
            for attempt in range(3):
                try:
                    os.sync()
                    break
                except Exception as sync_error:
                    logger.warning(f"⚠️ Sync attempt {attempt + 1} failed: {sync_error}")
                    await asyncio.sleep(0.1)  # Wait 100ms between attempts
            
            logger.info(f"🔥 IMMEDIATE trigger created for Cursor: {trigger_file}")
            logger.info(f"📁 Trigger file path: {trigger_file.absolute()}")
            logger.info(f"📊 Trigger file size: {file_size} bytes")
            
            # Add small delay to allow extension to process
            await asyncio.sleep(0.2)  # Wait 200ms for extension to process
            
            # Note: Trigger file may have been consumed by extension already, which is good!
            try:
                if trigger_file.exists():
                    logger.info(f"✅ Trigger file still exists: {trigger_file}")
                else:
                    logger.info(f"✅ Trigger file was consumed by extension: {trigger_file}")
                    logger.info(f"🎯 This is expected behavior - extension is working properly")
            except Exception as check_error:
                logger.info(f"✅ Cannot check trigger file status (likely consumed): {check_error}")
                logger.info(f"🎯 This is expected behavior - extension is working properly")
            
            # Check if extension might be watching
            log_file = Path(get_temp_path("review_gate_v2.log"))
            if log_file.exists():
                logger.info(f"📝 MCP log file exists: {log_file}")
            else:
                logger.warning(f"⚠️ MCP log file missing: {log_file}")
            
            # Force log flush
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to create Review Gate trigger: {e}")
            import traceback
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            # Wait before returning failure
            await asyncio.sleep(1.0)  # Wait 1 second before confirming failure
            return False

    async def run(self):
        """Run the Review Gate server with immediate activation capability and shutdown monitoring"""
        logger.info("🚀 Starting Review Gate 2.0 MCP Server for IMMEDIATE Cursor integration...")
        
        
        async with stdio_server() as (read_stream, write_stream):
            logger.info("✅ Review Gate v2 server ACTIVE on stdio transport for Cursor")
            
            # Create server run task
            server_task = asyncio.create_task(
                self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
            )
            
            # Create shutdown monitor task
            shutdown_task = asyncio.create_task(self._monitor_shutdown())
            
            # Create heartbeat task to keep log file fresh for extension status monitoring
            heartbeat_task = asyncio.create_task(self._heartbeat_logger())
            
            # Wait for either server completion or shutdown request
            done, pending = await asyncio.wait(
                [server_task, shutdown_task, heartbeat_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            if self.shutdown_requested:
                logger.info(f"🛑 Review Gate v2 server shutting down: {self.shutdown_reason}")
            else:
                logger.info("🏁 Review Gate v2 server completed normally")

    async def _heartbeat_logger(self):
        """Periodically update log file to keep MCP status active in extension"""
        logger.info("💓 Starting heartbeat logger for extension status monitoring")
        heartbeat_count = 0
        
        while not self.shutdown_requested:
            try:
                # Update log every 10 seconds to keep file modification time fresh
                await asyncio.sleep(10)
                heartbeat_count += 1
                
                # Write heartbeat to log
                logger.info(f"💓 MCP heartbeat #{heartbeat_count} - Server is active and ready")
                
                # Force log flush to ensure file is updated
                for handler in logger.handlers:
                    if hasattr(handler, 'flush'):
                        handler.flush()
                        
            except Exception as e:
                logger.error(f"❌ Heartbeat error: {e}")
                await asyncio.sleep(5)
        
        logger.info("💔 Heartbeat logger stopped")
    
    async def _monitor_shutdown(self):
        """Monitor for shutdown requests in a separate task"""
        while not self.shutdown_requested:
            await asyncio.sleep(1)  # Check every second
        
        # Cleanup operations before shutdown
        logger.info("🧹 Performing cleanup operations before shutdown...")
        
        # Clean up any temporary files
        try:
            for kind in ("trigger", "ack", "response", "speech_trigger", "speech_response"):
                for temp_file in glob.glob(_session_glob(kind)):
                    temp_path = Path(temp_file)
                    if temp_path.exists():
                        temp_path.unlink()
                        logger.info(f"🗑️ Cleaned up: {temp_path.name}")
                    
            # Clean up any orphaned audio files (older than 5 minutes)
            import time
            current_time = time.time()
            temp_dir = get_temp_path("")
            audio_pattern = os.path.join(temp_dir, "review_gate_audio_*.wav")
            
            for audio_file in glob.glob(audio_pattern):
                try:
                    file_age = current_time - os.path.getmtime(audio_file)
                    if file_age > 300:  # 5 minutes
                        Path(audio_file).unlink()
                        logger.info(f"🗑️ Cleaned up old audio file: {os.path.basename(audio_file)}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Could not clean up audio file {audio_file}: {cleanup_error}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
        
        logger.info("✅ Cleanup completed - shutdown ready")
        return True

    def _start_speech_monitoring(self):
        """Start monitoring for speech-to-text trigger files with enhanced error handling"""
        self._speech_monitoring_active = False
        self._speech_thread = None
        
        def monitor_speech_triggers():
            """Enhanced speech monitoring with health checks and better error handling"""
            monitor_start_time = time.time()
            processed_count = 0
            error_count = 0
            last_heartbeat = time.time()
            last_cleanup = 0.0
            
            logger.info("🎤 Speech monitoring thread started successfully")
            self._speech_monitoring_active = True
            
            while not self.shutdown_requested:
                try:
                    current_time = time.time()
                    
                    # Heartbeat logging every 60 seconds
                    if current_time - last_heartbeat > 60:
                        uptime = int(current_time - monitor_start_time)
                        logger.info(f"💓 Speech monitor heartbeat - Uptime: {uptime}s, Processed: {processed_count}, Errors: {error_count}")
                        last_heartbeat = current_time

                    if current_time - last_cleanup > 30:
                        self._cleanup_stale_session_files()
                        last_cleanup = current_time
                    
                    # Look for speech trigger files using cross-platform temp path
                    speech_triggers = glob.glob(_session_glob("speech_trigger"))
                    
                    for trigger_file in speech_triggers:
                        try:
                            trigger_path = Path(trigger_file)
                            expected_trigger_id = _session_trigger_id_from_path("speech_trigger", trigger_path)

                            # Validate file exists and is readable
                            if not os.path.exists(trigger_file):
                                continue
                                
                            with open(trigger_file, 'r', encoding='utf-8') as f:
                                trigger_data = json.load(f)

                            request_trigger_id = trigger_data.get('data', {}).get('trigger_id')
                            if expected_trigger_id and request_trigger_id and expected_trigger_id != request_trigger_id:
                                logger.warning(
                                    f"⚠️ Ignoring mismatched speech trigger file {trigger_path.name}: "
                                    f"expected {expected_trigger_id}, got {request_trigger_id}"
                                )
                                trigger_path.unlink()
                                continue
                            
                            if trigger_data.get('data', {}).get('tool') == 'speech_to_text':
                                logger.info(f"🎤 Processing speech-to-text request: {trigger_path.name}")
                                self._process_speech_request(trigger_data)
                                processed_count += 1
                                
                                # Clean up trigger file safely
                                try:
                                    trigger_path.unlink()
                                    logger.debug(f"🗑️ Cleaned up trigger file: {trigger_path.name}")
                                except Exception as cleanup_error:
                                    logger.warning(f"⚠️ Could not clean up trigger file: {cleanup_error}")
                                
                        except json.JSONDecodeError as json_error:
                            logger.error(f"❌ Invalid JSON in speech trigger {trigger_file}: {json_error}")
                            error_count += 1
                            try:
                                Path(trigger_file).unlink()  # Remove invalid file
                            except:
                                pass
                                
                        except Exception as e:
                            logger.error(f"❌ Error processing speech trigger {trigger_file}: {e}")
                            error_count += 1
                            try:
                                Path(trigger_file).unlink()
                            except:
                                pass
                    
                    time.sleep(0.5)  # Check every 500ms
                    
                except Exception as e:
                    logger.error(f"❌ Critical speech monitoring error: {e}")
                    error_count += 1
                    time.sleep(2)  # Longer wait on critical errors
                    
                    # If too many errors, consider restarting
                    if error_count > 10:
                        logger.warning("⚠️ Too many speech monitoring errors - attempting recovery")
                        time.sleep(5)
                        error_count = 0  # Reset error count after recovery pause
            
            self._speech_monitoring_active = False
            logger.info("🛑 Speech monitoring thread stopped")
        
        try:
            # Start monitoring in background thread
            import threading
            self._speech_thread = threading.Thread(target=monitor_speech_triggers, daemon=True)
            self._speech_thread.name = "ReviewGate-SpeechMonitor"
            self._speech_thread.start()
            
            # Verify thread started successfully
            time.sleep(0.1)  # Give thread time to start
            if self._speech_thread.is_alive():
                logger.info("✅ Speech-to-text monitoring started successfully")
            else:
                logger.error("❌ Speech monitoring thread failed to start")
                self._speech_monitoring_active = False
                
        except Exception as e:
            logger.error(f"❌ Failed to start speech monitoring thread: {e}")
            self._speech_monitoring_active = False

    def _process_speech_request(self, trigger_data):
        """Process speech-to-text request"""
        try:
            audio_file = trigger_data.get('data', {}).get('audio_file')
            trigger_id = trigger_data.get('data', {}).get('trigger_id')
            
            if not audio_file or not trigger_id:
                logger.error("❌ Invalid speech request - missing audio_file or trigger_id")
                return
            
            if not self._whisper_model:
                error_detail = self._whisper_error or "Whisper model not available"
                logger.error(f"❌ Whisper model not available: {error_detail}")
                self._write_speech_response(trigger_id, "", f"Speech-to-text unavailable: {error_detail}")
                return
            
            if not os.path.exists(audio_file):
                logger.error(f"❌ Audio file not found: {audio_file}")
                self._write_speech_response(trigger_id, "", "Audio file not found")
                return

            if not _audio_file_matches_trigger(audio_file, trigger_id):
                logger.warning(f"⚠️ Ignoring mismatched audio file for trigger {trigger_id}: {audio_file}")
                self._write_speech_response(trigger_id, "", "Audio file does not belong to the active speech session")
                try:
                    Path(audio_file).unlink()
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Could not clean up mismatched audio file {audio_file}: {cleanup_error}")
                return
            
            logger.info(f"🎤 Transcribing audio: {audio_file}")
            
            # Transcribe audio using Faster-Whisper
            segments, info = self._whisper_model.transcribe(audio_file, beam_size=5)
            transcription = " ".join(segment.text for segment in segments).strip()
            
            logger.info(f"✅ Speech transcribed: '{transcription}'")
            
            # Write response
            self._write_speech_response(trigger_id, transcription)
            
            # Clean up audio file (MCP server is responsible for this)
            try:
                # Small delay to ensure any pending file operations complete
                import time
                time.sleep(0.1)
                
                if Path(audio_file).exists():
                    Path(audio_file).unlink()
                    logger.info(f"🗑️ Cleaned up audio file: {os.path.basename(audio_file)}")
                else:
                    logger.debug(f"Audio file already cleaned up: {os.path.basename(audio_file)}")
            except Exception as e:
                logger.warning(f"⚠️ Could not clean up audio file: {e}")
                
        except Exception as e:
            logger.error(f"❌ Speech transcription failed: {e}")
            trigger_id = trigger_data.get('data', {}).get('trigger_id', 'unknown')
            self._write_speech_response(trigger_id, "", str(e))
        finally:
            self._cleanup_stale_session_files()

    def _write_speech_response(self, trigger_id, transcription, error=None):
        """Write speech-to-text response"""
        try:
            response_data = {
                'timestamp': datetime.now().isoformat(),
                'trigger_id': trigger_id,
                'transcription': transcription,
                'success': error is None,
                'status': 'ok' if error is None else 'error',
                'error': error,
                'source': 'review_gate_whisper'
            }
            
            response_file = _session_file("speech_response", trigger_id)
            with open(response_file, 'w') as f:
                json.dump(response_data, f, indent=2)
            
            logger.info(f"📝 Speech response written: {response_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to write speech response: {e}")

    def get_speech_monitoring_status(self):
        """Get comprehensive status of speech monitoring system"""
        status = {
            "speech_monitoring_active": getattr(self, '_speech_monitoring_active', False),
            "speech_thread_alive": getattr(self, '_speech_thread', None) and self._speech_thread.is_alive(),
            "whisper_model_loaded": self._whisper_model is not None,
            "whisper_error": getattr(self, '_whisper_error', None),
            "faster_whisper_available": WHISPER_AVAILABLE
        }
        
        # Log status if there are issues
        if not status["speech_monitoring_active"]:
            logger.warning("⚠️ Speech monitoring is not active")
        if not status["speech_thread_alive"]:
            logger.warning("⚠️ Speech monitoring thread is not running")
        if not status["whisper_model_loaded"]:
            logger.warning(f"⚠️ Whisper model not loaded: {status['whisper_error']}")
        
        return status

async def main():
    """Main entry point for Review Gate v2 with immediate activation"""
    logger.info("🎬 STARTING Review Gate v2 MCP Server...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"OS name: {os.name}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        server = ReviewGateServer()
        await server.run()
    except Exception as e:
        logger.error(f"❌ Fatal error in MCP server: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server crashed: {e}")
        sys.exit(1) 
