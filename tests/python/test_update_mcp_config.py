"""Fixture coverage for the shipped MCP config helper."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_SCRIPT = REPO_ROOT / "V2" / "update_mcp_config.py"
MCP_TEMPLATE = REPO_ROOT / "V2" / "mcp.json"


def normalize_path(value: str) -> str:
    return value.replace("\\", "/")


class UpdateMcpConfigCliTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_path = Path(self.temp_dir.name)
        self.config_path = self.temp_path / "mcp.json"

    def write_config(self, payload: dict) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def read_config(self) -> dict:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def run_helper(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HELPER_SCRIPT), *args],
            capture_output=True,
            cwd=REPO_ROOT,
            text=True,
            check=False,
        )

    def test_merge_preserves_unrelated_servers_and_injects_posix_paths(self) -> None:
        existing_config = {
            "mcpServers": {
                "existing-server": {"command": "node", "args": ["existing.js"]},
                "review-gate-v2": {"command": "python", "args": ["legacy.py"]},
            }
        }
        install_dir = "/tmp/review-gate smoke/review-gate-v2"
        python_cmd = f"{install_dir}/venv/bin/python"
        self.write_config(existing_config)

        completed = self.run_helper(
            "merge",
            "--config",
            str(self.config_path),
            "--template",
            str(MCP_TEMPLATE),
            "--server-name",
            "review-gate-v2",
            "--install-dir",
            install_dir,
            "--python-cmd",
            python_cmd,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = self.read_config()
        self.assertEqual(payload["mcpServers"]["existing-server"], existing_config["mcpServers"]["existing-server"])
        self.assertEqual(payload["mcpServers"]["review-gate-v2"]["command"], python_cmd)
        self.assertEqual(
            payload["mcpServers"]["review-gate-v2"]["args"],
            [f"{install_dir}/review_gate_v2_mcp.py"],
        )
        self.assertEqual(payload["mcpServers"]["review-gate-v2"]["env"]["PYTHONPATH"], install_dir)
        self.assertEqual(payload["mcpServers"]["review-gate-v2"]["env"]["REVIEW_GATE_MODE"], "cursor_integration")

    def test_merge_injects_windows_style_paths(self) -> None:
        install_dir = r"C:\Users\Example\cursor-extensions\review-gate-v2"
        python_cmd = r"C:\Users\Example\cursor-extensions\review-gate-v2\venv\Scripts\python.exe"

        completed = self.run_helper(
            "merge",
            "--config",
            str(self.config_path),
            "--template",
            str(MCP_TEMPLATE),
            "--server-name",
            "review-gate-v2",
            "--install-dir",
            install_dir,
            "--python-cmd",
            python_cmd,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = self.read_config()
        server = payload["mcpServers"]["review-gate-v2"]
        normalized_install_dir = normalize_path(install_dir)
        normalized_python_cmd = normalize_path(python_cmd)

        self.assertEqual(server["command"], normalized_python_cmd)
        self.assertEqual(server["args"], [f"{normalized_install_dir}/review_gate_v2_mcp.py"])
        self.assertEqual(server["env"]["PYTHONPATH"], normalized_install_dir)

    def test_remove_deletes_only_review_gate_server(self) -> None:
        existing_config = {
            "mcpServers": {
                "existing-server": {"command": "node", "args": ["existing.js"]},
                "review-gate-v2": {"command": "python", "args": ["legacy.py"]},
            }
        }
        self.write_config(existing_config)

        completed = self.run_helper(
            "remove",
            "--config",
            str(self.config_path),
            "--server-name",
            "review-gate-v2",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = self.read_config()
        self.assertEqual(payload["mcpServers"], {"existing-server": {"command": "node", "args": ["existing.js"]}})

    def test_invalid_json_fails_cleanly(self) -> None:
        self.config_path.write_text("{not json", encoding="utf-8")

        completed = self.run_helper(
            "merge",
            "--config",
            str(self.config_path),
            "--template",
            str(MCP_TEMPLATE),
            "--server-name",
            "review-gate-v2",
            "--install-dir",
            "/tmp/review-gate-v2",
            "--python-cmd",
            "/tmp/review-gate-v2/venv/bin/python",
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("ERROR: Invalid JSON", completed.stderr)

    def test_missing_template_server_name_fails_clearly(self) -> None:
        completed = self.run_helper(
            "merge",
            "--config",
            str(self.config_path),
            "--template",
            str(MCP_TEMPLATE),
            "--server-name",
            "missing-server",
            "--install-dir",
            "/tmp/review-gate-v2",
            "--python-cmd",
            "/tmp/review-gate-v2/venv/bin/python",
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("Server 'missing-server' not found", completed.stderr)


if __name__ == "__main__":
    unittest.main()
