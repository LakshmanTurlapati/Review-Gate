# Codebase Structure

**Analysis Date:** 2026-04-02

## Directory Layout

```text
[project-root]/
├── .planning/                 # Local planning workspace; generated analysis docs are written here
├── V2/                        # Review Gate V2 product files
│   ├── cursor-extension/      # Cursor/VS Code extension source and packaged VSIX
│   ├── review_gate_v2_mcp.py  # Python MCP server entry point
│   ├── ReviewGateV2.mdc       # V2 Cursor rule
│   ├── install.*              # Platform-specific installers
│   ├── uninstall.*            # Platform-specific uninstallers
│   ├── mcp.json               # Sample MCP server configuration
│   └── requirements_simple.txt # Python dependency list
├── assets/                    # README documentation images
├── ReviewGate.mdc             # Legacy root-level Review Gate rule
├── readme.md                  # Repository overview and usage guide
└── .gitignore                 # Ignore rules for Python, Node, build, and runtime files
```

## Directory Purposes

**`.planning/`:**
- Purpose: Workspace-local planning output used by the GSD workflow.
- Contains: generated docs such as `.planning/codebase/ARCHITECTURE.md` and `.planning/codebase/STRUCTURE.md`.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`

**`V2/`:**
- Purpose: The active Review Gate V2 implementation and distribution bundle.
- Contains: the MCP server in `V2/review_gate_v2_mcp.py`, the Cursor rule in `V2/ReviewGateV2.mdc`, installers such as `V2/install.sh`, uninstallers such as `V2/uninstall.sh`, packaged VSIX files, and support docs.
- Key files: `V2/review_gate_v2_mcp.py`, `V2/ReviewGateV2.mdc`, `V2/install.sh`, `V2/mcp.json`, `V2/INSTALLATION.md`

**`V2/cursor-extension/`:**
- Purpose: Cursor/VS Code extension package.
- Contains: the extension manifest in `V2/cursor-extension/package.json`, the runtime implementation in `V2/cursor-extension/extension.js`, the extension icon, and a packaged VSIX.
- Key files: `V2/cursor-extension/package.json`, `V2/cursor-extension/extension.js`, `V2/cursor-extension/review-gate-v2-2.7.3.vsix`

**`assets/`:**
- Purpose: Repository documentation assets referenced from `readme.md`.
- Contains: images only.
- Key files: `assets/snippet.png`

## Key File Locations

**Entry Points:**
- `V2/cursor-extension/package.json`: Cursor extension manifest, activation events, command contribution, keybinding, and `main` pointer to `V2/cursor-extension/extension.js`.
- `V2/cursor-extension/extension.js`: Extension-host runtime entry point exporting `activate` and `deactivate`.
- `V2/review_gate_v2_mcp.py`: Python MCP server entry point invoked through `asyncio.run(main())`.
- `V2/install.sh`: macOS/Linux installation entry point.
- `V2/install.ps1`: Windows PowerShell installation entry point.
- `V2/install.bat`: Windows Command Prompt installation entry point.

**Configuration:**
- `V2/mcp.json`: Sample Cursor MCP configuration template.
- `V2/requirements_simple.txt`: Python dependency list for the MCP server.
- `.gitignore`: Global ignore patterns for Python, Node, build, and runtime artifacts.

**Core Logic:**
- `V2/review_gate_v2_mcp.py`: MCP tool exposure, temp-file trigger creation, response polling, heartbeat logging, speech monitoring, Whisper transcription, and shutdown cleanup.
- `V2/cursor-extension/extension.js`: Cursor extension lifecycle, trigger polling, popup orchestration, HTML/CSS/JS webview generation, image handling, SoX recording, and response writing.
- `V2/ReviewGateV2.mdc`: V2 agent protocol that tells Cursor to transition into Review Gate.
- `ReviewGate.mdc`: Legacy non-MCP protocol based on a root-level Python script.

**Testing:**
- Not detected in the repository. No `tests/`, `__tests__/`, `spec/`, or dedicated test config files are present at the repo root or under `V2/`.

## Naming Conventions

**Files:**
- Python runtime files use `snake_case`: `V2/review_gate_v2_mcp.py`.
- Shell and platform scripts use lowercase imperative names: `V2/install.sh`, `V2/uninstall.sh`, `V2/install.ps1`, `V2/uninstall.bat`.
- Extension entry files use VS Code defaults: `V2/cursor-extension/package.json`, `V2/cursor-extension/extension.js`.
- Rule files use capitalized product names with `.mdc`: `V2/ReviewGateV2.mdc`, `ReviewGate.mdc`.
- Packaged artifacts include the semantic version in the filename: `V2/review-gate-v2-2.7.3.vsix`, `V2/cursor-extension/review-gate-v2-2.7.3.vsix`.

**Directories:**
- Product/version directories are top-level and explicit: `V2/`.
- The extension is nested under a descriptive package directory: `V2/cursor-extension/`.
- Documentation assets use a generic static-assets directory: `assets/`.
- Planning output is hidden under `.planning/`.

## Where to Add New Code

**New Feature:**
- MCP/server behavior: add it in `V2/review_gate_v2_mcp.py`.
- Cursor extension behavior or popup orchestration: add it in `V2/cursor-extension/extension.js`.
- Rule/protocol updates: edit `V2/ReviewGateV2.mdc` for V2 behavior or `ReviewGate.mdc` only if the legacy flow is intentionally being changed.
- Tests: no existing test location is established in the current repo.

**New Component/Module:**
- Current extension code is not split into modules; all extension-side implementation lives in `V2/cursor-extension/extension.js`.
- Current server code is not split into packages; all MCP-server behavior lives in `V2/review_gate_v2_mcp.py`.
- If code is kept consistent with the existing layout, place new extension-side sibling files in `V2/cursor-extension/` and new Python-side sibling files in `V2/`, then wire them into `V2/cursor-extension/extension.js` or `V2/review_gate_v2_mcp.py`.

**Utilities:**
- There is no shared `utils/` directory.
- Shared helpers currently stay inline near their caller, for example `get_temp_path()` in `V2/review_gate_v2_mcp.py` and `getTempPath()` in `V2/cursor-extension/extension.js`.

## Special Directories

**`.planning/codebase/`:**
- Purpose: Generated codebase reference documents for planning/execution workflows.
- Generated: Yes
- Committed: No

**`V2/cursor-extension/`:**
- Purpose: Extension package source plus packaged extension artifact.
- Generated: No
- Committed: Yes

**`assets/`:**
- Purpose: Documentation screenshots used by `readme.md`.
- Generated: No
- Committed: Yes

## Placement Guidance

**UI and popup changes:**
- Keep popup layout, styling, and browser-side behavior together in `V2/cursor-extension/extension.js` because the current webview is generated from a single template literal there.

**MCP protocol changes:**
- Update `V2/review_gate_v2_mcp.py` together with `V2/cursor-extension/extension.js` when changing trigger, acknowledgement, response, or speech file formats because those contracts are duplicated across both runtimes.

**Installer changes:**
- macOS/Linux install behavior belongs in `V2/install.sh`.
- Windows install behavior belongs in `V2/install.ps1` and `V2/install.bat`.
- Sample config changes belong in `V2/mcp.json`.

**Documentation changes:**
- End-user product overview belongs in `readme.md`.
- Detailed install instructions belong in `V2/INSTALLATION.md`.
- Rule text belongs in `V2/ReviewGateV2.mdc` and `ReviewGate.mdc`.

---

*Structure analysis: 2026-04-02*
