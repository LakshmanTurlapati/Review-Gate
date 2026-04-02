# Technology Stack

**Analysis Date:** 2026-04-02

## Languages

**Primary:**
- Python 3.8+ - local MCP server and speech pipeline in `V2/review_gate_v2_mcp.py`; minimum version is documented in `V2/INSTALLATION.md`
- JavaScript (CommonJS, Node-based extension host runtime) - Cursor extension entrypoint in `V2/cursor-extension/extension.js`, declared by `V2/cursor-extension/package.json`

**Secondary:**
- Shell - macOS/Linux installation and uninstallation in `V2/install.sh` and `V2/uninstall.sh`
- PowerShell - Windows installation and uninstallation in `V2/install.ps1` and `V2/uninstall.ps1`
- Batch - Windows fallback installation and uninstallation in `V2/install.bat` and `V2/uninstall.bat`
- JSON - MCP configuration template in `V2/mcp.json` and extension manifest in `V2/cursor-extension/package.json`
- Markdown rule files - V2 Cursor rule in `V2/ReviewGateV2.mdc`; legacy V1 rule in `ReviewGate.mdc`

## Runtime

**Environment:**
- Cursor/VS Code extension host compatible with `vscode` engine `^1.60.0`, declared in `V2/cursor-extension/package.json`
- Python 3.8+ local process launched from Cursor MCP configuration in `V2/mcp.json`, `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`
- Node version is not pinned by `.nvmrc`, `.node-version`, or similar repo files; use the runtime bundled with Cursor for `V2/cursor-extension/extension.js`

**Package Manager:**
- `pip` / `venv` - installs server dependencies from `V2/requirements_simple.txt` into the local environment created by `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`
- `npm` - used only for extension packaging; `V2/cursor-extension/package.json` defines `npm run package` as `vsce package`
- Lockfile: missing; no `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `requirements.lock`, or `poetry.lock` detected

## Frameworks

**Core:**
- Model Context Protocol Python SDK `mcp>=1.9.2` - stdio MCP server implementation and tool registration in `V2/review_gate_v2_mcp.py`
- VS Code/Cursor Extension API - popup UI, webview, file picker, output channel, and command registration in `V2/cursor-extension/extension.js`
- Faster-Whisper `>=1.0.0` - local speech-to-text transcription in `V2/review_gate_v2_mcp.py`

**Testing:**
- Not detected - no test framework config or test files were found in the repository root or under `V2/`

**Build/Dev:**
- `@vscode/vsce` `^2.32.0` - packages the extension defined by `V2/cursor-extension/package.json`
- Python `venv` - runtime isolation created by `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`
- Prebuilt VSIX artifacts - `V2/review-gate-v2-2.7.3.vsix` and `V2/cursor-extension/review-gate-v2-2.7.3.vsix`

## Key Dependencies

**Critical:**
- `mcp>=1.9.2` - required for `Server`, stdio transport, and MCP tool plumbing in `V2/review_gate_v2_mcp.py`
- `faster-whisper>=1.0.0` - enables microphone transcription handled by `V2/review_gate_v2_mcp.py`
- `@vscode/vsce^2.32.0` - required to rebuild the VSIX from `V2/cursor-extension/package.json`

**Infrastructure:**
- `Pillow>=10.0.0` - packaged as a Python dependency in `V2/requirements_simple.txt`
- `typing-extensions>=4.14.0` - packaged as a Python dependency in `V2/requirements_simple.txt`
- `asyncio` - listed in `V2/requirements_simple.txt`; the runtime code in `V2/review_gate_v2_mcp.py` also imports Python stdlib `asyncio`
- SoX CLI - external audio capture dependency invoked from `V2/cursor-extension/extension.js` and installed by `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`

## Configuration

**Environment:**
- Configure Cursor MCP launch in `V2/mcp.json` or let `V2/install.sh`, `V2/install.ps1`, or `V2/install.bat` write `~/.cursor/mcp.json` or `%USERPROFILE%\.cursor\mcp.json`
- Set `PYTHONPATH`, `PYTHONUNBUFFERED=1`, and `REVIEW_GATE_MODE=cursor_integration` exactly as shown in `V2/mcp.json`
- Load the V2 rule from `V2/ReviewGateV2.mdc` when using the MCP-based workflow; the root `ReviewGate.mdc` describes the older terminal-driven flow
- No `.env` files or other repo-local secret configuration files were detected during mapping

**Build:**
- Extension manifest and packaging config live in `V2/cursor-extension/package.json`
- No bundler, transpiler, or type-checker config was detected; `V2/cursor-extension/extension.js` ships as plain CommonJS
- Installation behavior is encoded in platform scripts: `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`

## Platform Requirements

**Development:**
- Cursor IDE is required for both the extension in `V2/cursor-extension/extension.js` and the MCP entry defined by `V2/mcp.json`
- Python 3.8+, `pip`, and virtual environment support are required by `V2/INSTALLATION.md` and all installer scripts
- SoX and microphone permissions are required to enable speech capture used by `V2/cursor-extension/extension.js`
- macOS/Linux installs expect `brew` or `apt-get` pathways in `V2/install.sh`; Windows installs use Scoop in `V2/install.ps1` and Chocolatey-aware fallback logic in `V2/install.bat`

**Production:**
- Deployment target is a local developer workstation, not a hosted service
- The installed runtime lives under `~/cursor-extensions/review-gate-v2/` or `%USERPROFILE%\cursor-extensions\review-gate-v2\`, with Cursor launching the Python server through `~/.cursor/mcp.json` or `%USERPROFILE%\.cursor\mcp.json`

---

*Stack analysis: 2026-04-02*
