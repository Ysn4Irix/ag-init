# ag-init Windows Bootstrap Installer
# Installs uv (if missing) and ag-init globally without requiring pre-installed Python.
# Usage:
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/Ysn4Irix/ag-init/main/install.ps1 | iex"

$ErrorActionPreference = 'Stop'

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "       ag-init Windows Bootstrap Installer        " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Check or install uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[*] uv is not installed. Bootstrapping standalone uv..." -ForegroundColor Yellow
    Write-Host "    (Astral uv requires zero pre-installed Python or admin privileges)" -ForegroundColor DarkGray
    
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    
    # Refresh PATH for current session
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $sysPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $localBin = "$env:USERPROFILE\.local\bin"
    $env:Path = "$localBin;$userPath;$sysPath"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Failed to find uv on PATH after installation." -ForegroundColor Red
    Write-Host "    Please restart your terminal and re-run." -ForegroundColor Red
    exit 1
}

Write-Host "[+] uv is available: $(uv --version)" -ForegroundColor Green

# 2. Install ag-init
$targetRepo = if ($env:AG_INIT_REPO) { $env:AG_INIT_REPO } else { "git+https://github.com/Ysn4Irix/ag-init.git" }
Write-Host "[*] Installing ag-init from $targetRepo..." -ForegroundColor Cyan

uv tool install --force $targetRepo

Write-Host "`n[+] ag-init installed successfully!" -ForegroundColor Green
Write-Host "[+] You can now run: ag-init --help`n" -ForegroundColor Cyan
