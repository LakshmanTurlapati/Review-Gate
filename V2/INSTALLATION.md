# Review Gate V2 - Installation Guide

## Overview
Review Gate V2 is a local MCP (Model Context Protocol) server plus a Cursor extension and a Cursor rule file. This guide covers the current shipped V2 install surface:
- `V2/review-gate-v2-2.7.3.vsix` - primary shipped VSIX artifact
- `V2/cursor-extension/review-gate-v2-2.7.3.vsix` - fallback build-output VSIX location
- `V2/ReviewGateV2.mdc` - current V2 Cursor rule
- `V2/mcp.json` - sample MCP configuration entry

Use the automated installer when possible. If you install manually, keep any existing Cursor MCP servers and merge only the `review-gate-v2` entry into `mcpServers`.

## Prerequisites

### System Requirements
- macOS, Linux, or Windows 10/11
- Cursor IDE (latest version)
- Python 3.8 or higher
- pip (Python package manager)

### Platform-Specific Requirements

**macOS/Linux:**
- Homebrew (macOS) or package manager (Linux)
- SoX audio system for speech-to-text

**Windows:**
- PowerShell or Command Prompt with administrator access
- Chocolatey (optional, for SoX installation)

## Quick Installation (Automated)

### macOS/Linux
```bash
# Clone the repository
git clone https://github.com/LakshmanTurlapati/Review-Gate.git
cd Review-Gate/V2

# Make installer executable
chmod +x install.sh

# Run installer
./install.sh
```

The installer uses `V2/review-gate-v2-2.7.3.vsix` first and falls back to `V2/cursor-extension/review-gate-v2-2.7.3.vsix` if needed. Existing `~/.cursor/mcp.json` servers are preserved while `review-gate-v2` is added or updated.

### Windows PowerShell
```powershell
# Clone the repository
git clone https://github.com/LakshmanTurlapati/Review-Gate.git
cd Review-Gate/V2

# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run installer
.\install.ps1
```

The Windows installer preserves unrelated MCP servers by merging the `review-gate-v2` entry into your existing Cursor configuration instead of replacing the whole file.

### Windows Command Prompt
```cmd
# Clone the repository
git clone https://github.com/LakshmanTurlapati/Review-Gate.git
cd Review-Gate\V2

# Run installer
install.bat
```

Like the PowerShell flow, the batch installer keeps other `mcpServers` entries intact and installs the current `2.7.3` VSIX from the shipped `V2/` artifact first.

## Manual Installation

If the automated installation fails, follow these step-by-step instructions:

### Step 1: Create Installation Directory

**macOS/Linux:**
```bash
mkdir -p ~/cursor-extensions/review-gate-v2
cd ~/cursor-extensions/review-gate-v2
```

**Windows:**
```cmd
mkdir %USERPROFILE%\cursor-extensions\review-gate-v2
cd %USERPROFILE%\cursor-extensions\review-gate-v2
```

### Step 2: Copy Required Files

Copy these files from the downloaded Review-Gate/V2 folder to your installation directory:
- `review_gate_v2_mcp.py` - The MCP server
- `requirements_simple.txt` - Python dependencies
- `mcp.json` - Sample MCP configuration entry
- `ReviewGateV2.mdc` - Current Review Gate V2 rule file
- `review-gate-v2-2.7.3.vsix` - Preferred shipped Cursor extension artifact

If your checkout does not include `V2/review-gate-v2-2.7.3.vsix`, use `V2/cursor-extension/review-gate-v2-2.7.3.vsix` as the fallback build-output artifact instead.

### Step 3: Set Up Python Environment

**macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements_simple.txt
```

**Windows:**
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements_simple.txt
```

### Step 4: Install SoX (for Speech-to-Text)

**macOS:**
```bash
brew install sox
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install sox
```

**Windows:**
```cmd
# Option 1: Using Chocolatey
choco install sox

# Option 2: Manual download from http://sox.sourceforge.net/
```

### Step 5: Configure MCP Server

Create or edit the MCP configuration file:

