# Testing Patterns

**Analysis Date:** 2026-04-02

## Test Framework

**Runner:**
- Not detected. The repository does not contain `pytest`, `unittest`, `jest`, `vitest`, `playwright`, or `cypress` configuration files.
- Config: Not applicable. No `jest.config.*`, `vitest.config.*`, `pytest.ini`, `pyproject.toml`, `.github/workflows`, or dedicated test package metadata was found under `V2/` or the repository root.

**Assertion Library:**
- None configured. Current verification relies on shell exit codes, log-string checks, file existence checks, and manual UI confirmation in `V2/install.sh`, `V2/install.ps1`, `V2/install.bat`, and `readme.md`.

**Run Commands:**
```bash
cd V2 && ./install.sh
pwsh -File V2/install.ps1
sox --version
sox -d -r 16000 -c 1 test.wav trim 0 3 && rm test.wav
```
- `cd V2 && ./install.sh` runs the macOS/Linux installation flow in `V2/install.sh`, including prerequisite validation, MCP config generation, a short server smoke test, VSIX copy/install, and final file checks.
- `pwsh -File V2/install.ps1` runs the Windows installation flow in `V2/install.ps1`, including similar smoke checks plus manual fallback instructions.
- `sox --version` and `sox -d -r 16000 -c 1 test.wav trim 0 3 && rm test.wav` come from the troubleshooting block in `readme.md` and are the documented manual checks for speech prerequisites.

## Test File Organization

**Location:**
- Not applicable. No `*.test.*`, `*.spec.*`, or `__tests__` paths exist in the repository.
- Verification logic lives inside production-adjacent files:
- `V2/install.sh`
- `V2/install.ps1`
- `V2/install.bat`
- `readme.md`

**Naming:**
- Manual checks are described by feature rather than suite name in `readme.md`: `Manual Popup Test`, `Agent Integration Test`, `Speech Test`, `Image Test`, and `Full Workflow Test`.
- Smoke artifacts are temp files whose names match runtime behavior, such as `mcp_test.log`, `review_gate_v2.log`, `review_gate_response*.json`, `mcp_response*.json`, and `review_gate_speech_response_*.json` in `V2/install.sh`, `V2/cursor-extension/extension.js`, and `V2/review_gate_v2_mcp.py`.

**Structure:**
```text
No dedicated test tree exists.

Current verification is embedded in:
- `V2/install.sh` for macOS/Linux smoke checks
- `V2/install.ps1` for Windows smoke checks
- `V2/install.bat` for Windows setup plus manual verification handoff
- `readme.md` for human-driven end-to-end validation
```

## Test Structure

**Suite Organization:**
```bash
# `V2/install.sh`
source venv/bin/activate
TEMP_DIR=$(python3 -c 'import tempfile; print(tempfile.gettempdir())')
timeout 5s python review_gate_v2_mcp.py > "$TEMP_DIR/mcp_test.log" 2>&1 || true
deactivate

if grep -q "Review Gate 2.0 server initialized" "$TEMP_DIR/mcp_test.log"; then
    log_success "MCP server test successful"
else
    log_warning "MCP server test inconclusive (may be normal)"
fi
```

**Patterns:**
- Setup pattern: use the real installation path, real Python virtual environment, real MCP config file, and real temp directory. `V2/install.sh` and `V2/install.ps1` do not simulate infrastructure.
- Teardown pattern: delete temp artifacts after the smoke check. `V2/install.sh` removes `mcp_test.log` and later cleans `review_gate_*` and `mcp_response*`; `V2/install.ps1` removes matching temp files; `V2/review_gate_v2_mcp.py` and `V2/cursor-extension/extension.js` also clean response and trigger files after use.
- Assertion pattern: assertions are string-based or file-based. `V2/install.sh` and `V2/install.ps1` look for the server initialization log line, while installer final verification checks that files like `review_gate_v2_mcp.py`, the MCP config, and the virtual environment exist.

## Mocking

**Framework:** Not used.

**Patterns:**
```text
Current verification uses live dependencies instead of mocks:
- real `sox` processes in `V2/cursor-extension/extension.js`
- real temp-file IPC between `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py`
- real Cursor CLI / VSIX installation attempts in `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`
```

**What to Mock:**
- No repository policy is implemented because there are no automated tests.
- If automated coverage is added, the natural mock seams are the VS Code API and webview messaging in `V2/cursor-extension/extension.js`, `fs` and `child_process.spawn` in `V2/cursor-extension/extension.js`, and `WhisperModel`, filesystem polling, and temp-file writes in `V2/review_gate_v2_mcp.py`.

**What NOT to Mock:**
- Current verification intentionally exercises live integration boundaries: `sox`, local temp files, generated `~/.cursor/mcp.json`, the real VSIX artifact, and manual Cursor actions documented in `readme.md`.

