#!/usr/bin/env python3
"""Run the shipped Phase 4 regression suites from the repository root."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
NODE = shutil.which("node") or "node"
TESTS_PYTHON = str(REPO_ROOT / "tests" / "python")


def build_suites() -> "OrderedDict[str, dict[str, object]]":
    return OrderedDict(
        [
            (
                "python-server",
                {
                    "description": "Phase 04-01 Python MCP regression suite",
                    "command": [PYTHON, "-m", "unittest", "tests/python/test_review_gate_v2_mcp.py", "-v"],
                    "env": {"PYTHONPATH": TESTS_PYTHON},
                },
            ),
            (
                "node-extension",
                {
                    "description": "Phase 04-02 Node extension runtime suite",
                    "command": [NODE, "--test", "tests/node/extension.runtime.test.js"],
                },
            ),
            (
                "installers",
                {
                    "description": "Phase 04-03 MCP helper fixtures plus installer smoke suite",
                    "command": [
                        PYTHON,
                        "-m",
                        "unittest",
                        "tests/python/test_update_mcp_config.py",
                        "tests/smoke/test_installers.py",
                        "-v",
                    ],
                    "env": {"PYTHONPATH": TESTS_PYTHON},
                },
            ),
        ]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List the available suite names and commands.")
    parser.add_argument(
        "--suite",
        action="append",
        choices=list(build_suites().keys()),
        help="Run one suite by name. Repeat to run multiple suites in the normal order.",
    )
    return parser.parse_args(argv)


def selected_suites(args: argparse.Namespace, suites: "OrderedDict[str, dict[str, object]]") -> list[tuple[str, dict[str, object]]]:
    if not args.suite:
        return list(suites.items())

    requested = set(args.suite)
    return [(name, suite) for name, suite in suites.items() if name in requested]


def list_suites(suites: "OrderedDict[str, dict[str, object]]") -> int:
    for name, suite in suites.items():
        command = " ".join(str(part) for part in suite["command"])
        print(f"{name}: {suite['description']}")
        print(f"  {command}")
    return 0


def run_suite(name: str, suite: dict[str, object]) -> int:
    command = [str(part) for part in suite["command"]]
    suite_env = os.environ.copy()
    for key, value in dict(suite.get("env", {})).items():
        if key == "PYTHONPATH" and suite_env.get("PYTHONPATH"):
            suite_env[key] = value + os.pathsep + suite_env["PYTHONPATH"]
        else:
            suite_env[key] = value
    print(f"==> {name}: {suite['description']}", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, env=suite_env, check=False)
    if result.returncode != 0:
        print(f"FAILED: {name} exited with status {result.returncode}", flush=True)
        return result.returncode
    print(f"PASS: {name}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    suites = build_suites()
    args = parse_args(argv)

    if args.list:
        return list_suites(suites)

    for name, suite in selected_suites(args, suites):
        exit_code = run_suite(name, suite)
        if exit_code != 0:
            return exit_code

    print("All requested Review Gate regression suites passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
