@echo off
setlocal enabledelayedexpansion

REM Review Gate V2 - Windows Batch Uninstaller Script
REM Author: Lakshman Turlapati

echo.
echo ========================================
echo     Review Gate V2 - Uninstaller
echo ========================================
echo.

set /p confirm="Are you sure you want to uninstall Review Gate V2? [y/N]: "
if /i not "%confirm%"=="y" if /i not "%confirm%"=="yes" (
    echo Uninstallation cancelled
    pause
    exit /b 0
)

echo.
echo Removing Review Gate V2...

REM Remove installation directory
set "REVIEW_GATE_DIR=%USERPROFILE%\cursor-extensions\review-gate-v2"
if exist "%REVIEW_GATE_DIR%" (
    rmdir /s /q "%REVIEW_GATE_DIR%"
    echo [OK] Removed installation directory
) else (
    echo [WARNING] Installation directory not found
)

REM Remove MCP configuration
set "MCP_CONFIG=%USERPROFILE%\.cursor\mcp.json"
if exist "%MCP_CONFIG%" (
    echo Updating MCP configuration...
    REM Create temporary Python script to remove review-gate-v2 from mcp.json
    echo import json > temp_remove_mcp.py
    echo import sys >> temp_remove_mcp.py
    echo try: >> temp_remove_mcp.py
    echo     with open(r'%MCP_CONFIG%', 'r') as f: >> temp_remove_mcp.py
    echo         config = json.load(f) >> temp_remove_mcp.py
    echo     config.get('mcpServers', {}).pop('review-gate-v2', None) >> temp_remove_mcp.py
    echo     with open(r'%MCP_CONFIG%', 'w') as f: >> temp_remove_mcp.py
    echo         json.dump(config, f, indent=2) >> temp_remove_mcp.py
    echo     print('✅ Removed review-gate-v2 from MCP configuration') >> temp_remove_mcp.py
    echo except Exception as e: >> temp_remove_mcp.py
    echo     print(f'⚠️ Error updating MCP config: {e}') >> temp_remove_mcp.py
    
    python temp_remove_mcp.py
    del temp_remove_mcp.py
) else (
    echo [WARNING] MCP configuration not found
)

REM Remove global rule (if exists)
set "CURSOR_RULES_DIR=%USERPROFILE%\.cursor"
if exist "%CURSOR_RULES_DIR%\ReviewGate.mdc" (
    del "%CURSOR_RULES_DIR%\ReviewGate.mdc"
    echo [OK] Removed global rule
)

REM Clean up temp files from both locations
del /q "%TEMP%\review_gate_*" 2>nul
del /q "%TEMP%\mcp_response*" 2>nul
echo [OK] Cleaned up temporary files

echo.
echo.
echo Manual Steps Required:
echo 1. Open Cursor IDE
echo 2. Go to Extensions (Ctrl+Shift+X)
echo 3. Find 'Review Gate V2 ゲート' and uninstall it
echo 4. Restart Cursor
echo.
echo.
echo Review Gate V2 uninstallation complete!
echo Note: Extension must be removed manually from Cursor
echo.
pause