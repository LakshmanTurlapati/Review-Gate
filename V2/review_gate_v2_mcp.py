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
import getpass
import json
import sys
import logging
import os
import shutil
import stat
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


def _sanitize_runtime_component(value: str, fallback: str) -> str:
    """Normalize a runtime path component so both runtimes derive the same subtree."""
    sanitized = "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in str(value or "").strip()
    ).strip("._-")
    return sanitized or fallback


def _runtime_user_id() -> str:
    """Derive a stable user identifier shared with the Cursor extension runtime."""
    for env_key in ("REVIEW_GATE_USER_ID", "USER", "USERNAME"):
        env_value = os.environ.get(env_key, "").strip()
        if env_value:
            return _sanitize_runtime_component(env_value, "unknown-user")

    try:
        return _sanitize_runtime_component(getpass.getuser(), "unknown-user")
    except Exception:
        return "unknown-user"


def _ensure_private_directory(directory_path: Path) -> Path:
    """Create a private runtime directory when the platform supports POSIX permissions."""
    directory_path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt':
        try:
            os.chmod(directory_path, 0o700)
        except OSError:
            pass
    return directory_path


def get_runtime_root() -> Path:
    """Return the Review Gate-owned per-user runtime root under the system temp directory."""
    return _ensure_private_directory(
        Path(get_temp_path("")) / "review-gate-v2" / _runtime_user_id()
    )


def _sessions_root() -> Path:
    """Return the shared session storage root inside the runtime subtree."""
    return _ensure_private_directory(get_runtime_root() / "sessions")


def _session_token(trigger_id: str) -> str:
    """Normalize a trigger identifier before using it as a runtime path segment."""
    return _sanitize_runtime_component(trigger_id, "session")


def _session_dir(trigger_id: str) -> Path:
    """Return the canonical session directory for a trigger."""
    return _ensure_private_directory(_session_path(trigger_id))


def _session_path(trigger_id: str) -> Path:
    """Return the session directory path without creating it."""
    return _sessions_root() / _session_token(trigger_id)


SESSION_FILE_NAMES = {
    "trigger": "review_gate_trigger_{trigger_id}.json",
    "ack": "review_gate_ack_{trigger_id}.json",
    "response": "review_gate_response_{trigger_id}.json",
    "speech_trigger": "review_gate_speech_trigger_{trigger_id}.json",
    "speech_response": "review_gate_speech_response_{trigger_id}.json",
}
IPC_PROTOCOL_VERSION = "review-gate-v2-session-v1"
STATUS_FILE_NAME = "review_gate_status.json"


def _session_file(kind: str, trigger_id: str) -> Path:
    """Return the canonical session-scoped IPC path for a trigger."""
    session_token = _session_token(trigger_id)
    return _session_dir(session_token) / SESSION_FILE_NAMES[kind].format(trigger_id=session_token)


def _session_glob(kind: str) -> str:
    """Return a glob pattern for session-scoped IPC files of a given kind."""
    return str(_sessions_root() / "*" / SESSION_FILE_NAMES[kind].format(trigger_id="*"))


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


def _path_within_runtime_root(candidate_path: Path, runtime_root: Path) -> bool:
    try:
        candidate_path.relative_to(runtime_root)
        return True
    except ValueError:
        return False


def _validate_runtime_path(
    path: Path,
    *,
    expect_file: bool = False,
    expect_directory: bool = False,
    allow_missing: bool = False,
) -> Path:
    runtime_root = get_runtime_root().resolve()
    normalized_path = path.resolve(strict=False)

    if not _path_within_runtime_root(normalized_path, runtime_root):
        raise ValueError(f"Runtime path escapes Review Gate root: {path}")

    chain_target = path
    if allow_missing and not os.path.lexists(str(path)):
        chain_target = path.parent

    current_path = chain_target
    while True:
        if not os.path.lexists(str(current_path)):
            if current_path == path and not allow_missing:
                raise FileNotFoundError(str(path))
        else:
            current_stat = current_path.lstat()
            if stat.S_ISLNK(current_stat.st_mode):
                raise ValueError(f"Refusing symlinked runtime path: {current_path}")
            if current_path == path:
                if expect_file and not stat.S_ISREG(current_stat.st_mode):
                    raise ValueError(f"Refusing non-regular runtime file: {current_path}")
                if expect_directory and not stat.S_ISDIR(current_stat.st_mode):
                    raise ValueError(f"Refusing non-directory runtime path: {current_path}")

        if current_path == runtime_root or current_path == current_path.parent:
            break
        current_path = current_path.parent

    resolved_target = chain_target.resolve(strict=True)
    if not _path_within_runtime_root(resolved_target, runtime_root):
        raise ValueError(f"Resolved runtime path escapes Review Gate root: {path}")

    return normalized_path


