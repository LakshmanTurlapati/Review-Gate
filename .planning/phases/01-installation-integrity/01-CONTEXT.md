# Phase 1: Installation Integrity - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Make Review Gate V2 install and uninstall correctly on supported platforms using the repo's current artifacts and without breaking unrelated user Cursor MCP configuration.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
- All implementation choices are at the agent's discretion because this is an infrastructure hardening phase.
- Prefer fixes that preserve existing user configuration and require the least manual recovery during install or uninstall.
- Treat the current V2 runtime (`V2/ReviewGateV2.mdc`, the Python MCP server, the Cursor extension, and current 2.7.3 artifact naming) as the supported product surface.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Installer behavior
- `V2/install.sh` — macOS/Linux install flow, dependency install, MCP config generation, rule and VSIX setup
- `V2/install.ps1` — Windows PowerShell install flow and MCP config merge behavior
- `V2/install.bat` — Windows batch install fallback and MCP config behavior
- `V2/uninstall.sh` — macOS/Linux uninstall flow
- `V2/uninstall.ps1` — Windows PowerShell uninstall flow
- `V2/uninstall.bat` — Windows batch uninstall flow

### Runtime artifacts and docs
- `V2/mcp.json` — canonical MCP config template for Review Gate V2
- `V2/INSTALLATION.md` — detailed manual installation guide
- `readme.md` — public install instructions and supported-path messaging
- `V2/ReviewGateV2.mdc` — current V2 rule file
- `V2/cursor-extension/package.json` — current extension version metadata

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The install scripts already create virtual environments, copy runtime files, and write MCP config; this phase should fix those flows rather than replace them wholesale.

### Established Patterns
- Platform-specific behavior is split across `install.sh`, `install.ps1`, and `install.bat`, with similar but not identical logic.
- Documentation currently duplicates install guidance between `readme.md` and `V2/INSTALLATION.md`.

### Integration Points
- Installer outputs must stay compatible with Cursor MCP configuration under `~/.cursor/mcp.json` or `%USERPROFILE%\\.cursor\\mcp.json`.
- Rule paths, VSIX filenames, and extension version strings must align with the committed V2 runtime files.

</code_context>

<specifics>
## Specific Ideas

- Preserve unrelated MCP server entries during install.
- Eliminate shell-specific breakage in the POSIX installer.
- Use the shipped V2 rule and current VSIX version consistently across scripts and docs.

</specifics>

<deferred>
## Deferred Ideas

None - infrastructure phase.

</deferred>
