---
phase: 05-canonical-release-surface
verified: 2026-04-02T22:23:27Z
status: passed
score: 3/3 must-haves verified
---

# Phase 5: Canonical Release Surface Verification Report

**Phase Goal:** Maintainers can ship one authoritative Review Gate release whose docs and artifacts match the actual supported runtime.  
**Verified:** 2026-04-02T22:23:27Z  
**Status:** passed  
**Re-verification:** No

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Maintainer has one canonical release manifest and one packaging command that produce the shipped `V2/review-gate-v2-2.7.3.vsix` artifact. | ✓ VERIFIED | `V2/release-manifest.json` now defines the canonical version, artifact basename, VSIX path, rule path, and extension source dir; `scripts/package_review_gate_vsix.py --check` passed; `V2/cursor-extension/package.json` delegates `npm run package` and `npm run package:check` to the helper. |
| 2 | The committed `V2/cursor-extension/` build-output VSIX no longer exists as a second supported release artifact. | ✓ VERIFIED | `V2/cursor-extension/review-gate-v2-2.7.3.vsix` is absent, `.gitignore` ignores `V2/cursor-extension/*.vsix`, and `tests/python/test_release_surface.py` plus `python3 -m unittest tests/smoke/test_installers.py -v` passed with the narrowed root-only artifact contract. |
| 3 | Release metadata for version, artifact basename, and supported rule file live in one repo-owned source of truth instead of drifting across scripts and docs. | ✓ VERIFIED | `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat` resolve release fields through `scripts/package_review_gate_vsix.py`; `V2/INSTALLATION.md`, `readme.md`, and `tests/python/test_release_surface.py` all align to `V2/review-gate-v2-2.7.3.vsix` plus `V2/ReviewGateV2.mdc`; `python3 scripts/run_review_gate_regression_checks.py` passed with the new `release-surface` suite included. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `V2/release-manifest.json` | Single source of truth for the shipped release surface | ✓ VERIFIED | Defines `version`, `artifact_basename`, `canonical_vsix_path`, `rule_path`, and `extension_source_dir`. |
| `scripts/package_review_gate_vsix.py` | Canonical packaging helper and metadata interface | ✓ VERIFIED | Supports `--field`, `--check`, and packaging into the root `V2/` artifact path. |
| `V2/cursor-extension/package.json` | Maintainer-facing package entrypoint | ✓ VERIFIED | `npm run package` delegates to the helper instead of writing a workspace-local VSIX. |
| `.gitignore` | Guardrail against regenerating a tracked workspace VSIX | ✓ VERIFIED | Ignores `V2/cursor-extension/*.vsix` while preserving the committed root artifact. |
| `V2/install.sh`, `V2/install.ps1`, `V2/install.bat` | Canonical installer contract | ✓ VERIFIED | All three installers read release metadata through the helper and fail clearly when the root artifact is missing. |
| `tests/smoke/test_installers.py` | Root-only installer smoke coverage | ✓ VERIFIED | Stages minimal temp repos, verifies happy-path installs, and proves missing-canonical-artifact failures. |
| `V2/INSTALLATION.md`, `readme.md` | Public docs aligned to one supported release story | ✓ VERIFIED | Both docs mention the canonical root artifact, the supported V2 rule file, and the manifest-backed packaging command. |
| `tests/python/test_release_surface.py` | Dedicated release-surface regression suite | ✓ VERIFIED | Covers manifest/package metadata, root artifact presence, workspace artifact absence, installer references, and doc references. |
| `scripts/run_review_gate_regression_checks.py` | Single repo-root release-check entrypoint | ✓ VERIFIED | Includes `release-surface` alongside the existing Python, Node, and installer suites in the default run. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Manifest/helper contract is internally consistent | `python3 scripts/package_review_gate_vsix.py --check` | Passed | ✓ PASS |
| Installer scripts reference the helper and no workspace-VSIX fallback | `rg -n 'package_review_gate_vsix\.py|ReviewGateV2\.mdc' V2/install.sh V2/install.ps1 V2/install.bat` and `! rg -n 'cursor-extension[\\/].*review-gate-v2-.*\.vsix' V2/install.sh V2/install.ps1 V2/install.bat` | Passed | ✓ PASS |
| Installer smoke coverage proves root-only artifact behavior | `python3 -m unittest tests/smoke/test_installers.py -v` | Passed 6 tests with 4 explicit Windows-shell skips on this macOS host | ✓ PASS |
| Dedicated release-surface suite is runnable | `python3 -m unittest tests/python/test_release_surface.py -v` | Passed 6 tests | ✓ PASS |
| Repo-root runner advertises and runs the release-surface suite | `python3 scripts/run_review_gate_regression_checks.py --suite release-surface` and `python3 scripts/run_review_gate_regression_checks.py` | Both passed | ✓ PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
| --- | --- | --- | --- |
| `REL-01` | Maintainer can produce one canonical VSIX artifact and documentation that matches the shipped version and supported rule file. | ✓ SATISFIED | Manifest-backed packaging helper, root-only installer contract, aligned docs, `tests/python/test_release_surface.py`, and the repo-root regression runner all passed. |

### Residual Risk

No blocking gaps remain for `REL-01`.

Residual host-confidence risk remains in the Windows smoke branches because this verification host did not provide `pwsh`, `powershell.exe`, or `cmd.exe`. Those branches stay explicitly covered and will execute automatically on a host that has the Windows shells available.

---

_Verified: 2026-04-02T22:23:27Z_  
_Verifier: Codex_
