<#
.SYNOPSIS
    Coop Sweden WDM Installation Wrapper
.DESCRIPTION
    Convenience script for installing WDM component with Coop-specific defaults
    Automatically requests administrator privileges if not already running as admin
#>

# Self-elevate the script if required
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
    Write-Host "Please click 'Yes' in the UAC prompt to continue." -ForegroundColor Yellow
    Start-Sleep -Seconds 2

    # Relaunch as administrator with explicit directory change
    $scriptPath = $PSCommandPath
    $scriptDir = $PSScriptRoot
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$scriptDir'; & '$scriptPath'`"" -Verb RunAs
    exit
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Coop Sweden WDM Installation" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Running with administrator privileges" -ForegroundColor Green
Write-Host ""
Write-Host "Installing WDM component with:"
Write-Host "- Workstation ID: 200"
Write-Host "- Offline Mode: Enabled"
Write-Host ""

# Call main installation script with Coop defaults
& "$PSScriptRoot\GKInstall.ps1" -ComponentType WDM -workstationId 200 -offline

# Pause at the end so user can see the results
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
