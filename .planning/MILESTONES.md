# Milestones

## v1.0 milestone (Shipped: 2026-04-02)

**Phases completed:** 5 phases, 16 plans, 33 tasks

**Key accomplishments:**

- V2/install.sh now installs Python dependencies through the created venv interpreter and runs SoX plus MCP validation through a portable timeout helper that works on default macOS and Linux shells
- Windows install and uninstall now merge or remove only the `review-gate-v2` MCP entry through a shared Python config mutator.
- Cross-platform runtime scripts now resolve the shipped 2.7.3 VSIX, install and remove ReviewGateV2.mdc, and preserve unrelated Cursor MCP config on POSIX uninstall
- V2 installation docs now point to the shipped 2.7.3 VSIX, the ReviewGateV2.mdc rule, and merge-safe MCP configuration updates
- Session-scoped trigger, acknowledgement, and response routing for Review Gate MCP popup exchanges
- Explicit busy, cancelled, timeout, and speech-ownership recovery on top of the Phase 2 session-scoped IPC contract
- Per-user runtime roots with session-owned trigger, response, speech, and audio artifacts under `review-gate-v2/<user>/sessions/<trigger_id>/`
- Protocol-versioned Review Gate session envelopes with per-session tokens, atomic JSON IPC writes, and redacted status heartbeats across the MCP server and Cursor extension
- Review Gate’s popup now runs under a nonce-based CSP, ships its own inline SVG icons, and renders attachment previews through DOM APIs instead of HTML injection
- Redacted Review Gate runtime diagnostics and added runtime-secret HMAC proof so the extension rejects stale or forged first triggers before claiming a new MCP popup session
- Stdlib-only Review Gate MCP regression harness covering signed triggers, authenticated session envelopes, and timeout cleanup without launching Cursor
- Built-in node:test coverage for authenticated trigger intake, busy and cancelled popup outcomes, and attachment response persistence in the shipped Cursor extension
- Shared installer smoke mode, update_mcp_config fixture coverage, and one repo-root command that runs the full Phase 4 regression set before release
- Established one manifest-backed release contract, rewired packaging to it, and removed the duplicate committed workspace VSIX.
- Rewired every supported installer to the manifest-backed release helper and tightened smoke coverage around the root-only VSIX contract.
- Aligned public release guidance to the canonical artifact story and added a release-surface regression suite to the existing repo-root runner.

---
