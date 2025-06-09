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
import platform
import threading
import traceback
import io
import codecs
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

try:
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
except ImportError:
    print("Error: MCP package not found. Please install with: pip install mcp")
    sys.exit(1)

# Try to import Whisper for speech-to-text
WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def get_temp_dir():
    """Get platform-appropriate temporary directory"""
    return tempfile.gettempdir()


def get_log_file():
    """Get platform-appropriate log file path"""
    temp_dir = get_temp_dir()
    return os.path.join(temp_dir, "review_gate_v2.log")


def get_temp_file_path(filename):
    """Get platform-appropriate temporary file path"""
    temp_dir = get_temp_dir()
    return os.path.join(temp_dir, filename)


# Configure logging with UTF-8 encoding for Windows compatibility
class UTF8StreamHandler(logging.StreamHandler):
    def __init__(self, stream):
        super().__init__(stream)
        if hasattr(stream, 'buffer'):
            # Wrap the stream buffer with UTF-8 encoding
            self.stream = codecs.getwriter('utf-8')(stream.buffer)
        else:
            self.stream = stream


class UTF8FileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding='utf-8'):
        super().__init__(filename, mode, encoding)


# Configure logging with UTF-8 support
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        UTF8StreamHandler(sys.stderr),
        UTF8FileHandler(get_log_file(), mode="a"),
    ],
)

logger = logging.getLogger("review-gate-v2")

# Force immediate log flushing
for handler in logger.handlers:
    handler.setLevel(logging.INFO)
    if hasattr(handler, "flush"):
        handler.flush()

if WHISPER_AVAILABLE:
    logger.info("✅ Faster-Whisper available for speech-to-text")
else:
    logger.warning("⚠️ Whisper not available - speech-to-text disabled")


