# Coding Conventions

**Analysis Date:** 2026-04-02

## Naming Patterns

**Files:**
- Use flat, purpose-driven filenames instead of deep module trees. The JavaScript extension entrypoint is `V2/cursor-extension/extension.js`, the Python MCP server is `V2/review_gate_v2_mcp.py`, and platform installers are `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`.
- Keep runtime-specific manifests next to the runtime they configure: `V2/cursor-extension/package.json`, `V2/requirements_simple.txt`, and `V2/mcp.json`.
- Package artifacts use versioned kebab-case filenames and are committed alongside source, for example `V2/review-gate-v2-2.7.3.vsix` and `V2/cursor-extension/review-gate-v2-2.7.3.vsix`.

**Functions:**
- JavaScript in `V2/cursor-extension/extension.js` uses lowerCamelCase helper and handler names such as `getTempPath`, `checkTriggerFile`, `openReviewGatePopup`, `handleReviewMessage`, `startNodeRecording`, and `stopNodeRecording`.
- Python in `V2/review_gate_v2_mcp.py` uses snake_case for functions and underscore-prefixed private methods such as `get_temp_path`, `_initialize_whisper_model`, `_wait_for_user_input`, and `_write_speech_response`.
- Bash in `V2/install.sh` and `V2/uninstall.sh` uses lower_snake_case utility helpers like `log_error`, `log_progress`, and `log_success`.
- PowerShell in `V2/install.ps1` follows Verb-Noun naming such as `Write-Error-Log`, `Write-Progress-Log`, and `Write-Step-Log`.

**Variables:**
- JavaScript runtime state is stored in module-level mutable lowerCamelCase bindings in `V2/cursor-extension/extension.js`, for example `chatPanel`, `reviewGateWatcher`, `mcpStatus`, `currentTriggerData`, and `currentRecording`.
- Python locals and object state are snake_case in `V2/review_gate_v2_mcp.py`, with underscore-prefixed attributes for internals such as `self._whisper_model`, `self._whisper_error`, and `self._last_attachments`.
- Shell and batch scripts use uppercase environment-style variables such as `CURSOR_MCP_FILE`, `REVIEW_GATE_DIR`, `EXTENSION_FILE`, and `TEMP_DIR` in `V2/install.sh`, `V2/uninstall.sh`, and `V2/install.bat`.
- PowerShell favors PascalCase variables like `$ScriptDir`, `$CursorMcpFile`, `$ReviewGateDir`, and `$ExtensionFile` in `V2/install.ps1`.

**Types:**
- Python classes use PascalCase and typed signatures in `V2/review_gate_v2_mcp.py`, for example `ReviewGateServer` and signatures like `def get_temp_path(filename: str) -> str:`.
- JavaScript in `V2/cursor-extension/extension.js` is untyped and uses implicit object shapes for webview messages, trigger files, and temp-file payloads.
- Cross-process JSON payloads use lowercase keys with underscores, such as `trigger_id`, `mcp_integration`, `audio_file`, and `event_type` in `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py`.

## Code Style

**Formatting:**
- No formatter config is detected. The repository does not contain `.prettierrc*`, `eslint.config.*`, `.editorconfig`, `biome.json`, `pyproject.toml`, or `setup.cfg`.
- Preserve the file-local formatting already present:
- `V2/cursor-extension/extension.js` uses 4-space indentation, semicolons, single-quoted JavaScript strings, CommonJS `require(...)`, and a large template literal that embeds HTML, CSS, and browser-side JavaScript.
- `V2/review_gate_v2_mcp.py` uses 4-space indentation, docstrings for selected helpers and methods, standard library imports before MCP imports, and typed Python signatures.
- `V2/install.sh` and `V2/uninstall.sh` use `#!/bin/bash`, `set -e`, uppercase constants, and compact inline shell functions.
- `V2/install.ps1` uses 4-space indentation, `$ErrorActionPreference = "Stop"`, cmdlets, and explicit `try/catch`.
- `V2/install.bat` uses uppercase `set` variables, `REM` comments, and explicit `if errorlevel` branching.
- `V2/cursor-extension/package.json` uses 2-space JSON indentation.

**Linting:**
- No lint runner or lint config is defined in `V2/cursor-extension/package.json` or elsewhere in the repository.
- Style is enforced manually by following the existing conventions in each language-specific file instead of a shared formatter or linter.

## Import Organization

**Order:**
1. Runtime or standard-library imports first.
   Examples: `const vscode = require('vscode');` and `const fs = require('fs');` at the top of `V2/cursor-extension/extension.js`, and `import asyncio`, `import json`, `import logging`, `import os` at the top of `V2/review_gate_v2_mcp.py`.
2. Optional dependencies behind a guarded fallback when availability is variable.
   Example: `try: from faster_whisper import WhisperModel ... except ImportError:` in `V2/review_gate_v2_mcp.py`.
3. Framework and protocol imports after the standard library.
   Example: `from mcp.server import Server` and `from mcp.types import ...` in `V2/review_gate_v2_mcp.py`.

**Path Aliases:**
- Not used. The repository relies on built-in modules, raw filesystem paths, and direct relative references such as `main: "./extension.js"` in `V2/cursor-extension/package.json`.

## Error Handling

