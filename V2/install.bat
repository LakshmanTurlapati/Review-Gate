@echo off
setlocal enabledelayedexpansion

REM Review Gate V2 - Windows Batch Installation Script
REM Author: Lakshman Turlapati
REM This script installs Review Gate V2 globally for Cursor IDE on Windows

REM Enable ANSI escape sequences for colors
for /f "tokens=2 delims=[]" %%i in ('ver') do set "winver=%%i"
for /f "tokens=2 delims= " %%i in ("%winver%") do set "winver=%%i"
for /f "tokens=1,2 delims=." %%i in ("%winver%") do set "winmajor=%%i" & set "winminor=%%j"

REM Define color codes (works on Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "WHITE=[97m"
set "NC=[0m"

REM Enhanced logging functions
set "log_error=echo %RED%ERROR:"
set "log_success=echo %GREEN%SUCCESS:"
set "log_info=echo %YELLOW%INFO:"
set "log_progress=echo %CYAN%PROGRESS:"
set "log_warning=echo %YELLOW%WARNING:"
set "log_step=echo %WHITE%"
set "log_header=echo %CYAN%"

echo.
%log_header% Review Gate V2 - Windows Installation%NC%
%log_header%===========================================%NC%
echo.

REM Check if running on Windows
ver | findstr /i "windows" > nul
if errorlevel 1 (
    %log_error% This script is designed for Windows only%NC%
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "SMOKE_MODE=0"
if /I "%REVIEW_GATE_SMOKE%"=="1" set "SMOKE_MODE=1"
set "SKIP_DEP_INSTALL=0"
if "!SMOKE_MODE!"=="1" set "SKIP_DEP_INSTALL=1"
if /I "%REVIEW_GATE_SKIP_DEP_INSTALL%"=="1" set "SKIP_DEP_INSTALL=1"
set "SKIP_EXTENSION_INSTALL=0"
if "!SMOKE_MODE!"=="1" set "SKIP_EXTENSION_INSTALL=1"
if /I "%REVIEW_GATE_SKIP_EXTENSION_INSTALL%"=="1" set "SKIP_EXTENSION_INSTALL=1"
set "SKIP_SERVER_SMOKE=0"
if "!SMOKE_MODE!"=="1" set "SKIP_SERVER_SMOKE=1"
if /I "%REVIEW_GATE_SKIP_SERVER_SMOKE%"=="1" set "SKIP_SERVER_SMOKE=1"
set "SHOULD_PAUSE=1"
if "!SMOKE_MODE!"=="1" set "SHOULD_PAUSE=0"

if "!SMOKE_MODE!"=="1" (
    if "%REVIEW_GATE_TEST_HOME%"=="" (
        %log_error% REVIEW_GATE_TEST_HOME is required when REVIEW_GATE_SMOKE=1%NC%
        exit /b 1
    )
    if "%REVIEW_GATE_TEST_INSTALL_DIR%"=="" (
        %log_error% REVIEW_GATE_TEST_INSTALL_DIR is required when REVIEW_GATE_SMOKE=1%NC%
        exit /b 1
    )
    set "USERPROFILE=%REVIEW_GATE_TEST_HOME%"
    set "APPDATA=%USERPROFILE%\AppData\Roaming"
    set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
    if not exist "!USERPROFILE!" mkdir "!USERPROFILE!"
    if not exist "!APPDATA!" mkdir "!APPDATA!"
    if not exist "!LOCALAPPDATA!" mkdir "!LOCALAPPDATA!"
    %log_info% Smoke mode enabled with USERPROFILE redirected to: !USERPROFILE!%NC%
    %log_info% Smoke install root redirected to: !REVIEW_GATE_TEST_INSTALL_DIR!%NC%
)

REM Check for admin privileges
if "!SMOKE_MODE!"=="1" (
    %log_info% Skipping Windows privilege checks in smoke mode%NC%
) else (
    net session >nul 2>&1
    if %errorLevel% == 0 (
        %log_success% Running with administrator privileges%NC%
    ) else (
        %log_warning% Administrator privileges recommended for package installations%NC%
        %log_info% Some features may require manual installation%NC%
    )
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        %log_error% Python 3 is required but not installed%NC%
        %log_info% Please install Python 3 from https://python.org or Microsoft Store%NC%
        %log_info% Then run this script again%NC%
        if "!SHOULD_PAUSE!"=="1" pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python3"
    )
) else (
    set "PYTHON_CMD=python"
)

for /f "tokens=*" %%i in ('!PYTHON_CMD! --version') do set "PYTHON_VERSION=%%i"
%log_success% Python found: !PYTHON_VERSION!%NC%

REM Check if Chocolatey is installed
if "!SKIP_DEP_INSTALL!"=="1" (
    %log_info% Skipping package-manager dependency installation%NC%
    set "CHOCO_AVAILABLE=false"
) else (
    choco --version >nul 2>&1
    if errorlevel 1 (
        %log_info% Chocolatey not found%NC%
        %log_info% For automatic SoX installation, please install Chocolatey from:%NC%
        %log_info% https://chocolatey.org/install%NC%
        %log_info% Or install SoX manually from: http://sox.sourceforge.net/%NC%
        set "CHOCO_AVAILABLE=false"
    ) else (
        %log_success% Chocolatey found%NC%
        set "CHOCO_AVAILABLE=true"
    )
)

REM Install SoX for speech-to-text
%log_progress% Checking SoX installation...%NC%
if "!SKIP_DEP_INSTALL!"=="1" (
    %log_info% Skipping SoX installation in smoke mode%NC%
) else (
    sox --version >nul 2>&1
    if errorlevel 1 (
        if "!CHOCO_AVAILABLE!"=="true" (
            %log_progress% Installing SoX via Chocolatey...%NC%
            choco install sox -y
            if errorlevel 1 (
                %log_warning% Failed to install SoX via Chocolatey%NC%
                %log_info% Please install SoX manually from http://sox.sourceforge.net/%NC%
            ) else (
                %log_success% SoX installed successfully%NC%
            )
        ) else (
            %log_warning% SoX not found and Chocolatey not available%NC%
            %log_info% Please install SoX manually from http://sox.sourceforge.net/%NC%
        )
    ) else (
        %log_success% SoX already installed%NC%
    )
)

REM Create global Cursor extensions directory
if "!SMOKE_MODE!"=="1" (
    set "REVIEW_GATE_DIR=%REVIEW_GATE_TEST_INSTALL_DIR%"
    for %%i in ("!REVIEW_GATE_DIR!\..") do set "CURSOR_EXTENSIONS_DIR=%%~fi"
) else (
    set "CURSOR_EXTENSIONS_DIR=%USERPROFILE%\cursor-extensions"
    set "REVIEW_GATE_DIR=%CURSOR_EXTENSIONS_DIR%\review-gate-v2"
)

%log_progress% Creating global installation directory...%NC%
if not exist "!CURSOR_EXTENSIONS_DIR!" mkdir "!CURSOR_EXTENSIONS_DIR!"
if not exist "!REVIEW_GATE_DIR!" mkdir "!REVIEW_GATE_DIR!"

REM Copy MCP server files
%log_progress% Copying MCP server files...%NC%
if exist "%SCRIPT_DIR%\review_gate_v2_mcp.py" (
    copy "%SCRIPT_DIR%\review_gate_v2_mcp.py" "!REVIEW_GATE_DIR!\" >nul
) else (
    %log_error% MCP server file not found: %SCRIPT_DIR%\review_gate_v2_mcp.py%NC%
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

if exist "%SCRIPT_DIR%\requirements_simple.txt" (
    copy "%SCRIPT_DIR%\requirements_simple.txt" "!REVIEW_GATE_DIR!\" >nul
) else (
    %log_error% Requirements file not found: %SCRIPT_DIR%\requirements_simple.txt%NC%
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

REM Create Python virtual environment
%log_progress% Creating Python virtual environment...%NC%
cd /d "!REVIEW_GATE_DIR!"
!PYTHON_CMD! -m venv venv
if errorlevel 1 (
    %log_error% Failed to create virtual environment%NC%
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

REM Activate virtual environment and install dependencies
if "!SKIP_DEP_INSTALL!"=="1" (
    %log_info% Skipping Python dependency installation%NC%
) else (
    %log_progress% Installing Python dependencies...%NC%
    call "venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    python -m pip install -r requirements_simple.txt
    call deactivate
)

%log_success% Python environment created and dependencies installed%NC%

REM Create MCP configuration
set "CURSOR_MCP_FILE=%USERPROFILE%\.cursor\mcp.json"
set "HELPER_SCRIPT=%SCRIPT_DIR%\update_mcp_config.py"
set "MCP_TEMPLATE=%SCRIPT_DIR%\mcp.json"
%log_progress% Configuring MCP servers...%NC%
if not exist "%USERPROFILE%\.cursor" mkdir "%USERPROFILE%\.cursor"

if not exist "!HELPER_SCRIPT!" (
    %log_error% MCP config helper not found: !HELPER_SCRIPT!%NC%
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

if not exist "!MCP_TEMPLATE!" (
    %log_error% MCP config template not found: !MCP_TEMPLATE!%NC%
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

REM Backup existing MCP configuration if it exists
set "BACKUP_FILE="
if exist "!CURSOR_MCP_FILE!" (
    for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
    set "timestamp=!dt:~0,4!!dt:~4,2!!dt:~6,2!_!dt:~8,2!!dt:~10,2!!dt:~12,2!"
    set "BACKUP_FILE=!CURSOR_MCP_FILE!.backup.!timestamp!"
    %log_info% Backing up existing MCP configuration to: !BACKUP_FILE!%NC%
    copy "!CURSOR_MCP_FILE!" "!BACKUP_FILE!" >nul
)

REM Run update_mcp_config.py merge to preserve existing MCP servers
%log_progress% Updating MCP configuration...%NC%
set "PYTHON_PATH=!REVIEW_GATE_DIR!\venv\Scripts\python.exe"
set "PYTHON_PATH_JSON=!PYTHON_PATH:\=/!"
set "REVIEW_GATE_DIR_JSON=!REVIEW_GATE_DIR:\=/!"

!PYTHON_CMD! "!HELPER_SCRIPT!" merge --config "!CURSOR_MCP_FILE!" --template "!MCP_TEMPLATE!" --server-name "review-gate-v2" --install-dir "!REVIEW_GATE_DIR_JSON!" --python-cmd "!PYTHON_PATH_JSON!"
if errorlevel 1 (
    %log_error% Failed to update MCP configuration%NC%
    if defined BACKUP_FILE (
        if exist "!BACKUP_FILE!" (
            %log_progress% Restoring from backup...%NC%
            copy "!BACKUP_FILE!" "!CURSOR_MCP_FILE!" >nul
            %log_success% Backup restored%NC%
        )
    ) else (
        if exist "!CURSOR_MCP_FILE!" (
            del /f /q "!CURSOR_MCP_FILE!" >nul 2>&1
        )
    )
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

%log_success% MCP configuration updated successfully%NC%


REM Test MCP server
%log_progress% Testing MCP server...%NC%
cd /d "!REVIEW_GATE_DIR!"
if "!SKIP_SERVER_SMOKE!"=="1" (
    %log_info% Skipping MCP server smoke test%NC%
) else (
    timeout /t 1 /nobreak >nul 2>&1
    %log_warning% MCP server test skipped (manual verification required)%NC%
)

REM Install Cursor extension
set "EXTENSION_VERSION=2.7.3"
set "EXTENSION_BASENAME=review-gate-v2-2.7.3.vsix"
set "EXTENSION_FILE="
if exist "%SCRIPT_DIR%\!EXTENSION_BASENAME!" (
    set "EXTENSION_FILE=%SCRIPT_DIR%\!EXTENSION_BASENAME!"
) else if exist "%SCRIPT_DIR%\cursor-extension\!EXTENSION_BASENAME!" (
    set "EXTENSION_FILE=%SCRIPT_DIR%\cursor-extension\!EXTENSION_BASENAME!"
)
set "INSTALLED_EXTENSION_FILE=!REVIEW_GATE_DIR!\!EXTENSION_BASENAME!"
if defined EXTENSION_FILE (
    %log_progress% Installing Cursor extension...%NC%
    copy "!EXTENSION_FILE!" "!INSTALLED_EXTENSION_FILE!" >nul
    
    REM Try automated installation first
    set "EXTENSION_INSTALLED=false"
    if "!SKIP_EXTENSION_INSTALL!"=="1" (
        %log_info% Skipping automated Cursor extension installation%NC%
    ) else (
        set "CURSOR_CMD="
        
        REM Check for cursor command in various locations
        if exist "%ProgramFiles%\Cursor\resources\app\bin\cursor.cmd" (
            set "CURSOR_CMD=%ProgramFiles%\Cursor\resources\app\bin\cursor.cmd"
        ) else if exist "%LOCALAPPDATA%\Programs\cursor\resources\app\bin\cursor.cmd" (
            set "CURSOR_CMD=%LOCALAPPDATA%\Programs\cursor\resources\app\bin\cursor.cmd"
        ) else if exist "%ProgramFiles(x86)%\Cursor\resources\app\bin\cursor.cmd" (
            set "CURSOR_CMD=%ProgramFiles(x86)%\Cursor\resources\app\bin\cursor.cmd"
        )
        
        if defined CURSOR_CMD (
            %log_progress% Attempting automated extension installation...%NC%
            "!CURSOR_CMD!" --install-extension "!INSTALLED_EXTENSION_FILE!" >nul 2>&1
            if !errorlevel! equ 0 (
                %log_success% Extension installed automatically via command line%NC%
                set "EXTENSION_INSTALLED=true"
            ) else (
                %log_warning% Automated installation failed, falling back to manual method%NC%
            )
        )
    )
    
    REM If automated installation failed, provide manual instructions
    if "!EXTENSION_INSTALLED!"=="false" if "!SKIP_EXTENSION_INSTALL!"=="0" (
        echo.
        %log_header% MANUAL EXTENSION INSTALLATION REQUIRED:%NC%
        %log_info% Please complete the extension installation manually:%NC%
        %log_step% 1. Open Cursor IDE%NC%
        %log_step% 2. Press Ctrl+Shift+P%NC%
        %log_step% 3. Type 'Extensions: Install from VSIX'%NC%
        %log_step% 4. Select: !INSTALLED_EXTENSION_FILE!%NC%
        %log_step% 5. Restart Cursor when prompted%NC%
        echo.
        
        REM Try to open Cursor if available
        if exist "%ProgramFiles%\Cursor\Cursor.exe" (
            %log_progress% Opening Cursor IDE...%NC%
            start "" "%ProgramFiles%\Cursor\Cursor.exe"
        ) else if exist "%LOCALAPPDATA%\Programs\cursor\Cursor.exe" (
            %log_progress% Opening Cursor IDE...%NC%
            start "" "%LOCALAPPDATA%\Programs\cursor\Cursor.exe"
        ) else (
            %log_info% Please open Cursor IDE manually%NC%
        )
    )
) else (
    %log_error% Extension file not found. Checked: %SCRIPT_DIR%\!EXTENSION_BASENAME! and %SCRIPT_DIR%\cursor-extension\!EXTENSION_BASENAME!%NC%
    %log_info% Please ensure one of the shipped VSIX files exists before running the installer again%NC%
    if "!SHOULD_PAUSE!"=="1" pause
    exit /b 1
)

REM Install global rule (optional) - Windows-specific directory
set "CURSOR_RULES_DIR=%APPDATA%\Cursor\User\rules"
set "RULE_FILENAME=ReviewGateV2.mdc"
set "RULE_SOURCE_FILE=%SCRIPT_DIR%\!RULE_FILENAME!"
set "INSTALLED_RULE_FILE=!CURSOR_RULES_DIR!\!RULE_FILENAME!"
if exist "!RULE_SOURCE_FILE!" (
    %log_progress% Installing global rule...%NC%
    if not exist "!CURSOR_RULES_DIR!" mkdir "!CURSOR_RULES_DIR!"
    copy "!RULE_SOURCE_FILE!" "!INSTALLED_RULE_FILE!" >nul
    %log_success% Global rule installed to: !INSTALLED_RULE_FILE!%NC%
) else if exist "!RULE_SOURCE_FILE!" (
    %log_warning% Could not determine Cursor rules directory%NC%
    %log_info% Global rule available at: !RULE_SOURCE_FILE!%NC%
)

REM Clean up any existing temp files
%log_progress% Cleaning up temporary files...%NC%
for /f "tokens=*" %%i in ('!PYTHON_CMD! -c "import tempfile; print(tempfile.gettempdir())"') do set "TEMP_DIR=%%i"
del /f /q "!TEMP_DIR!\review_gate_*" >nul 2>&1
del /f /q "!TEMP_DIR!\mcp_response*" >nul 2>&1

echo.
%log_success% Review Gate V2 Installation Complete!%NC%
%log_header%==========================================%NC%
echo.
%log_header% Installation Summary:%NC%
%log_step%    - MCP Server: !REVIEW_GATE_DIR!%NC%
%log_step%    - MCP Config: !CURSOR_MCP_FILE!%NC%
%log_step%    - Extension: !INSTALLED_EXTENSION_FILE!%NC%
%log_step%    - Global Rule: !INSTALLED_RULE_FILE!%NC%
echo.
%log_header% Testing Your Installation:%NC%
%log_step% 1. Restart Cursor completely%NC%
%log_info% 2. Press Ctrl+Shift+R to test manual trigger%NC%
%log_info% 3. Or ask Cursor Agent: 'Use the review_gate_chat tool'%NC%
echo.
%log_header% Speech-to-Text Features:%NC%
%log_step%    - Click microphone icon in popup%NC%
%log_step%    - Speak clearly for 2-3 seconds%NC%
%log_step%    - Click stop to transcribe%NC%
echo.
%log_header% Image Upload Features:%NC%
%log_step%    - Click camera icon in popup%NC%
%log_step%    - Select images (PNG, JPG, etc.)%NC%
%log_step%    - Images are included in response%NC%
echo.
%log_header% Troubleshooting:%NC%
%log_info%    - Logs: type "!PYTHON_CMD! -c "import tempfile; print(tempfile.gettempdir())"\review_gate_v2.log"%NC%
%log_info%    - Test SoX: sox --version%NC%
%log_info%    - Browser Console: F12 in Cursor%NC%
echo.
%log_success% Enjoy your voice-activated Review Gate!%NC%

REM Final verification
%log_progress% Final verification...%NC%
if exist "!REVIEW_GATE_DIR!\review_gate_v2_mcp.py" (
    if exist "!CURSOR_MCP_FILE!" (
        if exist "!REVIEW_GATE_DIR!\venv" (
            %log_success% All components installed successfully%NC%
            if "!SHOULD_PAUSE!"=="1" pause
            exit /b 0
        )
    )
)

%log_error% Some components may not have installed correctly%NC%
%log_info% Please check the installation manually%NC%
if "!SHOULD_PAUSE!"=="1" pause
exit /b 1
