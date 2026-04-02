---
status: partial
phase: 01-installation-integrity
source: [01-VERIFICATION.md]
started: 2026-04-02T19:37:51Z
updated: 2026-04-02T19:37:51Z
---

## Current Test

Awaiting human platform smoke testing for the native installation paths.

## Tests

### 1. macOS install smoke on default macOS with an existing multi-server ~/.cursor/mcp.json
expected: install.sh completes without shell redirection or missing-timeout failures, preserves unrelated MCP servers, and installs review-gate-v2, ReviewGateV2.mdc, and review-gate-v2-2.7.3.vsix.
result: pending

### 2. Windows PowerShell install/uninstall smoke with an existing multi-server %USERPROFILE%\.cursor\mcp.json
expected: install.ps1 merges only review-gate-v2, uninstall.ps1 removes only review-gate-v2, and unrelated MCP servers remain unchanged.
result: pending

### 3. Windows batch install/uninstall smoke with an existing multi-server %USERPROFILE%\.cursor\mcp.json
expected: install.bat and uninstall.bat preserve unrelated MCP servers while installing or removing the current V2 assets.
result: pending

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

None yet.