**macOS/Linux:**
```bash
mkdir -p ~/.cursor
nano ~/.cursor/mcp.json
```

**Windows:**
```cmd
mkdir %USERPROFILE%\.cursor
notepad %USERPROFILE%\.cursor\mcp.json
```

If `mcp.json` already exists, do not replace the whole file. Preserve the existing `mcpServers` entries and merge in only the `review-gate-v2` block below. If the file does not exist yet, you can start from `V2/mcp.json` and replace the placeholder paths.

Add or update this configuration block (replace paths with your actual paths):

**macOS/Linux Configuration:**
```json
{
  "mcpServers": {
    "existing-server": {
      "command": "/path/to/your/other/server",
      "args": []
    },
    "review-gate-v2": {
      "command": "/Users/YOUR_USERNAME/cursor-extensions/review-gate-v2/venv/bin/python",
      "args": ["/Users/YOUR_USERNAME/cursor-extensions/review-gate-v2/review_gate_v2_mcp.py"],
      "env": {
        "PYTHONPATH": "/Users/YOUR_USERNAME/cursor-extensions/review-gate-v2",
        "PYTHONUNBUFFERED": "1",
        "REVIEW_GATE_MODE": "cursor_integration"
      }
    }
  }
}
```

**Windows Configuration:**
```json
{
  "mcpServers": {
    "existing-server": {
      "command": "C:\\path\\to\\your\\other\\server.exe",
      "args": []
    },
    "review-gate-v2": {
      "command": "C:\\Users\\YOUR_USERNAME\\cursor-extensions\\review-gate-v2\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\YOUR_USERNAME\\cursor-extensions\\review-gate-v2\\review_gate_v2_mcp.py"],
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\cursor-extensions\\review-gate-v2",
        "PYTHONUNBUFFERED": "1",
        "REVIEW_GATE_MODE": "cursor_integration"
      }
    }
  }
}
```

### Step 6: Install Cursor Extension

1. Open Cursor IDE
2. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
3. Type "Extensions: Install from VSIX"
4. Navigate to your installation directory
5. Select `review-gate-v2-2.7.3.vsix`
6. Restart Cursor when prompted

Use the VSIX copied from `V2/review-gate-v2-2.7.3.vsix` when available. If you only have the fallback build output, install `V2/cursor-extension/review-gate-v2-2.7.3.vsix`.

### Step 7: Load the Current V2 Rule

1. Open `V2/ReviewGateV2.mdc`
2. Copy the entire rule text
3. Open Cursor settings and find the Rules or AI Rules section
4. Paste the contents of `ReviewGateV2.mdc`
5. Save and restart Cursor

### Step 8: Verify Installation

Test the MCP server:

**macOS/Linux:**
```bash
cd ~/cursor-extensions/review-gate-v2
source venv/bin/activate
python review_gate_v2_mcp.py
# Should see initialization messages, press Ctrl+C to stop
```

**Windows:**
```cmd
cd %USERPROFILE%\cursor-extensions\review-gate-v2
venv\Scripts\activate
python review_gate_v2_mcp.py
# Should see initialization messages, press Ctrl+C to stop
```

## Testing Your Installation

### Test 1: Extension Check
1. Open Cursor
2. Go to Extensions panel (Ctrl+Shift+X or Cmd+Shift+X)
3. Look for "Review Gate V2" in installed extensions
4. Ensure it's enabled

### Test 2: Manual Popup
1. Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (macOS)
2. Review Gate popup should appear
3. Try typing text and clicking send

### Test 3: MCP Integration
1. Start a new chat in Cursor
2. Type: "Use the review_gate_chat tool to get my feedback"
3. The popup should appear automatically

### Test 4: Check MCP Status
Look for the status indicator in the popup:
- Green dot: MCP server is active
- Orange dot: MCP server is inactive

## Troubleshooting

### MCP Server Not Starting

Check Python installation:
```bash
python --version  # or python3 --version
```

Verify virtual environment:
```bash
# macOS/Linux
which python

# Windows
where python
```

Check log file:
```bash
# macOS/Linux
tail -f /tmp/review_gate_v2.log

# Windows
type %TEMP%\review_gate_v2.log
```

