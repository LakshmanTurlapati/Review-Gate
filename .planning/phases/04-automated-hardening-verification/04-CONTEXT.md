# Phase 4: Automated Hardening Verification - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Add repeatable automated regression checks for the shipped Review Gate V2 runtime so maintainers can validate the hardened server, extension IPC flow, and installer behavior before release.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
- All implementation choices are at the agent's discretion because this is an infrastructure verification phase.
- Prefer a low-dependency test stack that works in the current repo without introducing a heavy frontend or CI platform rewrite.
- Build tests around the current shipped runtime surface (`V2/review_gate_v2_mcp.py`, `V2/cursor-extension/extension.js`, installer scripts, and `V2/update_mcp_config.py`) rather than inventing a replacement architecture first.
- Favor seams that keep Phase 4 focused on verification; only refactor production code when needed to make important behavior testable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Runtime and installer surfaces
- `V2/review_gate_v2_mcp.py` — Python MCP server, session routing, security checks, timeout handling, speech side channel
- `V2/cursor-extension/extension.js` — Cursor extension host, popup lifecycle, session routing, status monitoring, image/speech helpers
- `V2/install.sh` — macOS/Linux installer and smoke checks
- `V2/install.ps1` — Windows PowerShell installer and smoke checks
- `V2/install.bat` — Windows batch installer fallback
- `V2/update_mcp_config.py` — merge/remove helper already shared by install and uninstall flows

### Codebase maps
- `.planning/codebase/TESTING.md` — current testing gaps and likely mock seams
- `.planning/codebase/CONCERNS.md` — fragile areas worth covering first
- `.planning/codebase/ARCHITECTURE.md` — end-to-end flow for trigger, ack, response, speech, and popup state
- `.planning/codebase/STACK.md` — current language/tooling constraints

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The repo already has helper-driven session and security behavior in both runtimes; Phase 4 can target those helpers directly instead of only testing giant end-to-end flows.
- `V2/update_mcp_config.py` already isolates the trickiest installer-side JSON merge logic and is a natural target for repeatable tests.

### Established Patterns
- No test framework or CI exists in-repo today.
- The extension remains a single large CommonJS file, so tests may need exported helpers or extracted pure functions to avoid brittle whole-extension harnesses.
- Installer behavior currently relies on shell or PowerShell smoke paths plus manual inspection; that suggests fixture-based config tests and script-level smoke wrappers are higher value than trying to fully emulate Cursor.

### Integration Points
- Phase 4 must validate the hardened Phase 2 and Phase 3 behavior, especially session routing, authenticated IPC, status heartbeat handling, and cleanup semantics.
- Tests should cover installer MCP config preservation without requiring destructive changes to the user's real `~/.cursor/mcp.json`.
- The best low-friction runtime available locally is Python 3.14 plus Node 25, which makes stdlib `unittest` and built-in `node:test` viable even without extra package dependencies.

</code_context>

<specifics>
## Specific Ideas

- Add Python tests for trigger creation, authenticated ack/response parsing, timeout or busy outcomes, and cleanup helpers in `V2/review_gate_v2_mcp.py`.
- Add Node tests for session path helpers, initial trigger validation, popup or message helper behavior, and authenticated envelope handling in `V2/cursor-extension/extension.js`.
- Add fixture-driven installer smoke tests around `V2/update_mcp_config.py` and any script-level config generation that can be checked without launching real Cursor.
- Add one documented test entrypoint so maintainers can run the regression set consistently from the repo root.

</specifics>

<deferred>
## Deferred Ideas

- Full UI browser automation against a real Cursor webview.
- Cross-platform CI matrix or marketplace publishing automation.
- Replacing the current monolithic extension architecture purely for test elegance.

</deferred>
