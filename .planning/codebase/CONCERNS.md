# Codebase Concerns

**Analysis Date:** 2026-04-02

## Tech Debt

**Monolithic extension host implementation:**
- Issue: `V2/cursor-extension/extension.js` is a 2238-line file that mixes command registration, temp-file IPC, webview HTML, image handling, speech recording, and lifecycle cleanup.
- Files: `V2/cursor-extension/extension.js`, `V2/cursor-extension/package.json`
- Impact: Small changes in one area can regress unrelated behavior. Global mutable state (`chatPanel`, `currentTriggerData`, `currentRecording`) makes overlapping tool calls hard to reason about.
- Fix approach: Split `V2/cursor-extension/extension.js` into `commands`, `ipc`, `webview`, and `audio` modules, and move per-request state into a session map keyed by trigger ID.

**Dead MCP server code paths:**
- Issue: `V2/review_gate_v2_mcp.py` implements `_handle_unified_review_gate`, `_handle_get_user_input`, `_handle_quick_review`, `_handle_file_review`, `_handle_ingest_text`, and `_handle_shutdown_mcp`, but `list_tools()` and `call_tool()` expose and dispatch only `review_gate_chat`.
- Files: `V2/review_gate_v2_mcp.py:177`, `V2/review_gate_v2_mcp.py:215`, `V2/review_gate_v2_mcp.py:244`, `V2/review_gate_v2_mcp.py:384`, `V2/review_gate_v2_mcp.py:460`, `V2/review_gate_v2_mcp.py:497`, `V2/review_gate_v2_mcp.py:534`, `V2/review_gate_v2_mcp.py:595`
- Impact: Unreachable handlers can rot silently, and maintainers cannot tell which behaviors are supported versus abandoned.
- Fix approach: Either expose these tools in `list_tools()` and add tests for them, or delete the unused handlers and simplify the protocol surface.

**Protocol duplication across JS and Python:**
- Issue: Trigger names, fallback filenames, and response semantics are hard-coded in both `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py`.
- Files: `V2/cursor-extension/extension.js:82`, `V2/cursor-extension/extension.js:183`, `V2/cursor-extension/extension.js:376`, `V2/cursor-extension/extension.js:1858`, `V2/review_gate_v2_mcp.py:391`, `V2/review_gate_v2_mcp.py:644`, `V2/review_gate_v2_mcp.py:680`, `V2/review_gate_v2_mcp.py:769`, `V2/review_gate_v2_mcp.py:858`, `V2/review_gate_v2_mcp.py:1011`, `V2/review_gate_v2_mcp.py:1148`
- Impact: Any protocol change requires synchronized edits in two runtimes. Drift shows up as timeouts and silent failures instead of compile-time errors.
- Fix approach: Define a versioned protocol schema in-repo and generate or import shared constants from a single source.

**Release artifact drift:**
- Issue: Built VSIX artifacts are committed in two locations, while docs still reference an older version.
- Files: `V2/review-gate-v2-2.7.3.vsix`, `V2/cursor-extension/review-gate-v2-2.7.3.vsix`, `V2/INSTALLATION.md:85`, `V2/INSTALLATION.md:191`, `readme.md:125`
- Impact: Manual installation and release packaging can drift away from source, and outdated instructions remain easy to follow by mistake.
- Fix approach: Keep one canonical VSIX output, build it in CI, and update docs/version strings from one release manifest.

## Known Bugs

**POSIX installer dependency commands are malformed:**
- Symptoms: `./install.sh` can fail during dependency installation or create unexpected files named like `=1.9.2`, because version specifiers are passed unquoted in shell commands.
- Files: `V2/install.sh:146`, `V2/install.sh:150`, `V2/install.sh:155`
- Trigger: Run `V2/install.sh` on a POSIX shell.
- Workaround: Activate the created venv manually and run `pip install -r requirements_simple.txt`.

