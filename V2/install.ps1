# Review Gate V2 - Windows PowerShell Installation Script
# Author: Lakshman Turlapati
# This script installs Review Gate V2 globally for Cursor IDE on Windows

# Enable strict error handling
$ErrorActionPreference = "Stop"

# Enhanced color logging functions
function Write-Error-Log { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Success-Log { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info-Log { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Yellow }
function Write-Progress-Log { param([string]$Message) Write-Host "[PROGRESS] $Message" -ForegroundColor Cyan }
function Write-Warning-Log { param([string]$Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-Step-Log { param([string]$Message) Write-Host "$Message" -ForegroundColor White }
function Write-Header-Log { param([string]$Message) Write-Host "$Message" -ForegroundColor Cyan }

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Header-Log "Review Gate V2 - Windows Installation"
Write-Header-Log "========================================="
Write-Host ""

# Check if running on Windows
if ($PSVersionTable.Platform -and $PSVersionTable.Platform -ne "Win32NT") {
    Write-Error-Log "This script is designed for Windows only"
    exit 1
}

# Check for admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Warning-Log "Administrator privileges recommended for package installations"
    Write-Info-Log "Some features may require manual installation"
}

# Scoop installation
Write-Progress-Log "Checking for Scoop package manager..."
if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
    try {
        Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Invoke-Expression (New-Object System.Net.WebClient).DownloadString('https://get.scoop.sh')
        Write-Success-Log "Scoop installed successfully"
    } catch {
        Write-Error-Log "Failed to install Scoop"
        exit 1
    }
} else {
    Write-Success-Log "Scoop already installed"
}

# SoX installation
Write-Progress-Log "Installing SoX..."
if (-not (Get-Command sox -ErrorAction SilentlyContinue)) {
    try {
        scoop bucket add extras
        scoop install sox
        Write-Success-Log "SoX installed successfully"
    } catch {
        Write-Warning-Log "Failed to install SoX via Scoop"
    }
} else {
    Write-Success-Log "SoX already installed"
}

# Python installation
Write-Progress-Log "Checking Python installation..."
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Info-Log "Python 3 is required. Install it using Scoop? (y/n)"
    $userInput = Read-Host
    if ($userInput -eq "y") {
        scoop install python
        Write-Success-Log "Python installed"
    } else {
        Write-Error-Log "Python is required. Aborting."
        exit 1
    }
}

$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }

# Set up directories
$CursorExtensionsDir = Join-Path $env:USERPROFILE "cursor-extensions"
$ReviewGateDir = Join-Path $CursorExtensionsDir "review-gate-v2"
New-Item -Path $ReviewGateDir -ItemType Directory -Force | Out-Null

# Copy files
Copy-Item (Join-Path $ScriptDir "review_gate_v2_mcp.py") $ReviewGateDir -Force
Copy-Item (Join-Path $ScriptDir "requirements_simple.txt") $ReviewGateDir -Force

# Virtual environment setup
Set-Location $ReviewGateDir
$venvPath = Join-Path $ReviewGateDir "venv"
& $pythonCmd -m venv $venvPath

$venvPython = Join-Path $venvPath "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install mcp>=1.9.2 Pillow>=10.0.0 asyncio typing-extensions>=4.14.0

try {
    & $venvPython -m pip install faster-whisper>=1.0.0
} catch {
    & $venvPython -m pip install faster-whisper>=1.0.0 --no-deps
    & $venvPython -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
}

Write-Success-Log "Dependencies installed"

# MCP config creation
$CursorMcpFile = Join-Path $env:USERPROFILE ".cursor\mcp.json"
$CursorDir = Split-Path $CursorMcpFile
New-Item -Path $CursorDir -ItemType Directory -Force | Out-Null

$pythonPath = $venvPython -replace '\\', '/'
$mcpScriptPath = (Join-Path $ReviewGateDir "review_gate_v2_mcp.py") -replace '\\', '/'
$reviewGateDirPath = $ReviewGateDir -replace '\\', '/'

$mcpServers = @{
  "mcpServers" = @{
    "review-gate-v2" = @{
      command = $pythonPath
      args = @($mcpScriptPath)
      env = @{
        PYTHONPATH = $reviewGateDirPath
        PYTHONUNBUFFERED = "1"
        REVIEW_GATE_MODE = "cursor_integration"
      }
    }
  }
}

$mcpConfigJson = $mcpServers | ConvertTo-Json -Depth 5
Set-Content -Path $CursorMcpFile -Value $mcpConfigJson -Encoding UTF8

Write-Success-Log "MCP config created: $CursorMcpFile"

# Final check
if ((Test-Path $venvPath) -and (Test-Path $CursorMcpFile)) {
    Write-Success-Log "Review Gate V2 Installed Successfully!"
} else {
    Write-Error-Log "Installation incomplete. Check log for errors."
    exit 1
}
