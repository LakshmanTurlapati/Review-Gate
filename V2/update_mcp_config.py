#!/usr/bin/env python3
"""Safely merge or remove Review Gate from Cursor MCP configuration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


TEMPLATE_BASE_PATH = "/Users/YOUR_USERNAME/cursor-extensions/review-gate-v2"
TEMPLATE_COMMAND_PATH = f"{TEMPLATE_BASE_PATH}/venv/bin/python"


def _load_json_file(path: Path, *, create_default: bool = False) -> dict[str, Any]:
    if not path.exists():
        if create_default:
            return {"mcpServers": {}}
        raise FileNotFoundError(f"File not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _ensure_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _normalize_path(path_value: str) -> str:
    return path_value.replace("\\", "/")


def _inject_template_paths(value: Any, *, install_dir: str, python_cmd: str) -> Any:
    if isinstance(value, dict):
        return {
            key: _inject_template_paths(item, install_dir=install_dir, python_cmd=python_cmd)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _inject_template_paths(item, install_dir=install_dir, python_cmd=python_cmd)
            for item in value
        ]
    if isinstance(value, str):
        if value == TEMPLATE_COMMAND_PATH:
            return python_cmd
        if TEMPLATE_BASE_PATH in value:
            return value.replace(TEMPLATE_BASE_PATH, install_dir)
    return value


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def merge(
    *,
    config_path: Path,
    template_path: Path,
    server_name: str,
    install_dir: str,
    python_cmd: str,
) -> None:
    config = _load_json_file(config_path, create_default=True)
    template = _load_json_file(template_path)

    servers = _ensure_mapping(config.get("mcpServers"), field_name="mcpServers")
    template_servers = _ensure_mapping(template.get("mcpServers"), field_name="template mcpServers")

    if server_name not in template_servers:
        raise ValueError(f"Server '{server_name}' not found in template {template_path}")

    install_dir = _normalize_path(install_dir)
    python_cmd = _normalize_path(python_cmd)

    merged_servers = dict(servers)
    merged_servers.pop(server_name, None)
    merged_servers[server_name] = _inject_template_paths(
        template_servers[server_name],
        install_dir=install_dir,
        python_cmd=python_cmd,
    )

    config["mcpServers"] = merged_servers
    _write_json_file(config_path, config)


def remove(*, config_path: Path, server_name: str) -> None:
    if not config_path.exists():
        return

    config = _load_json_file(config_path)
    servers = _ensure_mapping(config.get("mcpServers"), field_name="mcpServers")
    servers.pop(server_name, None)
    config["mcpServers"] = servers
    _write_json_file(config_path, config)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mutate Cursor MCP config safely.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    merge_parser = subparsers.add_parser("merge", help="Merge or replace one MCP server entry.")
    merge_parser.add_argument("--config", required=True, type=Path)
    merge_parser.add_argument("--template", required=True, type=Path)
    merge_parser.add_argument("--server-name", required=True)
    merge_parser.add_argument("--install-dir", required=True)
    merge_parser.add_argument("--python-cmd", required=True)

    remove_parser = subparsers.add_parser("remove", help="Remove one MCP server entry.")
    remove_parser.add_argument("--config", required=True, type=Path)
    remove_parser.add_argument("--server-name", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "merge":
            merge(
                config_path=args.config,
                template_path=args.template,
                server_name=args.server_name,
                install_dir=args.install_dir,
                python_cmd=args.python_cmd,
            )
        else:
            remove(config_path=args.config, server_name=args.server_name)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"ERROR: Unexpected failure: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