**macOS installer uses GNU `timeout`, which is not standard on macOS:**
- Symptoms: microphone validation and MCP smoke test fail even on otherwise correct macOS installs.
- Files: `V2/install.sh:82`, `V2/install.sh:268`
- Trigger: Run `V2/install.sh` on a default macOS machine without GNU coreutils.
- Workaround: skip those checks manually, or install `gtimeout` and patch the script locally before running it.

**Windows installers overwrite existing MCP configuration:**
- Symptoms: existing entries in `%USERPROFILE%\\.cursor\\mcp.json` disappear after installation, despite docs claiming safe merging.
- Files: `V2/install.ps1:229`, `V2/install.ps1:287`, `V2/install.bat:160`, `V2/install.bat:181`, `readme.md:119`
- Trigger: Run `V2/install.ps1` or `V2/install.bat` on a machine that already has other MCP servers configured.
- Workaround: restore the backup file and merge `review-gate-v2` into the prior JSON manually.

**Rule installation points at the wrong file:**
- Symptoms: installers do not install the V2 rule automatically because they look for `ReviewGate.mdc` inside `V2/`, while the V2 rule file is `V2/ReviewGateV2.mdc`.
- Files: `V2/install.sh:333`, `V2/install.ps1:406`, `V2/install.bat:283`, `V2/ReviewGateV2.mdc`, `ReviewGate.mdc`
- Trigger: Run any installer from the `V2/` directory.
- Workaround: manually copy the contents of `V2/ReviewGateV2.mdc` into Cursor rules as described in `readme.md:132`.

**Manual installation docs reference a stale VSIX version:**
- Symptoms: the guide tells users to install `review-gate-v2-2.6.4.vsix`, but the repository contains `2.7.3`.
- Files: `V2/INSTALLATION.md:85`, `V2/INSTALLATION.md:191`, `V2/review-gate-v2-2.7.3.vsix`, `V2/cursor-extension/review-gate-v2-2.7.3.vsix`
- Trigger: Follow `V2/INSTALLATION.md` literally for manual installation.
- Workaround: select the `2.7.3` VSIX file manually.

## Security Considerations

**Unauthenticated temp-file IPC:**
- Risk: any local process can create or modify `review_gate_trigger*.json`, `review_gate_ack_*.json`, `review_gate_response*.json`, `mcp_response*.json`, and `review_gate_speech_response_*.json` under `/tmp` or the system temp directory and inject fake prompts or responses.
- Files: `V2/cursor-extension/extension.js:8`, `V2/cursor-extension/extension.js:183`, `V2/cursor-extension/extension.js:376`, `V2/cursor-extension/extension.js:1858`, `V2/review_gate_v2_mcp.py:47`, `V2/review_gate_v2_mcp.py:644`, `V2/review_gate_v2_mcp.py:680`, `V2/review_gate_v2_mcp.py:769`, `V2/review_gate_v2_mcp.py:1011`, `V2/review_gate_v2_mcp.py:1148`
- Current mitigation: the extension checks `editor` and `system`, and the server checks `trigger_id` when it is present.
- Recommendations: use a private per-user state directory with restrictive permissions, add a per-session secret or signature, use atomic write-then-rename, and reject generic fallback filenames for active sessions.

**Sensitive data is written to shared temp logs and response files:**
- Risk: raw user input, local file paths, speech transcripts, and image attachments are written to temp storage and logs, where other local processes can inspect them.
- Files: `V2/cursor-extension/extension.js:65`, `V2/cursor-extension/extension.js:89`, `V2/cursor-extension/extension.js:1748`, `V2/cursor-extension/extension.js:1781`, `V2/cursor-extension/extension.js:1884`, `V2/review_gate_v2_mcp.py:57`, `V2/review_gate_v2_mcp.py:700`, `V2/review_gate_v2_mcp.py:782`, `V2/review_gate_v2_mcp.py:1112`, `V2/review_gate_v2_mcp.py:1148`
- Current mitigation: partial cleanup on shutdown and some response-file deletion after reads.
- Recommendations: stop logging raw payloads by default, redact file paths and user content, store logs inside extension-managed storage, and delete transient files immediately after successful handoff.

