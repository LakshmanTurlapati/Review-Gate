@echo off
setlocal enabledelayedexpansion

REM Review Gate V2 - Windows Batch Installation Script
REM Author: Lakshman Turlapati
REM This script installs Review Gate V2 globally for Cursor IDE on Windows

echo.
echo ===========================================
echo 🚀 Review Gate V2 - Windows Installation
echo ===========================================
echo.

REM Check if running on Windows
ver | findstr /i "windows" > nul
if errorlevel 1 (
    echo ❌ This script is designed for Windows only
    pause
    exit /b 1
)

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running with administrator privileges
) else (
    echo ⚠️ Administrator privileges recommended for package installations
    echo 💡 Some features may require manual installation
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Python 3 is required but not installed
        echo 💡 Please install Python 3 from https://python.org or Microsoft Store
        echo 💡 Then run this script again
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python3"
    )
) else (
    set "PYTHON_CMD=python"
)

for /f "tokens=*" %%i in ('!PYTHON_CMD! --version') do set "PYTHON_VERSION=%%i"
echo ✅ Python found: !PYTHON_VERSION!

REM Check if Chocolatey is installed
choco --version >nul 2>&1
if errorlevel 1 (
    echo 📦 Chocolatey not found
    echo 💡 For automatic SoX installation, please install Chocolatey from:
    echo 💡 https://chocolatey.org/install
    echo 💡 Or install SoX manually from: http://sox.sourceforge.net/
    set "CHOCO_AVAILABLE=false"
) else (
    echo ✅ Chocolatey found
    set "CHOCO_AVAILABLE=true"
)

REM Install SoX for speech-to-text
echo 🎤 Checking SoX installation...
sox --version >nul 2>&1
if errorlevel 1 (
    if "!CHOCO_AVAILABLE!"=="true" (
        echo 📦 Installing SoX via Chocolatey...
        choco install sox -y
        if errorlevel 1 (
            echo ⚠️ Failed to install SoX via Chocolatey
            echo 💡 Please install SoX manually from http://sox.sourceforge.net/
        ) else (
            echo ✅ SoX installed successfully
        )
    ) else (
        echo ⚠️ SoX not found and Chocolatey not available
        echo 💡 Please install SoX manually from http://sox.sourceforge.net/
    )
) else (
    echo ✅ SoX already installed
)

REM Create global Cursor extensions directory
set "CURSOR_EXTENSIONS_DIR=%USERPROFILE%\cursor-extensions"
set "REVIEW_GATE_DIR=%CURSOR_EXTENSIONS_DIR%\review-gate-v2"

echo 📁 Creating global installation directory...
if not exist "!CURSOR_EXTENSIONS_DIR!" mkdir "!CURSOR_EXTENSIONS_DIR!"
if not exist "!REVIEW_GATE_DIR!" mkdir "!REVIEW_GATE_DIR!"

REM Copy MCP server files
echo 📋 Copying MCP server files...
if exist "%SCRIPT_DIR%\review_gate_v2_mcp.py" (
    copy "%SCRIPT_DIR%\review_gate_v2_mcp.py" "!REVIEW_GATE_DIR!\" >nul
) else (
    echo ❌ MCP server file not found: %SCRIPT_DIR%\review_gate_v2_mcp.py
    pause
    exit /b 1
)

if exist "%SCRIPT_DIR%\requirements_simple.txt" (
    copy "%SCRIPT_DIR%\requirements_simple.txt" "!REVIEW_GATE_DIR!\" >nul
) else (
    echo ❌ Requirements file not found: %SCRIPT_DIR%\requirements_simple.txt
    pause
    exit /b 1
)

REM Create Python virtual environment
echo 🐍 Creating Python virtual environment...
cd /d "!REVIEW_GATE_DIR!"
!PYTHON_CMD! -m venv venv
if errorlevel 1 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment and install dependencies
echo 📦 Installing Python dependencies...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements_simple.txt
call deactivate

echo ✅ Python environment created and dependencies installed

REM Create MCP configuration
set "CURSOR_MCP_FILE=%USERPROFILE%\.cursor\mcp.json"
echo ⚙️ Configuring MCP servers...
if not exist "%USERPROFILE%\.cursor" mkdir "%USERPROFILE%\.cursor"

