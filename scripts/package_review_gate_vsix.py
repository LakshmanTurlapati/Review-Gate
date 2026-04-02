#!/usr/bin/env python3
"""Canonical Review Gate VSIX packaging and metadata helper."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "V2" / "release-manifest.json"


def load_manifest() -> dict[str, str]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    required_fields = (
        "name",
        "version",
        "artifact_basename",
        "canonical_vsix_path",
        "rule_path",
        "extension_source_dir",
        "extension_package_json",
    )
    missing = [field for field in required_fields if not manifest.get(field)]
    if missing:
        raise ValueError(f"release manifest missing required fields: {', '.join(missing)}")
    return manifest


def repo_path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def load_extension_package(manifest: dict[str, str]) -> dict[str, object]:
    package_path = repo_path(manifest["extension_package_json"])
    with package_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_manifest(manifest: dict[str, str]) -> list[str]:
    errors: list[str] = []

    package_json = load_extension_package(manifest)
    canonical_vsix_path = repo_path(manifest["canonical_vsix_path"])
    extension_source_dir = repo_path(manifest["extension_source_dir"])
    rule_path = repo_path(manifest["rule_path"])

    if manifest["artifact_basename"] != canonical_vsix_path.name:
        errors.append("artifact_basename does not match canonical_vsix_path basename")

    if manifest["version"] != package_json.get("version"):
        errors.append("manifest version does not match V2/cursor-extension/package.json")

    if manifest["name"] != package_json.get("name"):
        errors.append("manifest name does not match V2/cursor-extension/package.json")

    if not extension_source_dir.is_dir():
        errors.append(f"extension source dir not found: {manifest['extension_source_dir']}")

    if not rule_path.is_file():
        errors.append(f"rule file not found: {manifest['rule_path']}")

    if canonical_vsix_path.exists():
        try:
            with zipfile.ZipFile(canonical_vsix_path) as archive:
                package_blob = json.loads(archive.read("extension/package.json"))
        except (KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            errors.append(f"canonical VSIX is invalid: {exc}")
        else:
            if package_blob.get("version") != manifest["version"]:
                errors.append("canonical VSIX package.json version does not match manifest")
            if package_blob.get("name") != manifest["name"]:
                errors.append("canonical VSIX package.json name does not match manifest")

    return errors


def print_field(manifest: dict[str, str], field: str) -> int:
    if field not in manifest:
        print(f"Unknown manifest field: {field}", file=sys.stderr)
        return 1
    print(manifest[field])
    return 0


def run_check(manifest: dict[str, str]) -> int:
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: {MANIFEST_PATH.relative_to(REPO_ROOT)} is internally consistent.")
    return 0


def package_vsix(manifest: dict[str, str]) -> int:
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    extension_source_dir = repo_path(manifest["extension_source_dir"])
    canonical_vsix_path = repo_path(manifest["canonical_vsix_path"])
    canonical_vsix_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "npm",
        "exec",
        "--",
        "@vscode/vsce",
        "package",
        "--out",
        str(canonical_vsix_path),
    ]
    completed = subprocess.run(command, cwd=extension_source_dir, check=False)
    if completed.returncode != 0:
        return completed.returncode

    print(str(canonical_vsix_path.relative_to(REPO_ROOT)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="package",
        choices=("package",),
        help="Action to run. Defaults to packaging the canonical VSIX.",
    )
    parser.add_argument("--field", help="Print a manifest field and exit.")
    parser.add_argument("--check", action="store_true", help="Validate manifest and package metadata.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest = load_manifest()

    if args.field:
        return print_field(manifest, args.field)

    if args.check:
        return run_check(manifest)

    return package_vsix(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
