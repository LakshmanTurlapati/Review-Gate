# Phase 2: Session Routing Reliability - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Make Review Gate V2 reliably route each popup round-trip to the correct active session so overlapping, stale, or partially cleaned temp files do not corrupt the user exchange.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
- All implementation choices are at the agent's discretion because this is an infrastructure hardening phase.
- Keep the shipped temp-file IPC transport for this phase; harden routing and recovery before considering bigger transport changes.
- Preserve the current single-popup UX unless a change is required to prevent cross-session corruption.
- Prefer shared protocol helpers/constants if they reduce drift between the Python MCP server and the Cursor extension.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Runtime session flow
- `V2/review_gate_v2_mcp.py` — trigger creation, extension acknowledgement wait, user-response polling, timeout behavior, speech side channel
- `V2/cursor-extension/extension.js` — trigger polling, popup activation, global session state, response-file writes, speech request flow

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md` — runtime layers and data-flow map
- `.planning/codebase/CONCERNS.md` — concurrency/security concerns and fragile areas
- `.planning/codebase/INTEGRATIONS.md` — exact temp-file protocol and platform paths

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The MCP server already waits on `review_gate_ack_<trigger_id>.json` and already prefers `review_gate_response_<trigger_id>.json` before generic fallbacks.
- The extension already includes `trigger_id` in acknowledgements and MCP response payloads, which gives this phase a stable routing key to build around.

### Established Patterns
- The Python server currently writes one shared trigger file plus three shared backup trigger files and then polls several response filenames, including generic fallbacks.
- The extension currently stores one module-level `currentTriggerData`, one `chatPanel`, and one `currentRecording`, so a newer trigger can overwrite the prior in-flight session before the earlier response is submitted.
- `logUserInput()` writes four response files for the same MCP submission, including generic `review_gate_response.json` and `mcp_response.json`, which increases stale-response leakage risk.

### Integration Points
- Phase 2 changes must keep the `review_gate_chat` tool working through the existing Cursor extension and MCP server runtime.
- Any file-naming or payload changes must stay synchronized between `V2/review_gate_v2_mcp.py` and `V2/cursor-extension/extension.js`.
- Speech-to-text and manual popup flows both depend on trigger-linked state and should not regress while hardening session routing.

</code_context>

<specifics>
## Specific Ideas

- Make trigger ownership deterministic so a new tool call cannot silently hijack an existing active popup exchange.
- Eliminate or sharply constrain generic response fallback files during active MCP sessions; session-scoped files should be authoritative.
- Add explicit stale-session cleanup and timeout recovery so users get a clear failure path instead of an indefinite wait.
- Centralize temp-file naming helpers or protocol constants where practical so trigger, ack, response, and speech file semantics do not drift between runtimes.

</specifics>

<deferred>
## Deferred Ideas

- Full transport replacement away from temp files.
- Major extension-file modularization beyond what is needed to make this phase safe and testable.

</deferred>
