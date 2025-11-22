<#
.SYNOPSIS
    Coop Sweden WDM Installation Wrapper
.DESCRIPTION
    Convenience script for installing WDM component with Coop-specific defaults
#>

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Coop Sweden WDM Installation" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installing WDM component with:"
Write-Host "- Workstation ID: 200"
Write-Host "- Offline Mode: Enabled"
Write-Host ""

# Call main installation script with Coop defaults
& "$PSScriptRoot\GKInstall.ps1" -ComponentType WDM -workstationId 200 -offline