**Webview XSS and supply-chain exposure:**
- Risk: the webview runs scripts, loads Font Awesome from a CDN, has no explicit Content Security Policy, and uses `innerHTML` with interpolated values from tool/user-controlled fields.
- Files: `V2/cursor-extension/extension.js:445`, `V2/cursor-extension/extension.js:553`, `V2/cursor-extension/extension.js:1194`
- Current mitigation: chat messages rendered by `addMessage()` use `textContent`.
- Recommendations: add a strict CSP using `webview.cspSource`, vendor icons locally, remove `innerHTML`, and sanitize every string interpolated into HTML attributes or DOM fragments.

## Performance Bottlenecks

**Extension-host busy polling with synchronous filesystem access:**
- Problem: the extension polls trigger files every 250ms and status every 2 seconds, while using `existsSync`, `readFileSync`, `statSync`, `appendFileSync`, and `writeFileSync` on the extension-host thread.
- Files: `V2/cursor-extension/extension.js:77`, `V2/cursor-extension/extension.js:105`, `V2/cursor-extension/extension.js:122`, `V2/cursor-extension/extension.js:143`, `V2/cursor-extension/extension.js:190`, `V2/cursor-extension/extension.js:224`
- Cause: file-based IPC and synchronous I/O inside hot polling loops.
- Improvement path: move to an evented transport or at minimum replace sync calls with async I/O and debounce file checks per trigger.

**Whole-file image and audio buffering:**
- Problem: images and audio are loaded entirely into memory, converted to base64, duplicated into webview state, serialized to JSON files, and in some cases returned again through MCP.
- Files: `V2/cursor-extension/extension.js:1161`, `V2/cursor-extension/extension.js:1194`, `V2/cursor-extension/extension.js:1776`, `V2/cursor-extension/extension.js:1838`, `V2/review_gate_v2_mcp.py:715`, `V2/review_gate_v2_mcp.py:364`, `V2/review_gate_v2_mcp.py:1148`
- Cause: no attachment size limits, synchronous reads, and repeated base64 copies.
- Improvement path: add strict file-size caps, compress or downscale images, stream large payloads, and pass file references instead of embedding repeated base64 blobs.

**Speech model loads on every server startup:**
- Problem: Faster-Whisper is initialized during `ReviewGateServer` construction, even when speech features are never used.
- Files: `V2/review_gate_v2_mcp.py:97`, `V2/review_gate_v2_mcp.py:115`
- Cause: eager model initialization in `__init__`.
- Improvement path: lazy-load speech support on first transcription request and make it an opt-in feature flag.

## Fragile Areas

**Speech capture and transcription pipeline:**
- Files: `V2/cursor-extension/extension.js:1824`, `V2/cursor-extension/extension.js:1945`, `V2/cursor-extension/extension.js:2030`, `V2/cursor-extension/extension.js:2125`, `V2/review_gate_v2_mcp.py:984`, `V2/review_gate_v2_mcp.py:1085`, `V2/install.sh`, `V2/install.ps1`, `V2/install.bat`
- Why fragile: recording depends on SoX availability, microphone permissions, temp-file coordination, two processes, and timing-based cleanup. A failure in any stage becomes a timeout or generic speech error.
- Safe modification: change one stage at a time and test the full record-stop-transcribe loop on each supported OS.
- Test coverage: Not detected.

**Installer matrix and onboarding flow:**
- Files: `V2/install.sh`, `V2/install.ps1`, `V2/install.bat`, `V2/INSTALLATION.md`, `readme.md`
- Why fragile: three separate installers implement different dependency setup, config merge behavior, and validation logic. Documentation does not stay in sync with these scripts.
- Safe modification: consolidate on one tested installer per OS or generate scripts from a shared template and add smoke tests.
- Test coverage: Not detected.

