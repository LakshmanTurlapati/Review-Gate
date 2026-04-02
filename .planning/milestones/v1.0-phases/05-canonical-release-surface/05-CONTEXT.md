# Phase 5: Canonical Release Surface - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Make Review Gate V2 ship from one authoritative artifact and documentation surface so maintainers and users no longer have to guess which VSIX, rule file, version string, or install path is actually supported.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
- All implementation choices are at the agent's discretion because this is an infrastructure release-hardening phase.
- Preserve the current supported V2 runtime and version (`2.7.3`) unless a change is required to establish one canonical release surface.
- Prefer one committed canonical VSIX path and one documented install story; fallback build-output paths can exist as generated outputs, but they should not read like equal supported artifacts.
- Keep Phase 5 focused on authoritative release surface and documentation alignment, not new product features or distribution channels.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Release-facing files
- `V2/cursor-extension/package.json` — extension version and packaging metadata
- `V2/review-gate-v2-2.7.3.vsix` — current primary committed VSIX artifact
- `V2/cursor-extension/review-gate-v2-2.7.3.vsix` — duplicate committed VSIX artifact in build-output location
- `V2/ReviewGateV2.mdc` — current supported V2 rule file
- `V2/INSTALLATION.md` — detailed install and release-facing instructions
- `readme.md` — top-level public install guidance and artifact references

### Script surfaces
- `V2/install.sh`
- `V2/install.ps1`
- `V2/install.bat`

### Codebase maps
- `.planning/codebase/CONCERNS.md` — release artifact drift findings
- `.planning/codebase/TESTING.md` — new Phase 4 verification surface that Phase 5 should reuse

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 already aligned installers and docs around `ReviewGateV2.mdc` and `review-gate-v2-2.7.3.vsix`.
- Phase 4 added a repo-root regression runner, which gives Phase 5 a concrete verification command to use when narrowing the release surface.

### Established Patterns
- The repo currently contains two committed VSIX files with the same version and name in different directories.
- Public docs still describe one path as primary and the other as fallback, which reduces confusion versus before but still leaves two artifact surfaces in the repo.
- Install scripts still know about versioned VSIX filenames directly, so any canonicalization work has to keep runtime lookup and documentation aligned.

### Integration Points
- Whatever becomes canonical must remain consistent across `package.json`, installer scripts, top-level README guidance, and `V2/INSTALLATION.md`.
- The release surface should remain compatible with the Phase 4 regression runner and not break installer smoke mode or runtime verification paths.

</code_context>

<specifics>
## Specific Ideas

- Choose one committed canonical VSIX location and treat any other output location as generated or unsupported for release purposes.
- Add one small release manifest or shared source of truth for version, artifact basename, and supported rule file if that reduces string drift across scripts and docs.
- Update README and installation docs so they describe one authoritative install path instead of two co-equal artifact stories.
- Reuse the new regression runner when verifying release-surface changes.

</specifics>

<deferred>
## Deferred Ideas

- Marketplace publishing automation.
- Full CI release pipeline or auto-generated changelog tooling.
- Major packaging-system rewrite beyond what is needed to establish one authoritative local release surface.

</deferred>
