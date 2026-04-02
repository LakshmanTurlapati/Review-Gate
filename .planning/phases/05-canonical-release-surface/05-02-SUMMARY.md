---
phase: 05-canonical-release-surface
plan: "02"
subsystem: installers
tags: [installers, smoke, manifest, release]
requires:
  - phase: "05-01"
    provides: "Manifest-backed canonical artifact metadata and root-only VSIX surface"
provides:
  - "Installers that resolve the canonical artifact and rule path through the shared release helper"
  - "Explicit missing-artifact failures instead of workspace-VSIX fallback logic"
  - "Smoke coverage that stages only the canonical root artifact and proves failure when it is absent"
affects: [REL-01, install.sh, install.ps1, install.bat, smoke-tests]
tech-stack:
  added: []
  patterns: [helper-driven installer metadata lookup, staged smoke repo fixture, missing-canonical-artifact regression]
key-files:
  created: []
  modified: [V2/install.sh, V2/install.ps1, V2/install.bat, tests/smoke/test_installers.py]
key-decisions:
  - "Had each installer shell out to `scripts/package_review_gate_vsix.py --field ...` instead of copying manifest parsing logic into shell."
  - "Kept the install-time behavior explicit: installers do not build the VSIX, they require the canonical artifact to already exist."
  - "Staged isolated temp repo copies in smoke tests so missing-artifact failures can be exercised without mutating the real checkout."
patterns-established:
  - "Installer smoke tests now build a minimal staged repo rooted around `V2/release-manifest.json` plus the helper, instead of assuming the live checkout layout."
requirements-completed: [REL-01]
duration: 1 session
completed: 2026-04-02
---

# Phase 5 Plan 02: Canonical installer contract and root-only smoke coverage

**Rewired every supported installer to the manifest-backed release helper and tightened smoke coverage around the root-only VSIX contract.**

## Accomplishments

- Removed the `V2/cursor-extension/` artifact fallback from `install.sh`, `install.ps1`, and `install.bat`.
- Made every installer read the canonical artifact basename, canonical VSIX path, and rule path through the shared release helper.
- Updated smoke coverage so staged installs pass with only the root `V2/` artifact present and fail clearly when that canonical artifact is missing.

## Task Commits

1. **Task 1 and Task 2: Rewire installers and tighten smoke coverage together** - `21d602e` (`fix`)

The installer API change and the smoke harness change landed in one atomic commit because the staged smoke fixtures needed to evolve at the same time as the runtime lookup contract.

## Files Created/Modified

- `V2/install.sh` - Reads release fields through the helper, copies only the canonical root VSIX, and fails clearly when it is absent.
- `V2/install.ps1` - Mirrors the same manifest-driven artifact and rule resolution on PowerShell.
- `V2/install.bat` - Mirrors the same manifest-driven artifact and rule resolution on batch.
- `tests/smoke/test_installers.py` - Stages minimal temp repos, verifies happy-path installs from the root artifact, and asserts missing-canonical-artifact failures.

## Verification

- `rg -n 'package_review_gate_vsix\.py|ReviewGateV2\.mdc' V2/install.sh V2/install.ps1 V2/install.bat`
- `! rg -n 'cursor-extension[\\/].*review-gate-v2-.*\.vsix' V2/install.sh V2/install.ps1 V2/install.bat`
- `python3 -m unittest tests/smoke/test_installers.py -v`

## Issues Encountered

- This host does not provide `pwsh`, `powershell.exe`, or `cmd.exe`, so the Windows smoke tests remained explicit skips while the POSIX smoke path and staged missing-artifact failure path executed normally.

## Next Phase Readiness

Docs and release gating can now describe one real installer contract instead of trying to explain competing artifact paths.
