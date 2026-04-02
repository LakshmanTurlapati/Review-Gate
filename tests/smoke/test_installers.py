"""Non-destructive smoke coverage for the shipped installers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
V2_DIR = REPO_ROOT / "V2"
PACKAGE_JSON = json.loads((V2_DIR / "cursor-extension" / "package.json").read_text(encoding="utf-8"))
EXTENSION_BASENAME = f"review-gate-v2-{PACKAGE_JSON['version']}.vsix"


def normalize_path(path: Path | str) -> str:
    return str(path).replace("\\", "/")


class InstallerSmokeTests(unittest.TestCase):
    maxDiff = None

    def seed_existing_config(self, home_dir: Path) -> Path:
        config_path = home_dir / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "existing-server": {"command": "node", "args": ["existing.js"]},
                        "review-gate-v2": {"command": "python", "args": ["legacy.py"]},
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return config_path

    def smoke_env(self, home_dir: Path, install_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "REVIEW_GATE_SMOKE": "1",
                "REVIEW_GATE_TEST_HOME": str(home_dir),
                "REVIEW_GATE_TEST_INSTALL_DIR": str(install_dir),
                "REVIEW_GATE_SKIP_DEP_INSTALL": "1",
                "REVIEW_GATE_SKIP_EXTENSION_INSTALL": "1",
                "REVIEW_GATE_SKIP_SERVER_SMOKE": "1",
            }
        )
        return env

    def assert_backup_and_config(self, config_path: Path, install_dir: Path, expected_command: str) -> None:
        backup_paths = sorted(config_path.parent.glob("mcp.json.backup*"))
        self.assertTrue(backup_paths, f"Expected backup file next to {config_path}")

        backup_payload = json.loads(backup_paths[0].read_text(encoding="utf-8"))
        self.assertIn("existing-server", backup_payload["mcpServers"])
        self.assertEqual(backup_payload["mcpServers"]["review-gate-v2"]["args"], ["legacy.py"])

        payload = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIn("existing-server", payload["mcpServers"])

        review_gate_server = payload["mcpServers"]["review-gate-v2"]
        normalized_install_dir = normalize_path(install_dir)
        self.assertEqual(review_gate_server["command"], expected_command)
        self.assertEqual(
            review_gate_server["args"],
            [f"{normalized_install_dir}/review_gate_v2_mcp.py"],
        )
        self.assertEqual(review_gate_server["env"]["PYTHONPATH"], normalized_install_dir)
        self.assertEqual(review_gate_server["env"]["REVIEW_GATE_MODE"], "cursor_integration")

    def assert_copied_assets(self, install_dir: Path, rule_path: Path) -> None:
        self.assertTrue((install_dir / "review_gate_v2_mcp.py").exists())
        self.assertTrue((install_dir / "requirements_simple.txt").exists())
        self.assertTrue((install_dir / EXTENSION_BASENAME).exists())
        self.assertTrue((install_dir / "venv").exists())
        self.assertTrue(rule_path.exists(), f"Expected installed rule at {rule_path}")

    def run_installer(self, command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_install_sh_smoke_mode_uses_temp_roots(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-sh-") as temp_dir:
            temp_root = Path(temp_dir)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"
            config_path = self.seed_existing_config(home_dir)

            completed = self.run_installer([bash, str(V2_DIR / "install.sh")], self.smoke_env(home_dir, install_dir))
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            if sys.platform == "darwin":
                rule_path = home_dir / "Library" / "Application Support" / "Cursor" / "User" / "rules" / "ReviewGateV2.mdc"
            else:
                rule_path = home_dir / ".config" / "Cursor" / "User" / "rules" / "ReviewGateV2.mdc"

            self.assert_copied_assets(install_dir, rule_path)
            self.assert_backup_and_config(
                config_path,
                install_dir,
                f"{normalize_path(install_dir)}/venv/bin/python",
            )

    def test_install_ps1_smoke_mode_uses_temp_roots(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell.exe")
        if not powershell:
            self.skipTest("pwsh or powershell.exe is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-ps1-") as temp_dir:
            temp_root = Path(temp_dir)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"
            config_path = self.seed_existing_config(home_dir)

            command = [powershell, "-NoLogo", "-NoProfile"]
            if powershell.lower().endswith("powershell.exe"):
                command.extend(["-ExecutionPolicy", "Bypass"])
            command.extend(["-File", str(V2_DIR / "install.ps1")])

            completed = self.run_installer(command, self.smoke_env(home_dir, install_dir))
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            rule_path = home_dir / "AppData" / "Roaming" / "Cursor" / "User" / "rules" / "ReviewGateV2.mdc"
            if (install_dir / "venv" / "Scripts" / "python.exe").exists():
                expected_command = normalize_path(install_dir / "venv" / "Scripts" / "python.exe")
            else:
                expected_command = normalize_path(install_dir / "venv" / "bin" / "python")

            self.assert_copied_assets(install_dir, rule_path)
            self.assert_backup_and_config(config_path, install_dir, expected_command)

    def test_install_bat_smoke_mode_uses_temp_roots(self) -> None:
        cmd = shutil.which("cmd.exe")
        if not cmd:
            self.skipTest("cmd.exe is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-bat-") as temp_dir:
            temp_root = Path(temp_dir)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"
            config_path = self.seed_existing_config(home_dir)

            completed = self.run_installer(
                [cmd, "/d", "/c", str(V2_DIR / "install.bat")],
                self.smoke_env(home_dir, install_dir),
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            rule_path = home_dir / "AppData" / "Roaming" / "Cursor" / "User" / "rules" / "ReviewGateV2.mdc"
            self.assert_copied_assets(install_dir, rule_path)
            self.assert_backup_and_config(
                config_path,
                install_dir,
                normalize_path(install_dir / "venv" / "Scripts" / "python.exe"),
            )


if __name__ == "__main__":
    unittest.main()
