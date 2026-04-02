"""Regression coverage for the canonical Review Gate release surface."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "V2" / "release-manifest.json"
HELPER_SCRIPT = REPO_ROOT / "scripts" / "package_review_gate_vsix.py"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
PACKAGE_JSON = json.loads((REPO_ROOT / MANIFEST["extension_package_json"]).read_text(encoding="utf-8"))
CANONICAL_VSIX_PATH = REPO_ROOT / MANIFEST["canonical_vsix_path"]
DUPLICATE_VSIX_PATH = REPO_ROOT / "V2" / "cursor-extension" / MANIFEST["artifact_basename"]
INSTALLERS = (
    REPO_ROOT / "V2" / "install.sh",
    REPO_ROOT / "V2" / "install.ps1",
    REPO_ROOT / "V2" / "install.bat",
)
DOCS = (
    REPO_ROOT / "V2" / "INSTALLATION.md",
    REPO_ROOT / "readme.md",
)
WORKSPACE_VSIX_REFERENCES = (
    f"V2/cursor-extension/{MANIFEST['artifact_basename']}",
    f"V2\\cursor-extension\\{MANIFEST['artifact_basename']}",
)


class ReleaseSurfaceTests(unittest.TestCase):
    maxDiff = None

    def run_helper(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HELPER_SCRIPT), *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_release_helper_check_passes(self) -> None:
        completed = self.run_helper("--check")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("V2/release-manifest.json", completed.stdout)

    def test_manifest_matches_extension_source_metadata(self) -> None:
        self.assertEqual(MANIFEST["name"], PACKAGE_JSON["name"])
        self.assertEqual(MANIFEST["version"], PACKAGE_JSON["version"])
        self.assertEqual(MANIFEST["artifact_basename"], CANONICAL_VSIX_PATH.name)
        self.assertEqual(MANIFEST["rule_path"], "V2/ReviewGateV2.mdc")

    def test_canonical_vsix_exists_and_embeds_matching_extension_metadata(self) -> None:
        self.assertTrue(CANONICAL_VSIX_PATH.exists(), f"Expected canonical VSIX at {CANONICAL_VSIX_PATH}")

        with zipfile.ZipFile(CANONICAL_VSIX_PATH) as archive:
            package_blob = json.loads(archive.read("extension/package.json"))

        self.assertEqual(package_blob["name"], MANIFEST["name"])
        self.assertEqual(package_blob["version"], MANIFEST["version"])

    def test_duplicate_workspace_vsix_is_absent(self) -> None:
        self.assertFalse(
            DUPLICATE_VSIX_PATH.exists(),
            f"Workspace VSIX should stay absent: {DUPLICATE_VSIX_PATH}",
        )

    def test_installers_reference_shared_release_metadata_and_no_workspace_vsix(self) -> None:
        for installer in INSTALLERS:
            with self.subTest(installer=installer.name):
                text = installer.read_text(encoding="utf-8")
                self.assertIn("package_review_gate_vsix.py", text)
                for reference in WORKSPACE_VSIX_REFERENCES:
                    self.assertNotIn(reference, text)

    def test_docs_describe_one_canonical_artifact_and_packaging_command(self) -> None:
        for document in DOCS:
            with self.subTest(document=document.name):
                text = document.read_text(encoding="utf-8")
                self.assertIn(MANIFEST["canonical_vsix_path"], text)
                self.assertIn(MANIFEST["rule_path"], text)
                self.assertIn("npm run package", text)
                self.assertIn("package_review_gate_vsix.py", text)
                for reference in WORKSPACE_VSIX_REFERENCES:
                    self.assertNotIn(reference, text)


if __name__ == "__main__":
    unittest.main()