**Single-panel, single-session state model:**
- Files: `V2/cursor-extension/extension.js:17`, `V2/cursor-extension/extension.js:22`, `V2/cursor-extension/extension.js:241`, `V2/cursor-extension/extension.js:401`, `V2/cursor-extension/extension.js:457`, `V2/cursor-extension/extension.js:2080`
- Why fragile: the extension keeps one global chat panel, one current trigger, and one recording object. New tool calls can overwrite earlier state before the previous interaction has finished.
- Safe modification: isolate state per trigger ID, reject overlapping sessions explicitly, and add cleanup tied to request completion rather than global panel disposal.
- Test coverage: Not detected.

## Scaling Limits

**Single active interaction session:**
- Current capacity: one visible panel and effectively one active request state.
- Limit: overlapping `review_gate_chat` calls can race because response routing depends on shared globals in `V2/cursor-extension/extension.js`.
- Scaling path: queue sessions, allow multiple panel instances, or enforce a session manager keyed by trigger ID.

**Attachment and temp-disk growth are unbounded:**
- Current capacity: no enforced size or count limits for attached images or recorded audio.
- Limit: large screenshots or repeated retries can exhaust extension memory and temp storage before cleanup runs.
- Scaling path: add attachment count/size limits, reject oversized files early, and run aggressive background cleanup for abandoned temp files.

## Dependencies at Risk

**Unpinned Python dependency set:**
- Risk: `V2/requirements_simple.txt` uses lower bounds only, and `faster-whisper` has heavy, platform-sensitive transitive dependencies.
- Impact: fresh installs can behave differently across days and operating systems, especially on Windows and CPU-only systems.
- Migration plan: generate a locked requirements file with hashes and make speech-related packages an optional extra instead of a hard default.

**No Node lockfile for extension packaging:**
- Risk: `V2/cursor-extension/package.json` is present without `package-lock.json`, `pnpm-lock.yaml`, or `yarn.lock`.
- Impact: VSIX builds are not reproducible, and packaging drift is hard to investigate.
- Migration plan: commit a lockfile and build the VSIX in CI from source rather than storing duplicate artifacts.

**External CDN dependency in webview:**
- Risk: the popup depends on `cdnjs.cloudflare.com` for icons.
- Impact: enterprise network restrictions or CDN outages can degrade the UI even when the local extension is otherwise healthy.
- Migration plan: vendor icons in the extension or replace them with inline SVG assets.

## Missing Critical Features

**Automated verification for the extension, server, and installers:**
- Problem: no CI workflow, no extension-host tests, no Python unit tests, and no installer smoke tests were detected.
- Blocks: safe refactors, reproducible releases, and platform parity claims.

**Authenticated and validated IPC contract:**
- Problem: the temp-file transport has no schema validation, no file ownership checks, and no session authentication.
- Blocks: secure local multi-process communication and trustworthy error diagnosis.

## Test Coverage Gaps

**Extension host and webview behavior:**
- What's not tested: panel lifecycle, trigger/ack/response routing, concurrent requests, image upload handling, and speech UI state transitions.
- Files: `V2/cursor-extension/extension.js`, `V2/cursor-extension/package.json`
- Risk: regressions surface only in manual Cursor sessions.
- Priority: High

**Installer behavior across operating systems:**
- What's not tested: dependency installation, MCP config merge, global rule installation, VSIX install, and rollback behavior.
- Files: `V2/install.sh`, `V2/install.ps1`, `V2/install.bat`, `V2/INSTALLATION.md`, `readme.md`
- Risk: onboarding failures reach end users immediately and differ by platform.
- Priority: High

**Python MCP server and speech worker:**
- What's not tested: popup trigger creation, response-file matching, image attachment return path, speech-trigger processing, and temp-file cleanup.
- Files: `V2/review_gate_v2_mcp.py`, `V2/requirements_simple.txt`
- Risk: timeouts, stale files, and cross-platform race conditions go unnoticed until runtime.
- Priority: High

---

*Concerns audit: 2026-04-02*