class ReviewGateServer:
    def __init__(self):
        self.server = Server("review-gate-v2")
        self.shutdown_requested = False
        self.shutdown_reason = ""
        self._last_attachments = []
        self._whisper_model = None

        # Initialize Whisper model if available
        if WHISPER_AVAILABLE:
            try:
                logger.info("🎤 Loading Faster-Whisper model...")
                self._whisper_model = WhisperModel(
                    "base", device="cpu", compute_type="int8"
                )
                logger.info("✅ Faster-Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load Whisper model: {e}")
                self._whisper_model = None
        else:
            logger.warning("⚠️ Whisper not available")
            self._whisper_model = None

        # Start speech trigger monitoring
        self._start_speech_monitoring()

        # Ensure log is written immediately
        for handler in logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        self.setup_handlers()
        logger.info("🚀 Review Gate 2.0 server initialized for Cursor")

    def setup_handlers(self):
        """Set up MCP request handlers"""

        @self.server.list_tools()
        async def list_tools():
            """List available Review Gate tools for Cursor Agent"""
            logger.info("🔧 Cursor Agent requesting available tools")
            tools = [
                Tool(
                    name="review_gate_chat",
                    description=(
                        "Open Review Gate chat popup in Cursor for "
                        "feedback and reviews. Use this when you need "
                        "user input, feedback, or review from the "
                        "human user. The popup will appear in Cursor "
                        "and wait for user response for up to 5 "
                        "minutes."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": (
                                    "The message to display in "
                                    "the Review Gate popup - this "
                                    "is what the user will see"
                                ),
                                "default": (
                                    "Please provide your review or " "feedback:"
                                ),
                            },
                            "title": {
                                "type": "string",
                                "description": (
                                    "Title for the Review Gate " "popup window"
                                ),
                                "default": "Review Gate V2 - ゲート",
                            },
                            "context": {
                                "type": "string",
                                "description": (
                                    "Additional context about "
                                    "what needs review (code, "
                                    "implementation, etc.)"
                                ),
                                "default": "",
                            },
                            "urgent": {
                                "type": "boolean",
                                "description": (
                                    "Whether this is an urgent " "review request"
                                ),
                                "default": False,
                            },
                        },
                    },
                )
            ]
            logger.info(f"✅ Listed {len(tools)} Review Gate tools")
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Handle tool calls from Cursor Agent with immediate activation"""
            logger.info(f"🎯 CURSOR AGENT CALLED TOOL: {name}")
            logger.info(f"📋 Tool arguments: {arguments}")

            # Add processing delay to ensure proper handling
            await asyncio.sleep(0.5)
            logger.info(f"⚙️ Processing tool call: {name}")

            # Immediately log that we're processing
            for handler in logger.handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

            try:
                if name == "review_gate_chat":
                    return await self._handle_review_gate_chat(arguments)
                else:
                    logger.error(f"❌ Unknown tool: {name}")
                    await asyncio.sleep(1.0)
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"💥 Tool call error for {name}: {e}")
                await asyncio.sleep(1.0)
                return [
                    TextContent(
                        type="text", text=f"ERROR: Tool {name} failed: {str(e)}"
                    )
                ]

    async def _handle_unified_review_gate(self, args: dict) -> list[TextContent]:
        """Handle unified Review Gate tool for all user interaction needs"""
        message = args.get("message", "Please provide your input:")
        title = args.get("title", "Review Gate ゲート v2")
        context = args.get("context", "")
        mode = args.get("mode", "chat")
        urgent = args.get("urgent", False)
        timeout = args.get("timeout", 300)

        logger.info(f"🎯 UNIFIED Review Gate activated - Mode: {mode}")
        logger.info(f"📝 Title: {title}")
        logger.info(f"📄 Message: {message}")
        logger.info(f"⏱️ Timeout: {timeout}s")

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
        success = await self._trigger_cursor_popup_immediately(
            {
                "tool": tool_name,
                "message": message,
                "title": title,
                "context": context,
                "urgent": urgent,
                "mode": mode,
                "trigger_id": trigger_id,
                "timestamp": datetime.now().isoformat(),
                "immediate_activation": True,
                "unified_tool": True,
            }
        )

        if success:
            logger.info(
                f"🔥 UNIFIED POPUP TRIGGERED - waiting for user "
                f"input (trigger_id: {trigger_id}, mode: {mode})"
            )

            # Wait for user input with specified timeout
            user_input = await self._wait_for_user_input(trigger_id, timeout=timeout)

            if user_input:
                logger.info(
                    f"✅ RETURNING USER INPUT TO MCP CLIENT: " f"{user_input[:100]}..."
                )
                result_message = f"✅ User Response (Mode: {mode})\n\n"
                result_message += f"💬 Input: {user_input}\n"
                result_message += f"📝 Request: {message}\n"
                result_message += f"📍 Context: {context}\n"
                result_message += f"⚙️ Mode: {mode}\n"
                result_message += f"🚨 Urgent: {urgent}\n\n"
                result_message += (
                    "🎯 User interaction completed "
                    "successfully via unified Review Gate tool."
                )

                return [TextContent(type="text", text=result_message)]
            else:
                response = (
                    f"TIMEOUT: No user input received within "
                    f"{timeout} seconds (Mode: {mode})"
                )
                logger.warning(
                    f"⚠️ Unified Review Gate timed out waiting "
                    f"for user input after {timeout} seconds"
                )
                return [TextContent(type="text", text=response)]
        else:
            response = (
                f"ERROR: Failed to trigger unified Review Gate " f"popup (Mode: {mode})"
            )
            return [TextContent(type="text", text=response)]

    async def _handle_review_gate_chat(self, args: dict) -> list[TextContent]:
        """Handle Review Gate chat popup and wait for user input"""
        message = args.get("message", "Please provide your review:")
        title = args.get("title", "Review Gate V2 - ゲート")
        context = args.get("context", "")
        urgent = args.get("urgent", False)

        logger.info("💬 ACTIVATING Review Gate chat popup IMMEDIATELY")
        logger.info(f"📝 Title: {title}")
        logger.info(f"📄 Message: {message}")
        logger.info(f"📄 Context: {context}")
        logger.info(f"🚨 Urgent: {urgent}")

        # Create trigger file for Cursor extension IMMEDIATELY
        trigger_id = f"review_{int(time.time() * 1000)}"

        # Force immediate trigger creation
        success = await self._trigger_cursor_popup_immediately(
            {
                "tool": "review_gate_chat",
                "message": message,
                "title": title,
                "context": context,
                "urgent": urgent,
                "trigger_id": trigger_id,
                "timestamp": datetime.now().isoformat(),
                "immediate_activation": True,
            }
        )

        if success:
            logger.info(
                f"🔥 POPUP TRIGGERED IMMEDIATELY - waiting for "
                f"user input (trigger_id: {trigger_id})"
            )

            # Wait for extension acknowledgement first
            ack_received = await self._wait_for_extension_acknowledgement(
                trigger_id, timeout=30
            )
            if ack_received:
                logger.info("📨 Extension acknowledged popup activation")
            else:
                logger.warning("⚠️ No extension acknowledgement received")

            # Wait for user input with 5 MINUTE timeout
            logger.info("⏳ Waiting for user input for up to 5 minutes...")
            user_input = await self._wait_for_user_input(trigger_id, timeout=300)

            if user_input:
                logger.info(
                    f"✅ RETURNING USER REVIEW TO MCP CLIENT: " f"{user_input[:100]}..."
                )

                # Check for images in the last response data
                response_content = [
                    TextContent(type="text", text=f"User Response: {user_input}")
                ]

                # If we have stored attachment data, include images
                if hasattr(self, "_last_attachments") and self._last_attachments:
                    for attachment in self._last_attachments:
                        if attachment.get("mimeType", "").startswith("image/"):
                            try:
                                image_content = ImageContent(
                                    type="image",
                                    data=attachment["base64Data"],
                                    mimeType=attachment["mimeType"],
                                )
                                response_content.append(image_content)
                                logger.info(
                                    "📸 Added image to response: "
                                    f"{attachment.get('fileName', 'unknown')}"
                                )
                            except Exception as e:
                                logger.error(f"❌ Error adding image: {e}")

                return response_content
            else:
                response = (
                    "TIMEOUT: No user input received for review "
                    "gate within 5 minutes"
                )
                logger.warning(
                    "⚠️ Review Gate timed out waiting for " "user input after 5 minutes"
                )
                return [TextContent(type="text", text=response)]
        else:
            response = "ERROR: Failed to trigger Review Gate popup"
            logger.error("❌ Failed to trigger Review Gate popup")
            return [TextContent(type="text", text=response)]

    async def _handle_get_user_input(self, args: dict) -> list[TextContent]:
        """Retrieve user input from any available response files"""
        timeout = args.get("timeout", 10)

        logger.info(f"🔍 CHECKING for user input (timeout: {timeout}s)")

        # Check all possible response file patterns (Windows compatible)
        temp_dir = get_temp_dir()
        response_patterns = [
            os.path.join(temp_dir, "review_gate_response_*.json"),
            os.path.join(temp_dir, "review_gate_response.json"),
            os.path.join(temp_dir, "mcp_response_*.json"),
            os.path.join(temp_dir, "mcp_response.json"),
        ]

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Check all response patterns
                for pattern in response_patterns:
                    matching_files = glob.glob(pattern)
                    for response_file_path in matching_files:
                        response_file = Path(response_file_path)
                        if response_file.exists():
                            try:
                                file_content = response_file.read_text().strip()
                                logger.info(
                                    f"📄 Found response file "
                                    f"{response_file}: "
                                    f"{file_content[:200]}..."
                                )

                                # Handle JSON format
                                if file_content.startswith("{"):
                                    data = json.loads(file_content)
                                    user_input = data.get(
                                        "user_input",
                                        data.get("response", data.get("message", "")),
                                    ).strip()
                                # Handle plain text format
                                else:
                                    user_input = file_content

                                if user_input:
                                    # Clean up response file
                                    try:
                                        response_file.unlink()
                                        logger.info(
                                            "🧹 Response file "
                                            f"cleaned up: {response_file}"
                                        )
                                    except Exception as cleanup_error:
                                        logger.warning(
                                            "⚠️ Cleanup error: " f"{cleanup_error}"
                                        )

                                    logger.info(
                                        "✅ RETRIEVED USER INPUT: "
                                        f"{user_input[:100]}..."
                                    )

                                    result_message = "✅ User Input " "Retrieved\n\n"
                                    result_message += (
                                        "💬 User Response: " f"{user_input}\n"
                                    )
                                    result_message += (
                                        "📁 Source File: " f"{response_file.name}\n"
                                    )
                                    result_message += (
                                        "⏰ Retrieved at: "
                                        f"{datetime.now().isoformat()}\n\n"
                                    )
                                    result_message += (
                                        "🎯 User input "
                                        "successfully captured "
                                        "from Review Gate."
                                    )

                                    return [
                                        TextContent(type="text", text=result_message)
                                    ]

                            except json.JSONDecodeError as e:
                                logger.error(
                                    f"❌ JSON decode error in " f"{response_file}: {e}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"❌ Error processing response "
                                    f"file {response_file}: {e}"
                                )

                # Short sleep to avoid excessive CPU usage
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Error in get_user_input loop: {e}")
                await asyncio.sleep(1)

        # No input found within timeout
        no_input_message = f"⏰ No user input found within {timeout} " "seconds\n\n"
        no_input_message += f"🔍 Checked patterns: {', '.join(response_patterns)}\n"
        no_input_message += (
            "💡 User may not have provided input yet, "
            "or the popup may not be active.\n\n"
        )
        no_input_message += (
            "🎯 Try calling this tool again after the " "user provides input."
        )

        logger.warning(f"⏰ No user input found within {timeout} seconds")
        return [TextContent(type="text", text=no_input_message)]

    async def _handle_quick_review(self, args: dict) -> list[TextContent]:
        """Handle quick review request with immediate activation"""
        prompt = args.get("prompt", "Quick feedback needed:")
        context = args.get("context", "")

        logger.info(f"⚡ ACTIVATING Quick Review IMMEDIATELY: {prompt}")

        # Create trigger for quick input IMMEDIATELY
        trigger_id = f"quick_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately(
            {
                "tool": "quick_review",
                "prompt": prompt,
                "context": context,
                "title": "Quick Review - Review Gate v2",
                "trigger_id": trigger_id,
                "timestamp": datetime.now().isoformat(),
                "immediate_activation": True,
            }
        )

        if success:
            logger.info(
                f"🔥 QUICK POPUP TRIGGERED - waiting for user "
                f"input (trigger_id: {trigger_id})"
            )

            # Wait for quick user input (1.5 minute timeout)
            user_input = await self._wait_for_user_input(trigger_id, timeout=90)

            if user_input:
                logger.info(f"✅ RETURNING QUICK REVIEW: {user_input}")
                return [TextContent(type="text", text=user_input)]
            else:
                response = (
                    "TIMEOUT: No quick review input received " "within 1.5 minutes"
                )
                logger.warning("⚠️ Quick review timed out")
                return [TextContent(type="text", text=response)]
        else:
            response = "ERROR: Failed to trigger quick review popup"
            return [TextContent(type="text", text=response)]

    async def _handle_file_review(self, args: dict) -> list[TextContent]:
        """Handle file review request with immediate activation"""
        instruction = args.get("instruction", "Please select file(s):")
        file_types = args.get("file_types", ["*"])

        logger.info(f"📁 ACTIVATING File Review IMMEDIATELY: {instruction}")

        # Create trigger for file picker IMMEDIATELY
        trigger_id = f"file_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately(
            {
                "tool": "file_review",
                "instruction": instruction,
                "file_types": file_types,
                "title": "File Review - Review Gate v2",
                "trigger_id": trigger_id,
                "timestamp": datetime.now().isoformat(),
                "immediate_activation": True,
            }
        )

        if success:
            logger.info(
                f"🔥 FILE POPUP TRIGGERED - waiting for selection "
                f"(trigger_id: {trigger_id})"
            )

            # Wait for file selection (1.5 minute timeout)
            user_input = await self._wait_for_user_input(trigger_id, timeout=90)

            if user_input:
                response = (
                    f"📁 File Review completed!\n\n"
                    f"**Selected Files:** {user_input}\n\n"
                    f"**Instruction:** {instruction}\n"
                    f"**Allowed Types:** {', '.join(file_types)}\n\n"
                    "You can now proceed to analyze the selected files."
                )
                logger.info(f"✅ FILES SELECTED: {user_input}")
            else:
                response = (
                    f"⏰ File Review timed out.\n\n"
                    f"**Instruction:** {instruction}\n\n"
                    "No files selected within 1.5 minutes. Try again."
                )
                logger.warning("⚠️ File review timed out")
        else:
            response = "⚠️ File Review trigger failed. Manual activation needed."

        logger.info("🏁 File review processing complete")
        return [TextContent(type="text", text=response)]

    async def _handle_ingest_text(self, args: dict) -> list[TextContent]:
        """Handle text ingestion with immediate activation"""
        text_content = args.get("text_content", "")
        source = args.get("source", "extension")
        context = args.get("context", "")
        processing_mode = args.get("processing_mode", "immediate")

        logger.info(
            f"🚀 ACTIVATING ingest_text IMMEDIATELY: " f"{text_content[:100]}..."
        )
        logger.info(
            f"📍 Source: {source}, Context: {context}, " f"Mode: {processing_mode}"
        )

        # Create trigger for ingest_text IMMEDIATELY
        trigger_id = f"ingest_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately(
            {
                "tool": "ingest_text",
                "text_content": text_content,
                "source": source,
                "context": context,
                "processing_mode": processing_mode,
                "title": "Text Ingestion - Review Gate v2",
                "message": f"Text to process: {text_content}",
                "trigger_id": trigger_id,
                "timestamp": datetime.now().isoformat(),
                "immediate_activation": True,
            }
        )

        if success:
            logger.info(
                f"🔥 INGEST POPUP TRIGGERED - waiting for user "
                f"input (trigger_id: {trigger_id})"
            )

            # Wait for user input (2 minute timeout)
            user_input = await self._wait_for_user_input(trigger_id, timeout=120)

            if user_input:
                result_message = "✅ Text ingestion completed!\n\n"
                result_message += f"📝 Original Text: {text_content}\n"
                result_message += f"💬 User Response: {user_input}\n"
                result_message += f"📍 Source: {source}\n"
                result_message += f"💭 Context: {context}\n"
                result_message += f"⚙️ Processing Mode: {processing_mode}\n\n"
                result_message += (
                    "🎯 The text has been processed and "
                    "user feedback collected successfully."
                )

                logger.info("✅ INGEST SUCCESS: User provided feedback")
                return [TextContent(type="text", text=result_message)]
            else:
                result_message = "⏰ Text ingestion timed out.\n\n"
                result_message += f"📝 Text Content: {text_content}\n"
                result_message += f"📍 Source: {source}\n\n"
                result_message += "No user response received within " "2 minutes."

                logger.warning("⚠️ Text ingestion timed out")
                return [TextContent(type="text", text=result_message)]
        else:
            result_message = "⚠️ Text ingestion trigger failed.\n\n"
            result_message += f"📝 Text Content: {text_content}\n"
            result_message += "Manual activation may be needed."

            logger.error("❌ Failed to trigger text ingestion popup")
            return [TextContent(type="text", text=result_message)]

    async def _handle_shutdown_mcp(self, args: dict) -> list[TextContent]:
        """Handle shutdown_mcp request with immediate activation"""
        reason = args.get("reason", "Task completed successfully")
        immediate = args.get("immediate", False)
        cleanup = args.get("cleanup", True)

        logger.info(f"🛑 ACTIVATING shutdown_mcp IMMEDIATELY: {reason}")

        # Create trigger for shutdown_mcp IMMEDIATELY
        trigger_id = f"shutdown_{int(time.time() * 1000)}"
        success = await self._trigger_cursor_popup_immediately(
            {
                "tool": "shutdown_mcp",
                "reason": reason,
                "immediate": immediate,
                "cleanup": cleanup,
                "title": "Shutdown - Review Gate v2",
                "trigger_id": trigger_id,
                "timestamp": datetime.now().isoformat(),
                "immediate_activation": True,
            }
        )

        if success:
            logger.info(
                f"🛑 SHUTDOWN TRIGGERED - waiting for confirmation "
                f"(trigger_id: {trigger_id})"
            )

            # Wait for confirmation (1 minute timeout)
            user_input = await self._wait_for_user_input(trigger_id, timeout=60)

            if user_input:
                # Check if user confirmed shutdown
                confirm_words = ["CONFIRM", "YES", "Y", "SHUTDOWN", "PROCEED"]
                if user_input.upper().strip() in confirm_words:
                    self.shutdown_requested = True
                    self.shutdown_reason = f"User confirmed: {user_input.strip()}"
                    response = (
                        f"🛑 shutdown_mcp CONFIRMED!\n\n"
                        f"**User Confirmation:** {user_input}\n\n"
                        f"**Reason:** {reason}\n"
                        f"**Immediate:** {immediate}\n"
                        f"**Cleanup:** {cleanup}\n\n"
                        "✅ MCP server will now shut down gracefully..."
                    )
                    logger.info(
                        f"✅ SHUTDOWN CONFIRMED BY USER: " f"{user_input[:100]}..."
                    )
                    logger.info(
                        f"🛑 Server shutdown initiated - reason: "
                        f"{self.shutdown_reason}"
                    )
                else:
                    response = (
                        f"💡 shutdown_mcp CANCELLED - Alternative "
                        f"instructions received!\n\n"
                        f"**User Response:** {user_input}\n\n"
                        f"**Original Reason:** {reason}\n\n"
                        "Shutdown cancelled. User provided alternative "
                        "instructions instead of confirmation."
                    )
                    logger.info(
                        f"💡 SHUTDOWN CANCELLED - user provided "
                        f"alternative: {user_input[:100]}..."
                    )
            else:
                response = (
                    f"⏰ shutdown_mcp timed out.\n\n"
                    f"**Reason:** {reason}\n\n"
                    "No response received within 1 minute. "
                    "Shutdown cancelled due to timeout."
                )
                logger.warning("⚠️ Shutdown timed out - shutdown cancelled")
        else:
            response = (
                "⚠️ shutdown_mcp trigger failed. Manual activation " "may be needed."
            )

        logger.info("🏁 shutdown_mcp processing complete")
        return [TextContent(type="text", text=response)]

    async def _wait_for_extension_acknowledgement(
        self, trigger_id: str, timeout: int = 30
    ) -> bool:
        """Wait for extension acknowledgement that popup was activated"""
        temp_dir = get_temp_dir()
        ack_file = Path(os.path.join(temp_dir, f"review_gate_ack_{trigger_id}.json"))

        logger.info(f"🔍 Monitoring for extension acknowledgement: {ack_file}")

        start_time = time.time()
        check_interval = 0.1

        while time.time() - start_time < timeout:
            try:
                if ack_file.exists():
                    data = json.loads(ack_file.read_text())
                    ack_status = data.get("acknowledged", False)

                    # Clean up acknowledgement file immediately
                    try:
                        ack_file.unlink()
                        logger.info("🧹 Acknowledgement file cleaned up")
                    except Exception:
                        pass

                    if ack_status:
                        logger.info(
                            f"📨 EXTENSION ACKNOWLEDGED popup "
                            f"activation for trigger {trigger_id}"
                        )
                        return True

                # Check frequently for faster response
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"❌ Error reading acknowledgement file: {e}")
                await asyncio.sleep(0.5)

        logger.warning(
            f"⏰ TIMEOUT waiting for extension acknowledgement "
            f"(trigger_id: {trigger_id})"
        )
        return False

    async def _wait_for_user_input(
        self, trigger_id: str, timeout: int = 120
    ) -> Optional[str]:
        """Wait for user input from the Cursor extension popup"""
        temp_dir = get_temp_dir()
        response_patterns = [
            Path(os.path.join(temp_dir, f"review_gate_response_{trigger_id}.json")),
            Path(os.path.join(temp_dir, "review_gate_response.json")),
            Path(os.path.join(temp_dir, f"mcp_response_{trigger_id}.json")),
            Path(os.path.join(temp_dir, "mcp_response.json")),
        ]

        logger.info(
            f"👁️ Monitoring for response files: "
            f"{[str(p) for p in response_patterns]}"
        )
        logger.info(f"🔍 Trigger ID: {trigger_id}")

        start_time = time.time()
        check_interval = 0.1

        while time.time() - start_time < timeout:
            try:
                # Check all possible response file patterns
                for response_file in response_patterns:
                    if response_file.exists():
                        try:
                            file_content = response_file.read_text().strip()
                            logger.info(
                                f"📄 Found response file "
                                f"{response_file}: "
                                f"{file_content[:200]}..."
                            )

                            # Handle JSON format
                            if file_content.startswith("{"):
                                data = json.loads(file_content)
                                user_input = data.get(
                                    "user_input",
                                    data.get("response", data.get("message", "")),
                                ).strip()
                                attachments = data.get("attachments", [])

                                # Check if trigger_id matches (if specified)
                                response_trigger_id = data.get("trigger_id", "")
                                if (
                                    response_trigger_id
                                    and response_trigger_id != trigger_id
                                ):
                                    logger.info(
                                        f"⚠️ Trigger ID mismatch: "
                                        f"expected {trigger_id}, "
                                        f"got {response_trigger_id}"
                                    )
                                    continue

                                # Process attachments if present
                                if attachments:
                                    logger.info(
                                        f"📎 Found {len(attachments)} " "attachments"
                                    )
                                    # Store attachments for use in response
                                    self._last_attachments = attachments
                                    attachment_descriptions = []
                                    for att in attachments:
                                        if att.get("mimeType", "").startswith("image/"):
                                            desc = f"Image: {att.get('fileName', 'unknown')}"
                                            attachment_descriptions.append(desc)

                                    if attachment_descriptions:
                                        user_input += (
                                            f"\n\nAttached: "
                                            f"{', '.join(attachment_descriptions)}"
                                        )
                                else:
                                    self._last_attachments = []

                            # Handle plain text format
                            else:
                                user_input = file_content
                                self._last_attachments = []

                            # Clean up response file immediately
                            try:
                                response_file.unlink()
                                logger.info(
                                    f"🧹 Response file cleaned up: " f"{response_file}"
                                )
                            except Exception as cleanup_error:
                                logger.warning(f"⚠️ Cleanup error: " f"{cleanup_error}")

                            if user_input:
                                logger.info(
                                    f"🎉 RECEIVED USER INPUT for "
                                    f"trigger {trigger_id}: "
                                    f"{user_input[:100]}..."
                                )
                                return user_input
                            else:
                                logger.warning(
                                    f"⚠️ Empty user input in file: " f"{response_file}"
                                )

                        except json.JSONDecodeError as e:
                            logger.error(
                                f"❌ JSON decode error in " f"{response_file}: {e}"
                            )
                        except Exception as e:
                            logger.error(
                                f"❌ Error processing response file "
                                f"{response_file}: {e}"
                            )

                # Check more frequently for faster response
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"❌ Error in wait loop: {e}")
                await asyncio.sleep(0.5)

        logger.warning(
            f"⏰ TIMEOUT waiting for user input " f"(trigger_id: {trigger_id})"
        )
        return None

    async def _trigger_cursor_popup_immediately(self, data: dict) -> bool:
        """Create trigger file for Cursor extension with immediate activation"""
        try:
            # Add delay before creating trigger to ensure readiness
            await asyncio.sleep(0.1)

            temp_dir = get_temp_dir()
            trigger_file = Path(os.path.join(temp_dir, "review_gate_trigger.json"))

            trigger_data = {
                "timestamp": datetime.now().isoformat(),
                "system": "review-gate-v2",
                "editor": "cursor",
                "data": data,
                "pid": os.getpid(),
                "active_window": True,
                "mcp_integration": True,
                "immediate_activation": True,
            }

            logger.info(
                f"🎯 CREATING trigger file with data: "
                f"{json.dumps(trigger_data, indent=2)}"
            )

            # Write trigger file with immediate flush
            trigger_file.write_text(json.dumps(trigger_data, indent=2))

            # Verify file was written successfully
            if not trigger_file.exists():
                logger.error(f"❌ Failed to create trigger file: " f"{trigger_file}")
                return False

            try:
                file_size = trigger_file.stat().st_size
                if file_size == 0:
                    logger.error(f"❌ Trigger file is empty: {trigger_file}")
                    return False
            except FileNotFoundError:
                # File may have been consumed by the extension already
                logger.info(
                    "✅ Trigger file was consumed immediately "
                    f"by extension: {trigger_file}"
                )
                file_size = len(json.dumps(trigger_data, indent=2))

            # Force file system sync with retry
            for attempt in range(3):
                try:
                    if hasattr(os, "sync"):
                        os.sync()
                    break
                except Exception as sync_error:
                    logger.warning(
                        f"⚠️ Sync attempt {attempt + 1} " f"failed: {sync_error}"
                    )
                    await asyncio.sleep(0.1)

            logger.info(f"🔥 IMMEDIATE trigger created for Cursor: " f"{trigger_file}")
            logger.info(f"📁 Trigger file path: {trigger_file.absolute()}")
            logger.info(f"📊 Trigger file size: {file_size} bytes")

            # Create multiple backup trigger files for reliability
            await self._create_backup_triggers(data)

            # Add small delay to allow extension to process
            await asyncio.sleep(0.2)

            # Check if trigger file was consumed
            try:
                if trigger_file.exists():
                    logger.info(f"✅ Trigger file still exists: " f"{trigger_file}")
                else:
                    logger.info("✅ Trigger file was consumed by extension")
                    logger.info(
                        "🎯 This is expected behavior - "
                        "extension is working properly"
                    )
            except Exception as check_error:
                logger.info(
                    f"✅ Cannot check trigger file status "
                    f"(likely consumed): {check_error}"
                )
                logger.info(
                    "🎯 This is expected behavior - " "extension is working properly"
                )

            # Check if extension might be watching
            log_file = Path(get_log_file())
            if log_file.exists():
                logger.info(f"📝 MCP log file exists: {log_file}")
            else:
                logger.warning(f"⚠️ MCP log file missing: {log_file}")

            # Force log flush
            for handler in logger.handlers:
                if hasattr(handler, "flush"):
                    handler.flush()

            return True

        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to create Review Gate " f"trigger: {e}")
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            await asyncio.sleep(1.0)
            return False

    async def _create_backup_triggers(self, data: dict):
        """Create backup trigger files for better reliability"""
        try:
            temp_dir = get_temp_dir()
            # Create multiple backup trigger files
            for i in range(3):
                backup_trigger = Path(
                    os.path.join(temp_dir, f"review_gate_trigger_{i}.json")
                )
                backup_data = {
                    "backup_id": i,
                    "timestamp": datetime.now().isoformat(),
                    "system": "review-gate-v2",
                    "data": data,
                    "mcp_integration": True,
                    "immediate_activation": True,
                }
                backup_trigger.write_text(json.dumps(backup_data, indent=2))

            logger.info("🔄 Backup trigger files created for reliability")

        except Exception as e:
            logger.warning(f"⚠️ Backup trigger creation failed: {e}")

    async def run(self):
        """Run the Review Gate server with immediate activation capability"""
        logger.info(
            "🚀 Starting Review Gate 2.0 MCP Server for "
            "IMMEDIATE Cursor integration..."
        )

        async with stdio_server() as (read_stream, write_stream):
            logger.info("✅ Review Gate v2 server ACTIVE on stdio transport")

            # Create server run task
            server_task = asyncio.create_task(
                self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
            )

            # Create shutdown monitor task
            shutdown_task = asyncio.create_task(self._monitor_shutdown())

            # Wait for either server completion or shutdown request
            done, pending = await asyncio.wait(
                [server_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            if self.shutdown_requested:
                logger.info(
                    f"🛑 Review Gate v2 server shutting down: "
                    f"{self.shutdown_reason}"
                )
            else:
                logger.info("🏁 Review Gate v2 server completed normally")

    async def _monitor_shutdown(self):
        """Monitor for shutdown requests in a separate task"""
        while not self.shutdown_requested:
            await asyncio.sleep(1)

        # Cleanup operations before shutdown
        logger.info("🧹 Performing cleanup operations before shutdown...")

        # Clean up any temporary files
        try:
            temp_dir = get_temp_dir()
            temp_files = [
                os.path.join(temp_dir, "review_gate_trigger.json"),
                os.path.join(temp_dir, "review_gate_trigger_0.json"),
                os.path.join(temp_dir, "review_gate_trigger_1.json"),
                os.path.join(temp_dir, "review_gate_trigger_2.json"),
            ]
            for temp_file in temp_files:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
                    logger.info(f"🗑️ Cleaned up: {temp_file}")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")

        logger.info("✅ Cleanup completed - shutdown ready")
        return True

    def _start_speech_monitoring(self):
        """Start monitoring for speech-to-text trigger files"""

        def monitor_speech_triggers():
            temp_dir = get_temp_dir()
            while not self.shutdown_requested:
                try:
                    # Look for speech trigger files
                    speech_pattern = os.path.join(
                        temp_dir, "review_gate_speech_trigger_*.json"
                    )
                    speech_triggers = glob.glob(speech_pattern)

                    for trigger_file in speech_triggers:
                        try:
                            with open(trigger_file, "r") as f:
                                trigger_data = json.load(f)

                            if (
                                trigger_data.get("data", {}).get("tool")
                                == "speech_to_text"
                            ):
                                logger.info(
                                    "🎤 Processing speech-to-text "
                                    f"request: {trigger_file}"
                                )
                                self._process_speech_request(trigger_data)

                                # Clean up trigger file
                                Path(trigger_file).unlink()

                        except Exception as e:
                            logger.error(
                                f"❌ Error processing speech trigger "
                                f"{trigger_file}: {e}"
                            )
                            try:
                                Path(trigger_file).unlink()
                            except Exception:
                                pass

                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"❌ Speech monitoring error: {e}")
                    time.sleep(1)

        # Start monitoring in background thread
        speech_thread = threading.Thread(target=monitor_speech_triggers, daemon=True)
        speech_thread.start()
        logger.info("🎤 Speech-to-text monitoring started")

    def _process_speech_request(self, trigger_data):
        """Process speech-to-text request"""
        try:
            audio_file = trigger_data.get("data", {}).get("audio_file")
            trigger_id = trigger_data.get("data", {}).get("trigger_id")

            if not audio_file or not trigger_id:
                logger.error(
                    "❌ Invalid speech request - missing audio_file " "or trigger_id"
                )
                return

            if not self._whisper_model:
                logger.error("❌ Whisper model not available")
                self._write_speech_response(
                    trigger_id, "", "Whisper model not available"
                )
                return

            if not os.path.exists(audio_file):
                logger.error(f"❌ Audio file not found: {audio_file}")
                self._write_speech_response(trigger_id, "", "Audio file not found")
                return

            logger.info(f"🎤 Transcribing audio: {audio_file}")

            # Transcribe audio using Faster-Whisper
            segments, info = self._whisper_model.transcribe(audio_file, beam_size=5)
            transcription = " ".join(segment.text for segment in segments).strip()

            logger.info(f"✅ Speech transcribed: '{transcription}'")

            # Write response
            self._write_speech_response(trigger_id, transcription)

            # Clean up audio file
            try:
                Path(audio_file).unlink()
                logger.info(f"🗑️ Cleaned up audio file: {audio_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not clean up audio file: {e}")

        except Exception as e:
            logger.error(f"❌ Speech transcription failed: {e}")
            trigger_id = trigger_data.get("data", {}).get("trigger_id", "unknown")
            self._write_speech_response(trigger_id, "", str(e))

    def _write_speech_response(self, trigger_id, transcription, error=None):
        """Write speech-to-text response (Windows compatible)"""
        try:
            temp_dir = get_temp_dir()
            response_file = os.path.join(
                temp_dir, f"review_gate_speech_response_{trigger_id}.json"
            )

            response_data = {
                "timestamp": datetime.now().isoformat(),
                "trigger_id": trigger_id,
                "transcription": transcription,
                "success": error is None,
                "error": error,
                "source": "review_gate_whisper",
            }

            with open(response_file, "w") as f:
                json.dump(response_data, f, indent=2)

            logger.info(f"📝 Speech response written: {response_file}")

        except Exception as e:
            logger.error(f"❌ Failed to write speech response: {e}")


async def main():
    """Main entry point for Review Gate v2 with immediate activation"""
    logger.info("🎬 STARTING Review Gate v2 MCP Server...")
    server = ReviewGateServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
