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
RELEASE_MANIFEST = json.loads((V2_DIR / "release-manifest.json").read_text(encoding="utf-8"))
EXTENSION_BASENAME = RELEASE_MANIFEST["artifact_basename"]
CANONICAL_VSIX_PATH = REPO_ROOT / RELEASE_MANIFEST["canonical_vsix_path"]
RULE_REPO_PATH = REPO_ROOT / RELEASE_MANIFEST["rule_path"]

STAGED_REPO_FILES = (
    Path("V2") / "install.sh",
    Path("V2") / "install.ps1",
    Path("V2") / "install.bat",
    Path("V2") / "release-manifest.json",
    Path("V2") / "ReviewGateV2.mdc",
    Path("V2") / "review_gate_v2_mcp.py",
    Path("V2") / "requirements_simple.txt",
    Path("V2") / "update_mcp_config.py",
    Path("V2") / "mcp.json",
    Path("V2") / "cursor-extension" / "package.json",
    Path("scripts") / "package_review_gate_vsix.py",
)


def normalize_path(path: Path | str) -> str:
    return str(path).replace("\\", "/")


class InstallerSmokeTests(unittest.TestCase):
    maxDiff = None

    def stage_repo(self, stage_root: Path, *, include_canonical_vsix: bool) -> Path:
        staged_repo = stage_root / "repo"
        for relative_path in STAGED_REPO_FILES:
            source = REPO_ROOT / relative_path
            destination = staged_repo / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        if include_canonical_vsix:
            destination = staged_repo / RELEASE_MANIFEST["canonical_vsix_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(CANONICAL_VSIX_PATH, destination)

        return staged_repo

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

    def run_installer(self, command: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_missing_canonical_artifact_failure(self, completed: subprocess.CompletedProcess[str]) -> None:
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("Canonical extension file not found", output)
        self.assertNotIn(f"cursor-extension/{EXTENSION_BASENAME}", output)

    def test_install_sh_smoke_mode_uses_temp_roots(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-sh-") as temp_dir:
            temp_root = Path(temp_dir)
            staged_repo = self.stage_repo(temp_root, include_canonical_vsix=True)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"
            config_path = self.seed_existing_config(home_dir)

            completed = self.run_installer(
                [bash, str(staged_repo / "V2" / "install.sh")],
                self.smoke_env(home_dir, install_dir),
                staged_repo,
            )
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

    def test_install_sh_missing_canonical_vsix_fails_clearly(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-sh-missing-") as temp_dir:
            temp_root = Path(temp_dir)
            staged_repo = self.stage_repo(temp_root, include_canonical_vsix=False)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"

            completed = self.run_installer(
                [bash, str(staged_repo / "V2" / "install.sh")],
                self.smoke_env(home_dir, install_dir),
                staged_repo,
            )
            self.assert_missing_canonical_artifact_failure(completed)

    def test_install_ps1_smoke_mode_uses_temp_roots(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell.exe")
        if not powershell:
            self.skipTest("pwsh or powershell.exe is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-ps1-") as temp_dir:
            temp_root = Path(temp_dir)
            staged_repo = self.stage_repo(temp_root, include_canonical_vsix=True)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"
            config_path = self.seed_existing_config(home_dir)

            command = [powershell, "-NoLogo", "-NoProfile"]
            if powershell.lower().endswith("powershell.exe"):
                command.extend(["-ExecutionPolicy", "Bypass"])
            command.extend(["-File", str(staged_repo / "V2" / "install.ps1")])

            completed = self.run_installer(command, self.smoke_env(home_dir, install_dir), staged_repo)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            rule_path = home_dir / "AppData" / "Roaming" / "Cursor" / "User" / "rules" / "ReviewGateV2.mdc"
            if (install_dir / "venv" / "Scripts" / "python.exe").exists():
                expected_command = normalize_path(install_dir / "venv" / "Scripts" / "python.exe")
            else:
                expected_command = normalize_path(install_dir / "venv" / "bin" / "python")

            self.assert_copied_assets(install_dir, rule_path)
            self.assert_backup_and_config(config_path, install_dir, expected_command)

    def test_install_ps1_missing_canonical_vsix_fails_clearly(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell.exe")
        if not powershell:
            self.skipTest("pwsh or powershell.exe is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-ps1-missing-") as temp_dir:
            temp_root = Path(temp_dir)
            staged_repo = self.stage_repo(temp_root, include_canonical_vsix=False)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"

            command = [powershell, "-NoLogo", "-NoProfile"]
            if powershell.lower().endswith("powershell.exe"):
                command.extend(["-ExecutionPolicy", "Bypass"])
            command.extend(["-File", str(staged_repo / "V2" / "install.ps1")])

            completed = self.run_installer(command, self.smoke_env(home_dir, install_dir), staged_repo)
            self.assert_missing_canonical_artifact_failure(completed)

    def test_install_bat_smoke_mode_uses_temp_roots(self) -> None:
        cmd = shutil.which("cmd.exe")
        if not cmd:
            self.skipTest("cmd.exe is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-bat-") as temp_dir:
            temp_root = Path(temp_dir)
            staged_repo = self.stage_repo(temp_root, include_canonical_vsix=True)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"
            config_path = self.seed_existing_config(home_dir)

            completed = self.run_installer(
                [cmd, "/d", "/c", str(staged_repo / "V2" / "install.bat")],
                self.smoke_env(home_dir, install_dir),
                staged_repo,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            rule_path = home_dir / "AppData" / "Roaming" / "Cursor" / "User" / "rules" / "ReviewGateV2.mdc"
            self.assert_copied_assets(install_dir, rule_path)
            self.assert_backup_and_config(
                config_path,
                install_dir,
                normalize_path(install_dir / "venv" / "Scripts" / "python.exe"),
            )

    def test_install_bat_missing_canonical_vsix_fails_clearly(self) -> None:
        cmd = shutil.which("cmd.exe")
        if not cmd:
            self.skipTest("cmd.exe is not available")

        with tempfile.TemporaryDirectory(prefix="review-gate-install-bat-missing-") as temp_dir:
            temp_root = Path(temp_dir)
            staged_repo = self.stage_repo(temp_root, include_canonical_vsix=False)
            home_dir = temp_root / "home"
            install_dir = temp_root / "install root" / "review-gate-v2"

            completed = self.run_installer(
                [cmd, "/d", "/c", str(staged_repo / "V2" / "install.bat")],
                self.smoke_env(home_dir, install_dir),
                staged_repo,
            )
            self.assert_missing_canonical_artifact_failure(completed)


if __name__ == "__main__":
    unittest.main()
