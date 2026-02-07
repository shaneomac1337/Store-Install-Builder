# ============================================================================
# On-demand hostname detection test (PowerShell 7)
#
# Spins up a Docker container per hostname, mounts the generated install dir,
# and runs: cd C:\install; .\GKInstall.ps1 -ComponentType ONEX
#
# Usage:
#   pwsh ./scripts/test-hostname.ps1                          # All NEXA test cases
#   pwsh ./scripts/test-hostname.ps1 RO93L01-R005             # Single hostname
#   pwsh ./scripts/test-hostname.ps1 RO93L01-R005 1234-101    # Multiple hostnames
# ============================================================================

param(
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$Hostnames
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$InstallDir = Join-Path $ProjectDir "QA" "qa.cloud4retail.co"

# Detect which script to test
$HasPs1 = Test-Path (Join-Path $InstallDir "GKInstall.ps1")
$HasSh = Test-Path (Join-Path $InstallDir "GKInstall.sh")

if ($HasPs1) {
    $DockerImage = "mcr.microsoft.com/powershell:lts-ubuntu-22.04"
    $RunCmd = 'cd /install && pwsh -NoProfile -File ./GKInstall.ps1 -ComponentType ONEX'
    $ScriptName = "GKInstall.ps1"
} elseif ($HasSh) {
    $DockerImage = "ubuntu:22.04"
    $RunCmd = 'cd /install && timeout 15 ./GKInstall.sh --ComponentType ONEX 2>&1 || true'
    $ScriptName = "GKInstall.sh"
} else {
    Write-Host "Error: No GKInstall.ps1 or GKInstall.sh found in $InstallDir" -ForegroundColor Red
    exit 1
}

Write-Host "Using: $InstallDir"
Write-Host "Script: $ScriptName"
Write-Host "Image: $DockerImage"
Write-Host ""

# Default NEXA test hostnames
if (-not $Hostnames -or $Hostnames.Count -eq 0) {
    $Hostnames = @(
        "RO93L01-R005"
        "RO93L02-R005"
        "BE93L01-1234"
        "DE93L50-STORE42"
        "RO33S01-R005"
        "RO03S01-R005"
        "RO97W01-R005"
        "1234-101"
        "R005-101"
        "localhost"
    )
}

# Pull image if needed
$null = docker image inspect $DockerImage 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pulling $DockerImage ..."
    docker pull $DockerImage
}

$FilterPattern = 'Hostname|Computer name|environment|Store Number|Workstation ID|StoreNr|WorkstationId|does not match|NO MATCH|NEVER_MATCH|Matched|Extracted|Detection'

foreach ($hn in $Hostnames) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  HOSTNAME: $hn" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan

    $output = docker run --rm --hostname $hn `
        -v "${InstallDir}:/install" `
        $DockerImage `
        bash -c $RunCmd 2>&1

    $output | Select-String -Pattern $FilterPattern | ForEach-Object { $_.Line }

    Write-Host ""
}
