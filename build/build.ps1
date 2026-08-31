# build.ps1
#
# One-time build script: run this ONCE on your Windows machine to produce
# the standalone app (dist\BTSpeakerMirror\BTSpeakerMirror.exe) and, if
# Inno Setup is installed, the final installer
# (installer\Output\BTSpeakerMirrorSetup.exe).
#
# Usage (from the project root, in PowerShell):
#   .\build\build.ps1
#
# This does NOT need to run every time you use the app - only when you
# want to (re)package it after a code change.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "== Installing build dependencies ==" -ForegroundColor Cyan
pip install --user -r requirements.txt pyinstaller

Write-Host "== Building BTSpeakerMirror.exe with PyInstaller ==" -ForegroundColor Cyan
if (Test-Path "$ProjectRoot\build\dist") { Remove-Item "$ProjectRoot\build\dist" -Recurse -Force }
if (Test-Path "$ProjectRoot\build\__pycache__") { Remove-Item "$ProjectRoot\build\__pycache__" -Recurse -Force }
pyinstaller --distpath "$ProjectRoot\dist" --workpath "$ProjectRoot\build\work" "$ProjectRoot\build\bt_speaker_mirror.spec"

if (-not (Test-Path "$ProjectRoot\dist\BTSpeakerMirror\BTSpeakerMirror.exe")) {
    Write-Error "Build failed: BTSpeakerMirror.exe was not produced. Check the PyInstaller output above."
    exit 1
}
Write-Host "Built: $ProjectRoot\dist\BTSpeakerMirror\BTSpeakerMirror.exe" -ForegroundColor Green

# --- Optional: compile the installer with Inno Setup, if available ---
$IsccCandidates = @(
    "$Env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$Env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($Iscc) {
    Write-Host "== Compiling installer with Inno Setup ==" -ForegroundColor Cyan
    & $Iscc "$ProjectRoot\installer\setup.iss"
    Write-Host "Installer built: $ProjectRoot\installer\Output\BTSpeakerMirrorSetup.exe" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Inno Setup (ISCC.exe) was not found, so the Setup.exe installer was NOT built." -ForegroundColor Yellow
    Write-Host "Download it (free) from https://jrsoftware.org/isdl.php, install it, then either:" -ForegroundColor Yellow
    Write-Host "  - re-run this script, or" -ForegroundColor Yellow
    Write-Host "  - open installer\setup.iss in Inno Setup and click Compile." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The app itself already works without the installer - you can run it directly from:" -ForegroundColor Yellow
    Write-Host "  $ProjectRoot\dist\BTSpeakerMirror\BTSpeakerMirror.exe" -ForegroundColor Yellow
}