REM Backup existing MCP configuration if it exists
if exist "!CURSOR_MCP_FILE!" (
    for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
    set "timestamp=!dt:~0,4!!dt:~4,2!!dt:~6,2!_!dt:~8,2!!dt:~10,2!!dt:~12,2!"
    set "BACKUP_FILE=!CURSOR_MCP_FILE!.backup.!timestamp!"
    echo 💾 Backing up existing MCP configuration to: !BACKUP_FILE!
    copy "!CURSOR_MCP_FILE!" "!BACKUP_FILE!" >nul
)

REM Create MCP configuration using Python (simpler than parsing JSON in batch)
echo 📝 Creating MCP configuration...
REM Create temporary Python script for MCP configuration
echo import json > temp_mcp_config.py
echo import os >> temp_mcp_config.py
echo. >> temp_mcp_config.py
echo mcp_file = r'!CURSOR_MCP_FILE!' >> temp_mcp_config.py
echo review_gate_dir = r'!REVIEW_GATE_DIR!' >> temp_mcp_config.py
echo. >> temp_mcp_config.py
echo # Try to read existing configuration >> temp_mcp_config.py
echo existing_servers = {} >> temp_mcp_config.py
echo if os.path.exists(mcp_file): >> temp_mcp_config.py
echo     try: >> temp_mcp_config.py
echo         with open(mcp_file, 'r') as f: >> temp_mcp_config.py
echo             config = json.load(f) >> temp_mcp_config.py
echo         existing_servers = config.get('mcpServers', {}) >> temp_mcp_config.py
echo         existing_servers.pop('review-gate-v2', None) >> temp_mcp_config.py
echo         print('✅ Found existing MCP servers, merging configurations') >> temp_mcp_config.py
echo     except: >> temp_mcp_config.py
echo         print('⚠️ Existing config invalid, creating new one') >> temp_mcp_config.py
echo         existing_servers = {} >> temp_mcp_config.py
echo else: >> temp_mcp_config.py
echo     print('📝 Creating new MCP configuration file') >> temp_mcp_config.py
echo. >> temp_mcp_config.py
echo # Add Review Gate V2 server >> temp_mcp_config.py
echo existing_servers['review-gate-v2'] = { >> temp_mcp_config.py
echo     'command': os.path.join(review_gate_dir, 'venv', 'Scripts', 'python.exe'), >> temp_mcp_config.py
echo     'args': [os.path.join(review_gate_dir, 'review_gate_v2_mcp.py')], >> temp_mcp_config.py
echo     'env': { >> temp_mcp_config.py
echo         'PYTHONPATH': review_gate_dir, >> temp_mcp_config.py
echo         'PYTHONUNBUFFERED': '1', >> temp_mcp_config.py
echo         'REVIEW_GATE_MODE': 'cursor_integration' >> temp_mcp_config.py
echo     } >> temp_mcp_config.py
echo } >> temp_mcp_config.py
echo. >> temp_mcp_config.py
echo # Create final config >> temp_mcp_config.py
echo config = {'mcpServers': existing_servers} >> temp_mcp_config.py
echo. >> temp_mcp_config.py
echo # Write to file >> temp_mcp_config.py
echo try: >> temp_mcp_config.py
echo     with open(mcp_file, 'w') as f: >> temp_mcp_config.py
echo         json.dump(config, f, indent=2) >> temp_mcp_config.py
echo     print('✅ MCP configuration updated successfully') >> temp_mcp_config.py
echo     print(f'Total MCP servers configured: {len(existing_servers)}') >> temp_mcp_config.py
echo     for name in existing_servers.keys(): >> temp_mcp_config.py
echo         print(f'  • {name}') >> temp_mcp_config.py
echo except Exception as e: >> temp_mcp_config.py
echo     print(f'❌ Failed to write MCP configuration: {e}') >> temp_mcp_config.py
echo     exit(1) >> temp_mcp_config.py

REM Execute the Python script
!PYTHON_CMD! temp_mcp_config.py

REM Clean up temporary script
del temp_mcp_config.py

if errorlevel 1 (
    echo ❌ Failed to create MCP configuration
    if exist "!BACKUP_FILE!" (
        echo 🔄 Restoring from backup...
        copy "!BACKUP_FILE!" "!CURSOR_MCP_FILE!" >nul
        echo ✅ Backup restored
    )
    pause
    exit /b 1
)