### Extension Not Working

1. Check if extension is enabled:
   - Open Extensions panel
   - Find Review Gate V2
   - Click "Enable" if disabled

2. Check browser console for errors:
   - Press F12 in Cursor
   - Go to Console tab
   - Look for error messages

3. Restart Cursor completely:
   - Close all Cursor windows
   - Wait 5 seconds
   - Reopen Cursor

### Popup Not Appearing

Verify MCP configuration:
```bash
# macOS/Linux
cat ~/.cursor/mcp.json

# Windows
type %USERPROFILE%\.cursor\mcp.json
```

Check for trigger files:
```bash
# macOS/Linux
ls -la /tmp/review_gate_*

# Windows
dir %TEMP%\review_gate_*
```

### Speech-to-Text Issues

Test microphone:
```bash
# macOS/Linux
sox -d -r 16000 -c 1 test.wav trim 0 2

# Windows (if SoX installed)
sox -d -r 16000 -c 1 test.wav trim 0 2
```

Check microphone permissions:
- macOS: System Preferences > Security & Privacy > Privacy > Microphone
- Windows: Settings > Privacy > Microphone
- Linux: Check your distribution's audio settings

### Windows-Specific Issues

1. Path format errors:
   - Use double backslashes in JSON: `C:\\Users\\...`
   - Or use forward slashes: `C:/Users/...`

2. Python not found:
   - Add Python to PATH during installation
   - Or use full path to python.exe

3. Permission denied:
   - Run Command Prompt as Administrator
   - Check Windows Defender settings

## File Locations

After installation, files should be in these locations:

**macOS/Linux:**
```
~/cursor-extensions/review-gate-v2/
  - review_gate_v2_mcp.py
  - requirements_simple.txt
  - review-gate-v2-2.7.3.vsix
  - venv/

~/.cursor/
  - mcp.json

Temp files: /tmp/review_gate_*
Log file: /tmp/review_gate_v2.log
```

**Windows:**
```
%USERPROFILE%\cursor-extensions\review-gate-v2\
  - review_gate_v2_mcp.py
  - requirements_simple.txt
  - review-gate-v2-2.7.3.vsix
  - venv\

%USERPROFILE%\.cursor\
  - mcp.json

Temp files: %TEMP%\review_gate_*
Log file: %TEMP%\review_gate_v2.log
```

## Uninstallation

### Automated Uninstall

**macOS/Linux:**
```bash
cd Review-Gate/V2
chmod +x uninstall.sh
./uninstall.sh
```

**Windows:**
```cmd
cd Review-Gate\V2
uninstall.bat
```

### Manual Uninstall

1. Remove extension from Cursor:
   - Open Extensions panel
   - Find Review Gate V2
   - Click Uninstall

2. Remove installation directory:
   ```bash
   # macOS/Linux
   rm -rf ~/cursor-extensions/review-gate-v2

   # Windows
   rmdir /s %USERPROFILE%\cursor-extensions\review-gate-v2
   ```

3. Remove MCP configuration:
   - Edit `mcp.json`
   - Remove only the `review-gate-v2` entry
   - Preserve any unrelated MCP servers and keep any backup file created by the installer or uninstaller

4. Clean temporary files:
   ```bash
   # macOS/Linux
   rm -f /tmp/review_gate_*

   # Windows
   del %TEMP%\review_gate_*
   ```

## Getting Help

If you encounter issues not covered here:

1. Check the log file for error messages
2. Verify all file paths are correct
3. Ensure Python and dependencies are installed
4. Try the manual installation method
5. Report issues at: https://github.com/LakshmanTurlapati/Review-Gate/issues

## Features

Once installed, Review Gate V2 provides:

- Text input capture from Cursor agents
- Image upload functionality
- Speech-to-text conversion (requires SoX)
- 5-minute timeout for user responses
- Cross-platform compatibility
- MCP status monitoring
- Manual trigger hotkey (Ctrl/Cmd+Shift+R)

The system is now ready to enhance your Cursor workflow with interactive popups.
