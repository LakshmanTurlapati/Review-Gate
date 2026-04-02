# Phase 3: Scoped IPC Security - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Reduce the trust and exposure of Review Gate's local IPC and popup surface so sensitive data stays session-scoped, malformed or untrusted temp-file payloads do not alter active state, and the webview no longer depends on unsafe external asset and HTML patterns.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
- All implementation choices are at the agent's discretion because this is an infrastructure hardening phase.
- Build on the Phase 2 session-scoped trigger, acknowledgement, response, and speech contract rather than replacing temp-file IPC outright.
- Prefer changes that reduce exposure in the shipped runtime without forcing a broader product redesign or queue-based UX.
- Treat webview security as part of this phase even though the UI stays visually similar; local asset loading and HTML safety are in scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Runtime surfaces
- `V2/review_gate_v2_mcp.py` — session-scoped IPC helpers, temp-log writes, JSON parsing, speech trigger handling, and cleanup behavior
- `V2/cursor-extension/extension.js` — temp-file routing, user input logging, session cleanup, popup HTML, CDN asset loading, and dynamic DOM rendering

### Codebase maps
- `.planning/codebase/CONCERNS.md` — security concerns and fragile areas for IPC, logs, and the webview
- `.planning/codebase/ARCHITECTURE.md` — current server/extension/webview data flow
- `.planning/codebase/INTEGRATIONS.md` — exact temp-file and log paths used by the runtime
- `.planning/codebase/STACK.md` — runtime/tooling constraints for Python, Cursor, and the extension host

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 2 already standardized the active popup flow on session-scoped trigger, acknowledgement, response, and speech filenames keyed by `trigger_id`.
- Both runtimes now have helper-based naming (`_session_file` in Python and `getSessionFilePath()` in JavaScript), which gives this phase a single place to tighten path and payload policy.

### Established Patterns
- The Python server still writes logs to a shared temp log file (`review_gate_v2.log`) and the extension still appends user activity to `review_gate_user_inputs.log` in the temp directory.
- The extension still accepts temp-file JSON based mostly on `system`, `editor`, and `trigger_id` fields; malformed or forged local payloads are not strongly rejected yet.
- The popup webview still loads Font Awesome from `cdnjs.cloudflare.com` and still uses `innerHTML` for image-preview rendering and other HTML assembly patterns inside `V2/cursor-extension/extension.js`.

### Integration Points
- Security hardening must preserve the current `review_gate_chat` flow and Phase 2 recovery semantics for busy, cancelled, and timeout outcomes.
- Speech-to-text, image attachments, and manual popup usage all touch temp storage and webview rendering, so cleanup and validation changes must not break those features.
- Phase 4 will depend on whatever seams this phase creates for automated verification, so validation helpers and explicit cleanup hooks are preferable to hidden side effects.

</code_context>

<specifics>
## Specific Ideas

- Move transient IPC and log artifacts out of broad shared temp locations where practical, or at minimum into a Review Gate-owned session subtree with predictable cleanup and narrower exposure.
- Add stricter envelope validation before either runtime trusts a trigger, acknowledgement, response, or speech message.
- Stop writing raw user feedback and attachment metadata to broad temp logs by default.
- Replace external webview asset loading with local assets and remove or minimize `innerHTML`-based rendering paths so the popup does not depend on CDN reachability or unsafe HTML interpolation.

</specifics>

<deferred>
## Deferred Ideas

- Full replacement of temp-file IPC with sockets, named pipes, or an authenticated daemon.
- Large UX redesigns or multi-session conversation management beyond what security hardening strictly requires.

</deferred>