## Fixtures and Factories

**Test Data:**
```javascript
// `V2/cursor-extension/extension.js`
const responseData = {
    timestamp: timestamp,
    trigger_id: triggerId,
    user_input: inputText,
    response: inputText,
    message: inputText,
    attachments: attachments,
    event_type: eventType,
    source: 'review_gate_extension'
};
```
- The repository does not maintain fixture files or factories. Runtime JSON payloads like the one above, plus speech trigger/response objects in `V2/review_gate_v2_mcp.py`, are the closest thing to reusable test data.

**Location:**
- Temp fixtures are created in the OS temp directory by `logUserInput(...)` in `V2/cursor-extension/extension.js`, `_trigger_cursor_popup_immediately(...)` and `_write_speech_response(...)` in `V2/review_gate_v2_mcp.py`, and the installer smoke checks in `V2/install.sh` and `V2/install.ps1`.
- No `fixtures/`, `factories/`, or dedicated test-data directory exists in the repository.

## Coverage

**Requirements:** None enforced. No coverage tooling, threshold, or CI gate is present in the repository.

**View Coverage:**
```bash
# Not available
```

## Test Types

**Unit Tests:**
- Not used. No isolated unit tests exist for `V2/cursor-extension/extension.js`, `V2/review_gate_v2_mcp.py`, or the installer scripts.

**Integration Tests:**
- Installer smoke tests are the closest thing to automated integration coverage.
- `V2/install.sh` validates SoX/Python prerequisites, JSON config creation, brief MCP server startup, VSIX presence, and final file installation.
- `V2/install.ps1` follows the same pattern on Windows using `Start-Job` for the short MCP server launch.
- `V2/install.bat` validates setup and config creation but explicitly skips the MCP server smoke test and leaves verification manual.

**E2E Tests:**
- No E2E framework is configured.
- Human-driven end-to-end verification is documented in `readme.md`:
- open the popup manually with `Cmd+Shift+R`
- ask Cursor to call `review_gate_chat`
- speak into the microphone and confirm transcription
- upload an image and send it
- run the full Review Gate workflow until the popup loops correctly

## Common Patterns

**Async Testing:**
```powershell
# `V2/install.ps1`
$testJob = Start-Job -ScriptBlock {
    param($venvPython, $reviewGateDir)
    & $venvPython (Join-Path $reviewGateDir "review_gate_v2_mcp.py")
} -ArgumentList $venvPython, $ReviewGateDir

Start-Sleep -Seconds 5
Stop-Job $testJob -ErrorAction SilentlyContinue
```
- The repository verifies async startup by running the real server briefly, then inspecting output or handing off to manual observation.
- Runtime code also follows polling-with-timeout patterns in `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py`, but those patterns are not covered by dedicated automated tests.

**Error Testing:**
```bash
# `readme.md`
tail -f /tmp/review_gate_v2.log
sox --version
sox -d -r 16000 -c 1 test.wav trim 0 3 && rm test.wav
cat ~/.cursor/mcp.json
```
- Error diagnosis is manual. The project documents troubleshooting commands in `readme.md` instead of maintaining automated failure-mode tests.
- Installers do include fallback branches for missing SoX, missing `faster-whisper`, invalid MCP JSON, or failed VSIX installation, but those branches are not asserted by a formal test suite.

## Verification Gaps

**No Automated Regression Harness:**
- There are no repo-level tests, no lint step, no formatter check, and no CI config to stop regressions in `V2/cursor-extension/extension.js`, `V2/review_gate_v2_mcp.py`, or the install scripts.

**Extension UI Is Untested:**
- The webview UI in `V2/cursor-extension/extension.js` has no automated checks for message rendering, drag-and-drop, clipboard image ingestion, speech-state transitions, or MCP status changes.

**IPC Protocol Is Untested:**
- File-based handoff between `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py` is only exercised indirectly through manual runs. There are no tests for malformed JSON, duplicate trigger files, stale response files, or race conditions.

**Cross-Platform Installer Coverage Is Uneven:**
- `V2/install.sh` and `V2/install.ps1` run a short MCP smoke test, but `V2/install.bat` prints `MCP server test skipped (manual verification required)` and never validates a live server start.

**Packaging Drift Is Unchecked:**
- `V2/cursor-extension/package.json` defines `vsce package`, but there is no automated verification that the committed artifacts `V2/review-gate-v2-2.7.3.vsix` and `V2/cursor-extension/review-gate-v2-2.7.3.vsix` match the current source in `V2/cursor-extension/extension.js`.

**Speech and Whisper Failure Paths Are Manual Only:**
- SoX validation, microphone permissions, small-audio handling, Whisper initialization fallbacks, and speech-trigger polling are implemented in `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py`, but no repeatable test coverage exists for them.

---

*Testing analysis: 2026-04-02*