**Patterns:**
- Wrap IO, parsing, and process boundaries in defensive `try/catch` or `try/except` blocks instead of letting exceptions terminate the feature. Current examples include `checkTriggerFile`, `logUserInput`, `handleImageUpload`, `handleSpeechToText`, `validateSoxSetup`, `startNodeRecording`, and `stopNodeRecording` in `V2/cursor-extension/extension.js`, plus tool dispatch, speech monitoring, and Whisper setup in `V2/review_gate_v2_mcp.py`.
- Fail hard only for mandatory prerequisites. `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat` stop when Python or critical files are missing, but degrade optional steps such as SoX support, `faster-whisper` installation, and automated VSIX installation to warnings plus manual instructions.
- Prefer user-visible fallback over exception propagation. `V2/cursor-extension/extension.js` posts UI error states or empty transcriptions when recording/transcription fails, and `V2/review_gate_v2_mcp.py` returns `TextContent` messages that begin with `ERROR:` or `TIMEOUT:` instead of bubbling failures back through the server.
- Keep validation inline and close to the boundary:
- `checkTriggerFile` in `V2/cursor-extension/extension.js` accepts only trigger files whose `editor` is `cursor` and whose `system` is `review-gate-v2`.
- `sendMessage` in `V2/cursor-extension/extension.js` rejects empty submissions unless image attachments exist.
- `handleImageUpload` plus `getMimeType` in `V2/cursor-extension/extension.js` constrain image handling to known file types.
- `validateSoxSetup` and the minimum-size check in `stopNodeRecording` in `V2/cursor-extension/extension.js` validate command availability, mic access, timeout behavior, and non-empty audio.
- `V2/install.sh` and `V2/install.ps1` validate existing `~/.cursor/mcp.json` as JSON before merging or recreating configuration.
- There is no centralized schema or validator library. Message shapes, trigger files, and temp-file payloads are validated field by field inside `V2/cursor-extension/extension.js`, `V2/review_gate_v2_mcp.py`, and the install scripts.

## Logging

**Framework:** `console` plus VS Code output channels in `V2/cursor-extension/extension.js`; Python `logging` in `V2/review_gate_v2_mcp.py`; colored log helper functions in `V2/install.sh`, `V2/install.ps1`, `V2/install.bat`, and `V2/uninstall.sh`.

**Patterns:**
- The extension keeps operational logs near the interaction boundary. `logMessage(...)` and `logUserInput(...)` in `V2/cursor-extension/extension.js` log to `console`, append to the `Review Gate V2 ゲート` output channel, and mirror selected data into temp files.
- The MCP server in `V2/review_gate_v2_mcp.py` always logs to stderr and attempts to add a temp-file handler at `review_gate_v2.log`.
- Installer and uninstaller scripts use colored wrappers such as `log_success`, `Write-Success-Log`, and `%log_success%` so every branch prints a human-readable status line.
- Emoji-heavy log text is normal in both `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py`. Match that style if extending existing workflows in those files.

## Comments

**When to Comment:**
- Use brief operational comments to explain why a branch, timeout, or cleanup step exists. This is the dominant comment style in `V2/cursor-extension/extension.js`, `V2/review_gate_v2_mcp.py`, `V2/install.sh`, and `V2/install.ps1`.
- Keep comments attached to concrete workflow details such as platform differences, retry logic, file-based IPC, backup/restore behavior, or UI state changes.
- Prefer short headers over long prose. Existing files use section comments like `// Handle messages from webview`, `# Validate SoX installation and microphone access`, and `"""Set up MCP request handlers"""`.

**JSDoc/TSDoc:**
- Not used in `V2/cursor-extension/extension.js`.
- Python docstrings are used selectively in `V2/review_gate_v2_mcp.py` for helpers, methods, and monitoring routines.
- Shell, PowerShell, and batch files use header comments plus inline comments instead of formal doc blocks.

## Function Design

**Size:** Large workflow functions are acceptable in the current codebase when the logic is tightly coupled. `getReviewGateHTML(...)` in `V2/cursor-extension/extension.js` and the main bodies of `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat` are monolithic by design.

**Parameters:**
- Use primitive parameters for focused helpers such as `getTempPath(filename)` in `V2/cursor-extension/extension.js` and `get_temp_path(filename: str)` in `V2/review_gate_v2_mcp.py`.
- Use option objects or loose dicts when a workflow needs multiple optional fields. Current examples are `openReviewGatePopup(context, options = {})` in `V2/cursor-extension/extension.js` and MCP tool `arguments: dict` throughout `V2/review_gate_v2_mcp.py`.

**Return Values:**
- JavaScript helpers in `V2/cursor-extension/extension.js` are mostly side-effect driven. They mutate module state, show UI, write temp files, or post messages instead of returning rich values.
- Python tool handlers in `V2/review_gate_v2_mcp.py` return MCP payloads such as `list[TextContent]`, status dicts, or boolean success values.
- Scripts communicate success through exit codes, created files, and console logs rather than reusable return objects.

## Module Design

**Exports:**
- `V2/cursor-extension/extension.js` exports only `activate` and `deactivate` via `module.exports`.
- `V2/review_gate_v2_mcp.py` is a script-style module centered on the `ReviewGateServer` class and its entrypoint path.
- `V2/install.sh`, `V2/install.ps1`, `V2/install.bat`, `V2/uninstall.sh`, `V2/uninstall.ps1`, and `V2/uninstall.bat` are standalone executables, not shared libraries.

**Barrel Files:**
- Not used. There are no re-export modules or shared internal packages.
- Packaging is direct and artifact-based. `V2/cursor-extension/package.json` defines a single build script, `package`, that runs `vsce package`, and the installers copy prebuilt VSIX files from `V2/cursor-extension/review-gate-v2-2.7.3.vsix` or `V2/review-gate-v2-2.7.3.vsix` instead of building during install.

---

*Convention analysis: 2026-04-02*