def _read_json_file(path: Path) -> Dict[str, Any]:
    _validate_runtime_path(path, expect_file=True)
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _write_json_atomically(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_private_directory(path.parent)
    _validate_runtime_path(path.parent, expect_directory=True)
    try:
        _validate_runtime_path(path, expect_file=True)
    except FileNotFoundError:
        pass

    temp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    serialized = json.dumps(payload, indent=2)

    try:
        with temp_path.open("w", encoding="utf-8") as file_handle:
            file_handle.write(serialized)
            file_handle.flush()
            os.fsync(file_handle.fileno())

        os.replace(temp_path, path)

        try:
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if os.path.lexists(str(temp_path)):
            try:
                temp_path.unlink()
            except OSError:
                pass

# Configure logging with immediate flush on stderr only
handlers = []
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.INFO)
handlers.append(stderr_handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

class ReviewGateServer:
    def __init__(self):
        self.server = Server("review-gate-v2")
        self.setup_handlers()
        self.shutdown_requested = False
        self.shutdown_reason = ""
        self._last_attachments = []
        self._last_session_outcome = {"status": "idle", "message": ""}
        self._last_acknowledgement_outcome = {"status": "idle", "message": ""}
        self._session_contracts: Dict[str, Dict[str, str]] = {}
        self._heartbeat_count = 0
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
        self._write_status_heartbeat("starting")
        
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

    def _status_file(self) -> Path:
        return get_runtime_root() / STATUS_FILE_NAME

    def _write_status_heartbeat(self, server_state: str = "running") -> None:
        status_payload = {
            "timestamp": datetime.now().isoformat(),
            "source": "review_gate_mcp_status",
            "protocol_version": IPC_PROTOCOL_VERSION,
            "pid": os.getpid(),
            "server_state": server_state,
            "heartbeat_count": self._heartbeat_count,
            "heartbeat_interval_seconds": 10,
            "session_status": self._last_session_outcome.get("status", "idle"),
            "acknowledgement_status": self._last_acknowledgement_outcome.get("status", "idle"),
            "speech_monitoring_active": bool(getattr(self, "_speech_monitoring_active", False)),
        }
        _write_json_atomically(self._status_file(), status_payload)

    def _contract_key(self, trigger_id: str) -> str:
        return _session_token(trigger_id)

    def _create_session_contract(self, trigger_id: str) -> Dict[str, str]:
        contract = {
            "trigger_id": trigger_id,
            "protocol_version": IPC_PROTOCOL_VERSION,
            "session_token": uuid.uuid4().hex,
        }
        self._session_contracts[self._contract_key(trigger_id)] = contract
        return contract

    def _get_session_contract(self, trigger_id: str) -> Optional[Dict[str, str]]:
        return self._session_contracts.get(self._contract_key(trigger_id))

    def _clear_session_contract(self, trigger_id: str) -> None:
        self._session_contracts.pop(self._contract_key(trigger_id), None)

    def _session_envelope_fields(self, trigger_id: str) -> Dict[str, str]:
        contract = self._get_session_contract(trigger_id)
        if not contract:
            raise ValueError(f"No active session contract found for trigger {trigger_id}")
        return {
            "trigger_id": contract["trigger_id"],
            "protocol_version": contract["protocol_version"],
            "session_token": contract["session_token"],
        }

    def _validate_session_envelope(
        self,
        envelope: Any,
        *,
        expected_trigger_id: Optional[str] = None,
        expected_source: Optional[str] = None,
        required_data_keys: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(envelope, dict):
            raise ValueError("Session envelope must be a JSON object")

        protocol_version = str(envelope.get("protocol_version") or "").strip()
        if protocol_version != IPC_PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {protocol_version or 'missing'}")

        envelope_trigger_id = str(
            envelope.get("trigger_id")
            or (envelope.get("data", {}) or {}).get("trigger_id")
            or ""
        ).strip()
        if not envelope_trigger_id:
            raise ValueError("Session envelope is missing trigger_id")

        if expected_trigger_id and envelope_trigger_id != expected_trigger_id:
            raise ValueError(
                f"Unexpected trigger_id in session envelope: {envelope_trigger_id}"
            )

        session_token = str(envelope.get("session_token") or "").strip()
        if not session_token:
            raise ValueError("Session envelope is missing session_token")

        contract = self._get_session_contract(envelope_trigger_id)
        if not contract:
            raise ValueError(f"No active session contract for trigger {envelope_trigger_id}")

        if session_token != contract["session_token"]:
            raise ValueError(f"Session token mismatch for trigger {envelope_trigger_id}")

        if expected_source:
            source = str(envelope.get("source") or "").strip()
            if source != expected_source:
                raise ValueError(
                    f"Unexpected session envelope source for {envelope_trigger_id}: {source or 'missing'}"
                )

        data = envelope.get("data")
        if required_data_keys:
            if not isinstance(data, dict):
                raise ValueError("Session envelope data payload must be an object")
            for required_key in required_data_keys:
                if data.get(required_key) in (None, ""):
                    raise ValueError(
                        f"Session envelope data is missing required field '{required_key}'"
                    )

        if isinstance(data, dict):
            nested_trigger_id = str(data.get("trigger_id") or envelope_trigger_id).strip()
            if nested_trigger_id != envelope_trigger_id:
                raise ValueError("Nested trigger_id does not match the session envelope")

            nested_protocol_version = str(
                data.get("protocol_version") or protocol_version
            ).strip()
            if nested_protocol_version != protocol_version:
                raise ValueError("Nested protocol_version does not match the session envelope")

            nested_session_token = str(data.get("session_token") or session_token).strip()
            if nested_session_token != session_token:
                raise ValueError("Nested session_token does not match the session envelope")

        return envelope

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

    def _session_last_activity(self, session_path: Path) -> float:
        """Return the newest modification time inside a session directory."""
        latest_mtime = session_path.stat().st_mtime
        for child_path in session_path.rglob("*"):
            try:
                latest_mtime = max(latest_mtime, child_path.stat().st_mtime)
            except FileNotFoundError:
                continue
        return latest_mtime

    def _cleanup_session_directory(self, trigger_id: str, clear_contract: bool = True) -> bool:
        """Remove an entire session directory and every IPC artifact it owns."""
        session_path = _session_path(trigger_id)
        if not session_path.exists():
            if clear_contract:
                self._clear_session_contract(trigger_id)
            return False

        try:
            shutil.rmtree(session_path)
            logger.info(f"🧹 Removed session directory for trigger {trigger_id}: {session_path}")
            if clear_contract:
                self._clear_session_contract(trigger_id)
            return True
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Could not clean up session directory {session_path}: {cleanup_error}")
            return False

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
        """Remove abandoned session directories before they can be reused."""
        cutoff = time.time() - max_age_seconds
        removed_count = 0

        try:
            for session_path in _sessions_root().iterdir():
                if not session_path.is_dir():
                    continue

                try:
                    if self._session_last_activity(session_path) >= cutoff:
                        continue

                    if self._cleanup_session_directory(session_path.name):
                        removed_count += 1
                except FileNotFoundError:
                    continue
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Could not inspect stale session directory {session_path}: {cleanup_error}")
        except FileNotFoundError:
            return 0

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
            logger.info(
                "📋 Tool request metadata: name=%s arg_keys=%s",
                name,
                sorted((arguments or {}).keys())
            )
            
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
        
        logger.info(
            "🎯 Unified Review Gate activated mode=%s title_chars=%s message_chars=%s timeout=%ss",
            mode,
            len(title),
            len(message),
            timeout,
        )
        
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
        
        try:
            if success:
                logger.info(f"🔥 UNIFIED POPUP TRIGGERED - waiting for user input (trigger_id: {trigger_id}, mode: {mode})")
                
                # Wait for user input with specified timeout
                user_input = await self._wait_for_user_input(trigger_id, timeout=timeout)
                
                if user_input:
                    # Return user input directly to MCP client with mode context
                    logger.info(
                        "✅ Returning unified Review Gate response trigger=%s chars=%s",
                        trigger_id,
                        len(user_input),
                    )
                    result_message = f"✅ User Response (Mode: {mode})\n\n"
                    result_message += f"💬 Input: {user_input}\n"
                    result_message += f"📝 Request: {message}\n"
                    result_message += f"📍 Context: {context}\n"
                    result_message += f"⚙️ Mode: {mode}\n"
                    result_message += f"🚨 Urgent: {urgent}\n\n"
                    result_message += f"🎯 User interaction completed successfully via unified Review Gate tool."
                    
                    return [TextContent(type="text", text=result_message)]

                response = f"TIMEOUT: No user input received within {timeout} seconds (Mode: {mode})"
                logger.warning(f"⚠️ Unified Review Gate timed out waiting for user input after {timeout} seconds")
                return [TextContent(type="text", text=response)]

            response = f"ERROR: Failed to trigger unified Review Gate popup (Mode: {mode})"
            return [TextContent(type="text", text=response)]
        finally:
            self._cleanup_session_directory(trigger_id)
            self._cleanup_stale_session_files()

    async def _handle_review_gate_chat(self, args: dict) -> list[TextContent]:
        """Handle Review Gate chat popup and wait for user input with 5 minute timeout"""
        message = args.get("message", "Please provide your review or feedback:")
        title = args.get("title", "Review Gate V2 - ゲート")
        context = args.get("context", "")
        urgent = args.get("urgent", False)
        self._clear_last_attachments()
        self._set_session_outcome("pending")
        self._set_acknowledgement_outcome("pending")
        
        logger.info(
            "💬 Activating Review Gate chat popup title_chars=%s message_chars=%s",
            len(title),
            len(message),
        )
        
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
                    logger.info(
                        "✅ Returning Review Gate response trigger=%s chars=%s attachments=%s",
                        trigger_id,
                        len(user_input),
                        len(self._last_attachments or []),
                    )
                    
                    # Check for images in the last response data
                    response_content = [TextContent(type="text", text=f"User Response: {user_input}")]
                    
                    # If we have stored attachment data, include images
                    if hasattr(self, '_last_attachments') and self._last_attachments:
                        image_attachment_count = 0
                        for attachment in self._last_attachments:
                            if attachment.get('mimeType', '').startswith('image/'):
                                try:
                                    image_content = ImageContent(
                                        type="image",
                                        data=attachment['base64Data'],
                                        mimeType=attachment['mimeType']
                                    )
                                    response_content.append(image_content)
                                    image_attachment_count += 1
                                except Exception as e:
                                    logger.error(f"❌ Error adding image to response: {e}")
                        if image_attachment_count:
                            logger.info(
                                "📸 Added image attachments to Review Gate response trigger=%s count=%s",
                                trigger_id,
                                image_attachment_count,
                            )
                    
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
            self._cleanup_session_directory(trigger_id)
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
                    logger.info(
                        "✅ Retrieved Review Gate response trigger=%s chars=%s",
                        trigger_id,
                        len(user_input),
                    )

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
        
        trigger_id = f"quick_{int(time.time() * 1000)}"
        logger.info(
            "⚡ Activating quick review trigger=%s prompt_chars=%s context_chars=%s",
            trigger_id,
            len(prompt),
            len(context),
        )

        # Create trigger for quick input IMMEDIATELY
        success = await self._trigger_cursor_popup_immediately({
            "tool": "quick_review",
            "prompt": prompt,
            "context": context,
            "title": "Quick Review - Review Gate v2",
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True
        })
        
        try:
            if success:
                logger.info(f"🔥 QUICK POPUP TRIGGERED - waiting for user input (trigger_id: {trigger_id})")
                
                # Wait for quick user input
                user_input = await self._wait_for_user_input(trigger_id, timeout=90)  # 1.5 minute timeout for quick review
                
                if user_input:
                    # Return user input directly to MCP client
                    logger.info(
                        "✅ Returning quick review trigger=%s chars=%s",
                        trigger_id,
                        len(user_input),
                    )
                    return [TextContent(type="text", text=user_input)]

                response = f"TIMEOUT: No quick review input received within 1.5 minutes"
                logger.warning("⚠️ Quick review timed out")
                return [TextContent(type="text", text=response)]

            response = f"ERROR: Failed to trigger quick review popup"
            return [TextContent(type="text", text=response)]
        finally:
            self._cleanup_session_directory(trigger_id)

    async def _handle_file_review(self, args: dict) -> list[TextContent]:
        """Handle file review request and wait for file selection with immediate activation"""
        instruction = args.get("instruction", "Please select file(s) for review:")
        file_types = args.get("file_types", ["*"])
        
        trigger_id = f"file_{int(time.time() * 1000)}"
        logger.info(
            "📁 Activating file review trigger=%s instruction_chars=%s file_type_count=%s",
            trigger_id,
            len(instruction),
            len(file_types),
        )

        # Create trigger for file picker IMMEDIATELY
        success = await self._trigger_cursor_popup_immediately({
            "tool": "file_review",
            "instruction": instruction,
            "file_types": file_types,
            "title": "File Review - Review Gate v2",
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "immediate_activation": True
        })
        
        try:
            if success:
                logger.info(f"🔥 FILE POPUP TRIGGERED - waiting for selection (trigger_id: {trigger_id})")
                
                # Wait for file selection
                user_input = await self._wait_for_user_input(trigger_id, timeout=90)  # 1.5 minute timeout
                
                if user_input:
                    response = f"📁 File Review completed!\n\n**Selected Files:** {user_input}\n\n**Instruction:** {instruction}\n**Allowed Types:** {', '.join(file_types)}\n\nYou can now proceed to analyze the selected files."
                    logger.info(
                        "✅ Returning file review selection trigger=%s chars=%s",
                        trigger_id,
                        len(user_input),
                    )
                else:
                    response = f"⏰ File Review timed out.\n\n**Instruction:** {instruction}\n\nNo files selected within 1.5 minutes. Try again or proceed with current workspace files."
                    logger.warning("⚠️ File review timed out")
            else:
                response = f"⚠️ File Review trigger failed. Manual activation may be needed."
            
            logger.info("🏁 File review processing complete")
            return [TextContent(type="text", text=response)]
        finally:
            self._cleanup_session_directory(trigger_id)

    async def _handle_ingest_text(self, args: dict) -> list[TextContent]:
        """
        Handle text ingestion with immediate activation and user input capture
        """
        text_content = args.get("text_content", "")
        source = args.get("source", "extension")
        context = args.get("context", "")
        processing_mode = args.get("processing_mode", "immediate")
        
        logger.info(
            "🚀 Activating ingest_text source=%s context_chars=%s mode=%s text_chars=%s",
            source,
            len(context),
            processing_mode,
            len(text_content),
        )
        
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
        
        try:
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

                result_message = f"⏰ Text ingestion timed out.\n\n"
                result_message += f"📝 Text Content: {text_content}\n"
                result_message += f"📍 Source: {source}\n\n"
                result_message += f"No user response received within 2 minutes. The text content is noted but no additional processing occurred."
                
                logger.warning("⚠️ Text ingestion timed out")
                return [TextContent(type="text", text=result_message)]

            result_message = f"⚠️ Text ingestion trigger failed.\n\n"
            result_message += f"📝 Text Content: {text_content}\n"
            result_message += f"Manual activation may be needed."
            
            logger.error("❌ Failed to trigger text ingestion popup")
            return [TextContent(type="text", text=result_message)]
        finally:
            self._cleanup_session_directory(trigger_id)

    async def _handle_shutdown_mcp(self, args: dict) -> list[TextContent]:
        """Handle shutdown_mcp request and wait for confirmation with immediate activation"""
        reason = args.get("reason", "Task completed successfully")
        immediate = args.get("immediate", False)
        cleanup = args.get("cleanup", True)
        
        trigger_id = f"shutdown_{int(time.time() * 1000)}"
        logger.info(
            "🛑 Activating shutdown_mcp trigger=%s reason_chars=%s immediate=%s cleanup=%s",
            trigger_id,
            len(reason),
            bool(immediate),
            bool(cleanup),
        )

        # Create trigger for shutdown_mcp IMMEDIATELY
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
        
        try:
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
                        logger.info(
                            "✅ Shutdown confirmed by user trigger=%s chars=%s",
                            trigger_id,
                            len(user_input),
                        )
                        logger.info(
                            "🛑 Server shutdown initiated trigger=%s reason_chars=%s",
                            trigger_id,
                            len(self.shutdown_reason),
                        )
                    else:
                        response = f"💡 shutdown_mcp CANCELLED - Alternative instructions received!\n\n**User Response:** {user_input}\n\n**Original Reason:** {reason}\n\nShutdown cancelled. User provided alternative instructions instead of confirmation."
                        logger.info(
                            "💡 Shutdown cancelled with alternative instructions trigger=%s chars=%s",
                            trigger_id,
                            len(user_input),
                        )
                else:
                    response = f"⏰ shutdown_mcp timed out.\n\n**Reason:** {reason}\n\nNo response received within 1 minute. Shutdown cancelled due to timeout."
                    logger.warning("⚠️ Shutdown timed out - shutdown cancelled")
            else:
                response = f"⚠️ shutdown_mcp trigger failed. Manual activation may be needed."
            
            logger.info("🏁 shutdown_mcp processing complete")
            return [TextContent(type="text", text=response)]
        finally:
            self._cleanup_session_directory(trigger_id)

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
                        data = self._validate_session_envelope(
                            _read_json_file(ack_file),
                            expected_trigger_id=trigger_id,
                            expected_source="review_gate_extension",
                        )
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid acknowledgement JSON for {trigger_id}: {e}")
                        try:
                            ack_file.unlink()
                        except Exception:
                            pass
                        await asyncio.sleep(check_interval)
                        continue
                    except ValueError as validation_error:
                        logger.warning(
                            f"⚠️ Removing invalid acknowledgement envelope for {trigger_id}: {validation_error}"
                        )
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
                            try:
                                data = self._validate_session_envelope(
                                    _read_json_file(response_file),
                                    expected_trigger_id=trigger_id,
                                    expected_source="review_gate_extension",
                                )
                            except json.JSONDecodeError as e:
                                logger.error(f"❌ JSON decode error in {response_file}: {e}")
                                self._last_attachments = []
                                try:
                                    response_file.unlink()
                                except Exception:
                                    pass
                                continue
                            except ValueError as validation_error:
                                logger.warning(
                                    f"⚠️ Removing invalid response envelope for {trigger_id}: {validation_error}"
                                )
                                self._clear_last_attachments()
                                try:
                                    response_file.unlink()
                                except Exception:
                                    pass
                                continue

                            user_input = data.get("user_input", data.get("response", data.get("message", ""))).strip()
                            attachments = data.get("attachments", [])
                            
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
                            
                            if attachments:
                                logger.info(f"📎 Found {len(attachments)} attachments")
                                self._last_attachments = attachments
                                attachment_descriptions = []
                                for att in attachments:
                                    if att.get('mimeType', '').startswith('image/'):
                                        attachment_descriptions.append(f"Image: {att.get('fileName', 'unknown')}")
                                
                                if attachment_descriptions:
                                    user_input += f"\n\nAttached: {', '.join(attachment_descriptions)}"
                            else:
                                self._clear_last_attachments()
                            
                            # Clean up response file immediately
                            try:
                                response_file.unlink()
                                logger.info(f"🧹 Response file cleaned up: {response_file}")
                            except Exception as cleanup_error:
                                logger.warning(f"⚠️ Cleanup error: {cleanup_error}")
                            
                            if user_input:
                                self._set_session_outcome("response", "User response received", source_file=str(response_file))
                                logger.info(
                                    "🎉 Received Review Gate response trigger=%s chars=%s attachments=%s",
                                    trigger_id,
                                    len(user_input),
                                    len(self._last_attachments or []),
                                )
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

            self._cleanup_session_directory(trigger_id)
            trigger_file = _session_file("trigger", trigger_id)
            session_contract = self._create_session_contract(trigger_id)
            
            trigger_data = {
                "timestamp": datetime.now().isoformat(),
                "system": "review-gate-v2",
                "editor": "cursor",
                "source": "review_gate_mcp",
                "trigger_id": session_contract["trigger_id"],
                "protocol_version": session_contract["protocol_version"],
                "session_token": session_contract["session_token"],
                "data": data,
                "pid": os.getpid(),
                "active_window": True,
                "mcp_integration": True,
                "immediate_activation": True
            }
            
            logger.info(
                "🎯 Creating trigger envelope trigger=%s tool=%s session_dir=%s",
                trigger_id,
                str(data.get("tool") or "unknown"),
                trigger_file.parent.name,
            )
            
            # Write trigger file with immediate flush
            _write_json_atomically(trigger_file, trigger_data)
            
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
            logger.info(f"📁 Trigger file ready: {trigger_file.name}")
            logger.info(f"📊 Trigger file size: {file_size} bytes")
            
            # Add small delay to allow extension to process
            await asyncio.sleep(0.2)  # Wait 200ms for extension to process
            
            # Note: Trigger file may have been consumed by extension already, which is good!
            try:
                if trigger_file.exists():
                    logger.info(f"✅ Trigger file still exists: {trigger_file.name}")
                else:
                    logger.info(f"✅ Trigger file was consumed by extension: {trigger_file.name}")
                    logger.info(f"🎯 This is expected behavior - extension is working properly")
            except Exception as check_error:
                logger.info(f"✅ Cannot check trigger file status (likely consumed): {check_error}")
                logger.info(f"🎯 This is expected behavior - extension is working properly")
            
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
            
            # Create heartbeat task to keep the redacted status file fresh for extension monitoring
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

            try:
                self._write_status_heartbeat("shutting_down" if self.shutdown_requested else "stopped")
            except Exception as status_error:
                logger.warning(f"⚠️ Failed to write final status heartbeat: {status_error}")
            
            if self.shutdown_requested:
                logger.info(
                    "🛑 Review Gate v2 server shutting down reason_chars=%s",
                    len(self.shutdown_reason),
                )
            else:
                logger.info("🏁 Review Gate v2 server completed normally")

    async def _heartbeat_logger(self):
        """Periodically update the redacted MCP status file for the extension."""
        logger.info("💓 Starting MCP status heartbeat")
        self._write_status_heartbeat("running")
        
        while not self.shutdown_requested:
            try:
                await asyncio.sleep(10)
                self._heartbeat_count += 1
                self._write_status_heartbeat("running")
                logger.info(f"💓 MCP heartbeat #{self._heartbeat_count}")
                
                for handler in logger.handlers:
                    if hasattr(handler, 'flush'):
                        handler.flush()
                        
            except Exception as e:
                logger.error(f"❌ Heartbeat error: {e}")
                await asyncio.sleep(5)
        
        self._write_status_heartbeat("shutting_down")
        logger.info("💔 MCP status heartbeat stopped")
    
    async def _monitor_shutdown(self):
        """Monitor for shutdown requests in a separate task"""
        while not self.shutdown_requested:
            await asyncio.sleep(1)  # Check every second
        
        # Cleanup operations before shutdown
        logger.info("🧹 Performing cleanup operations before shutdown...")
        self._write_status_heartbeat("shutting_down")
        
        try:
            for session_path in _sessions_root().iterdir():
                if not session_path.is_dir():
                    continue
                self._cleanup_session_directory(session_path.name)
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

                            trigger_data = self._validate_session_envelope(
                                _read_json_file(trigger_path),
                                expected_source="review_gate_extension",
                                required_data_keys=("trigger_id", "tool", "audio_file"),
                            )

                            request_trigger_id = trigger_data.get('data', {}).get('trigger_id')
                            if expected_trigger_id and request_trigger_id and expected_trigger_id != request_trigger_id:
                                logger.warning(
                                    f"⚠️ Ignoring mismatched speech trigger file {trigger_path.name}: "
                                    f"expected {expected_trigger_id}, got {request_trigger_id}"
                                )
                                trigger_path.unlink()
                                continue

                            expected_trigger_path = _session_file("speech_trigger", request_trigger_id)
                            if trigger_path.resolve(strict=False) != expected_trigger_path.resolve(strict=False):
                                logger.warning(
                                    f"⚠️ Ignoring speech trigger outside the expected session path: {trigger_path.name}"
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
            
            logger.info(
                "✅ Speech transcription completed trigger=%s chars=%s",
                trigger_id,
                len(transcription),
            )
            
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
                **self._session_envelope_fields(trigger_id),
                'transcription': transcription,
                'success': error is None,
                'status': 'ok' if error is None else 'error',
                'error': error,
                'source': 'review_gate_whisper'
            }
            
            response_file = _session_file("speech_response", trigger_id)
            _write_json_atomically(response_file, response_data)
            
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
