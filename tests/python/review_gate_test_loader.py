"""Stdlib-only test loader for the shipped Review Gate MCP server."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import tempfile
import types
import uuid
from contextlib import contextmanager
from typing import Iterator
from unittest import mock


_ROOT = pathlib.Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "V2" / "review_gate_v2_mcp.py"


class _StubServer:
    def __init__(self, name: str):
        self.name = name
        self._list_tools_handler = None
        self._call_tool_handler = None

    def list_tools(self):
        def decorator(func):
            self._list_tools_handler = func
            return func

        return decorator

    def call_tool(self):
        def decorator(func):
            self._call_tool_handler = func
            return func

        return decorator

    async def run(self, read_stream, write_stream, initialization_options):
        return None

    def create_initialization_options(self):
        return {}


def _install_dependency_stubs() -> None:
    if "mcp" not in os.sys.modules:
        os.sys.modules["mcp"] = types.ModuleType("mcp")

    if "mcp.server" not in os.sys.modules:
        server_module = types.ModuleType("mcp.server")
        server_module.Server = _StubServer
        os.sys.modules["mcp.server"] = server_module

    if "mcp.server.models" not in os.sys.modules:
        server_models_module = types.ModuleType("mcp.server.models")
        server_models_module.InitializationOptions = type("InitializationOptions", (), {})
        os.sys.modules["mcp.server.models"] = server_models_module

    if "mcp.server.stdio" not in os.sys.modules:
        stdio_module = types.ModuleType("mcp.server.stdio")

        @contextmanager
        def stdio_server():
            yield (None, None)

        stdio_module.stdio_server = stdio_server
        os.sys.modules["mcp.server.stdio"] = stdio_module

    if "mcp.types" not in os.sys.modules:
        types_module = types.ModuleType("mcp.types")

        class _BaseContent:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        for name in (
            "CallToolRequest",
            "ListToolsRequest",
            "Tool",
            "CallToolResult",
            "Resource",
            "ImageContent",
            "EmbeddedResource",
        ):
            setattr(types_module, name, type(name, (_BaseContent,), {}))

        class TextContent(_BaseContent):
            def __init__(self, type: str, text: str):
                super().__init__(type=type, text=text)

        types_module.TextContent = TextContent
        os.sys.modules["mcp.types"] = types_module

    if "faster_whisper" not in os.sys.modules:
        faster_whisper_module = types.ModuleType("faster_whisper")

        class WhisperModel:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        faster_whisper_module.WhisperModel = WhisperModel
        os.sys.modules["faster_whisper"] = faster_whisper_module


def unique_review_gate_user_id(prefix: str = "review-gate-test") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


@contextmanager
def isolated_review_gate_user(prefix: str = "review-gate-test") -> Iterator[str]:
    user_id = unique_review_gate_user_id(prefix=prefix)
    with mock.patch.dict(os.environ, {"REVIEW_GATE_USER_ID": user_id}, clear=False):
        yield user_id


@contextmanager
def disable_speech_monitoring(module) -> Iterator[None]:
    def _disabled_start(self):
        self._speech_monitoring_active = False
        self._speech_thread = None

    with mock.patch.object(module.ReviewGateServer, "_start_speech_monitoring", _disabled_start):
        yield


@contextmanager
def isolated_review_gate_runtime(module, prefix: str = "review-gate-test-runtime") -> Iterator[pathlib.Path]:
    temp_root = pathlib.Path(tempfile.mkdtemp(prefix=f"{prefix}-")).resolve()

    def _test_get_temp_path(filename: str) -> str:
        return str(temp_root / filename) if filename else str(temp_root)

    with mock.patch.object(module, "get_temp_path", side_effect=_test_get_temp_path):
        yield temp_root

    shutil.rmtree(temp_root, ignore_errors=True)


def load_review_gate_module():
    _install_dependency_stubs()

    module_name = f"review_gate_v2_mcp_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, _MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create import spec for {_MODULE_PATH}")

    module = importlib.util.module_from_spec(spec)
    os.sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