REM Test MCP server
echo 🧪 Testing MCP server...
cd /d "!REVIEW_GATE_DIR!"
timeout /t 1 /nobreak >nul 2>&1
echo ⚠️ MCP server test skipped (manual verification required)

REM Install Cursor extension
set "EXTENSION_FILE=%SCRIPT_DIR%\cursor-extension\review-gate-v2-2.6.3.vsix"
if exist "!EXTENSION_FILE!" (
    echo 🔌 Installing Cursor extension...
    copy "!EXTENSION_FILE!" "!REVIEW_GATE_DIR!\" >nul
    
    echo.
    echo 📋 MANUAL STEP REQUIRED:
    echo Please complete the extension installation manually:
    echo 1. Open Cursor IDE
    echo 2. Press Ctrl+Shift+P
    echo 3. Type 'Extensions: Install from VSIX'
    echo 4. Select: !REVIEW_GATE_DIR!\review-gate-v2-2.6.3.vsix
    echo 5. Restart Cursor when prompted
    echo.
    
    REM Try to open Cursor if available
    if exist "%ProgramFiles%\Cursor\Cursor.exe" (
        echo 🚀 Opening Cursor IDE...
        start "" "%ProgramFiles%\Cursor\Cursor.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\cursor\Cursor.exe" (
        echo 🚀 Opening Cursor IDE...
        start "" "%LOCALAPPDATA%\Programs\cursor\Cursor.exe"
    ) else (
        echo 💡 Please open Cursor IDE manually
    )
) else (
    echo ❌ Extension file not found: !EXTENSION_FILE!
    echo 💡 Please install the extension manually from the Cursor Extensions marketplace
)

REM Install global rule (optional)
set "CURSOR_RULES_DIR=%APPDATA%\Cursor\User\rules"
if exist "%SCRIPT_DIR%\ReviewGate.mdc" (
    echo 📜 Installing global rule...
    if not exist "!CURSOR_RULES_DIR!" mkdir "!CURSOR_RULES_DIR!"
    copy "%SCRIPT_DIR%\ReviewGate.mdc" "!CURSOR_RULES_DIR!\" >nul
    echo ✅ Global rule installed
)

REM Clean up any existing temp files
echo 🧹 Cleaning up temporary files...
for /f "tokens=*" %%i in ('!PYTHON_CMD! -c "import tempfile; print(tempfile.gettempdir())"') do set "TEMP_DIR=%%i"
del /f /q "!TEMP_DIR!\review_gate_*" >nul 2>&1
del /f /q "!TEMP_DIR!\mcp_response*" >nul 2>&1

echo.
echo ==========================================
echo 🎉 Review Gate V2 Installation Complete!
echo ==========================================
echo.
echo 📍 Installation Summary:
echo    • MCP Server: !REVIEW_GATE_DIR!
echo    • MCP Config: !CURSOR_MCP_FILE!
echo    • Extension: !REVIEW_GATE_DIR!\review-gate-v2-2.6.3.vsix
echo    • Global Rule: !CURSOR_RULES_DIR!\ReviewGate.mdc
echo.
echo 🧪 Testing Your Installation:
echo 1. Restart Cursor completely
echo 2. Press Ctrl+Shift+R to test manual trigger
echo 3. Or ask Cursor Agent: 'Use the review_gate_chat tool'
echo.
echo 🎤 Speech-to-Text Features:
echo    • Click microphone icon in popup
echo    • Speak clearly for 2-3 seconds
echo    • Click stop to transcribe
echo.
echo 📷 Image Upload Features:
echo    • Click camera icon in popup
echo    • Select images (PNG, JPG, etc.)
echo    • Images are included in response
echo.
echo 🔧 Troubleshooting:
echo    • Logs: type "!PYTHON_CMD! -c "import tempfile; print(tempfile.gettempdir())"\review_gate_v2.log"
echo    • Test SoX: sox --version
echo    • Browser Console: F12 in Cursor
echo.
echo ✨ Enjoy your voice-activated Review Gate! ✨

REM Final verification
echo 🔍 Final verification...
if exist "!REVIEW_GATE_DIR!\review_gate_v2_mcp.py" (
    if exist "!CURSOR_MCP_FILE!" (
        if exist "!REVIEW_GATE_DIR!\venv" (
            echo ✅ All components installed successfully
            pause
            exit /b 0
        )
    )
)

echo ❌ Some components may not have installed correctly
echo 💡 Please check the installation manually
pause
exit /b 1