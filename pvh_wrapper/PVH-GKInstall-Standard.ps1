<#
.SYNOPSIS
    PVH STANDARD wrapper for GKInstall.ps1 - normal re-install after migration is complete.
    Auto-detects store ID and workstation ID from hostname.

.DESCRIPTION
    USE THIS VERSION FOR NORMAL RE-INSTALLS ON TILLS THAT HAVE ALREADY BEEN MIGRATED.
    For the one-time migration from SMInfoServer/SMInfoClient to ONEX-POS,
    use PVH-GKInstall-Migration.ps1 instead.

    Reads the hostname, parses it into store prefix + till number, derives storeId and workstationId,
    and calls GKInstall.ps1 with --storeId, --workstationId, and -y parameters.

    This wrapper does NOT:
    - Stop/start the SMInfo service (already Disabled after migration)
    - Kill the POS process on port 3333
    - Release open file handles
    - Fix permissions on C:\gkretail
    - Back up C:\gkretail or roll back on failure
    - Run a post-install health check

    If GKInstall fails, the wrapper exits with the underlying exit code and leaves the system
    as-is. Use PVH-GKInstall-Migration.ps1 if you need backup/rollback safety.

    Hostname format: [CC-]{StorePrefix}TILL{TillNumber}[T]
    Examples: DE-A319TILL01, DE-A319TILL01T, A319TILL01

.EXAMPLE
    .\PVH-GKInstall-Standard.ps1
    # Auto-detects everything from hostname

.EXAMPLE
    .\PVH-GKInstall-Standard.ps1 -ComponentType ONEX-POS -offline
    # Auto-detects store/workstation, passes through -ComponentType and -offline

.EXAMPLE
    .\PVH-GKInstall-Standard.ps1 -WhatIf
    # Dry-run: shows parsed values and the GKInstall command without executing
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    # GKInstall parameters (pass-through)
    [ValidateSet('POS', 'ONEX', 'ONEX-POS', 'WDM', 'FLOW-SERVICE', 'LPA', 'SH', 'LPA-SERVICE', 'STOREHUB-SERVICE', 'RCS', 'RCS-SERVICE')]
    [string]$ComponentType = 'ONEX-POS',
    [switch]$offline,
    [string]$base_url,
    [bool]$UseDefaultVersions,
    [string]$VersionSource,
    [string]$Env,
    [string]$EnvironmentName,
    [switch]$noOverrides,
    [switch]$skipCheckAlive,
    [switch]$skipStartApplication,
    [switch]$ListEnvironments,
    [string]$rcsUrl,
    [string]$SslPassword,
    [string]$VersionOverride,

    # PVH-specific parameters
    [string]$HostnameOverride     # Override hostname for testing
)

# ============================================================
# DISABLE PROXY (process-scoped only)
# Admin PowerShell sessions can inherit a corporate WinHTTP proxy
# (e.g., amsrpxy01.retailstoreseu.com:8080) that returns 503 for the
# Cloud4Retail endpoints. Clearing it forces all Invoke-WebRequest /
# curl-alias / GKInstall HTTP calls in this process to go direct.
# Affects only this PowerShell process - no system-wide change.
# ============================================================
[System.Net.WebRequest]::DefaultWebProxy = $null

# ============================================================
# CONFIGURABLE HOSTNAME PATTERN
# Adjust this regex if the hostname format changes.
# Production format: [CC-]{4-char prefix}TILL{2-digit number}[T]
#   e.g., DE-A319TILL01, DE-A319TILL01T, A319TILL01
# Optional country prefix (CC-) is ignored. Optional trailing T (test env) is ignored.
# Capture groups: (1) store prefix (4 chars), (2) till number (2 digits)
# ============================================================
$hostnamePattern = '^(?:[A-Za-z]{2}-)?([A-Za-z][A-Za-z0-9]{3})TILL(\d{2})T?$'

# ============================================================
# CONFIGURABLE ENVIRONMENT
# Change this value when creating copies for other environments.
# Example: "PVHTST2" for test, "PVHPRD" for production
# ============================================================
$pvhEnvironment = ""

# ============================================================
# 1. GET HOSTNAME
# ============================================================
if ($HostnameOverride) {
    $hostname = $HostnameOverride
    Write-Host "[PVH] Using hostname override: $hostname" -ForegroundColor Yellow
} else {
    $hostname = $env:COMPUTERNAME
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " PVH GKInstall Wrapper (Standard)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[PVH] Hostname: $hostname"

# ============================================================
# 2. PARSE HOSTNAME
# ============================================================
if ($hostname -match $hostnamePattern) {
    $storePrefix = $Matches[1]
    $tillNumber  = [int]$Matches[2]
} else {
    Write-Host ""
    Write-Host "[PVH] ERROR: Hostname '$hostname' does not match expected pattern." -ForegroundColor Red
    Write-Host "[PVH] Expected format: [CC-]{StorePrefix}TILL{TillNumber}[T]" -ForegroundColor Red
    Write-Host "[PVH] Examples: DE-A319TILL01, DE-A319TILL01T, A319TILL01" -ForegroundColor Red
    Write-Host "[PVH] Pattern: $hostnamePattern" -ForegroundColor Red
    Write-Host ""
    Write-Host "[PVH] To test with a different hostname, use: -HostnameOverride 'DE-A319TILL01'" -ForegroundColor Yellow
    exit 1
}

Write-Host "[PVH] Parsed -> Store: $storePrefix | Till: $tillNumber"

# ============================================================
# 3. DERIVE WORKSTATION ID
# ============================================================
$workstationId = 100 + $tillNumber                          # TILL01 -> 101

# ============================================================
# 4. DISPLAY SUMMARY
# ============================================================
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host " Resolved Values:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "  Store ID:           $storePrefix" -ForegroundColor Green
Write-Host "  Till Number:        $tillNumber"
Write-Host "  Workstation ID:     $workstationId" -ForegroundColor Green
Write-Host "  Auto-Confirm:       Yes (-y)" -ForegroundColor Green
Write-Host "  Component Type:     $ComponentType"
Write-Host "  Environment:        $pvhEnvironment" -ForegroundColor Green
Write-Host "  Mode:               Standard (no backup/rollback/health check)" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# Early check: ensure GKInstall.ps1 exists before proceeding
$gkInstallPath = Join-Path $PSScriptRoot "GKInstall.ps1"
if (-not $WhatIfPreference -and -not (Test-Path $gkInstallPath)) {
    Write-Host "[PVH] ERROR: GKInstall.ps1 not found at $gkInstallPath" -ForegroundColor Red
    Write-Host "[PVH]        Cannot proceed. Aborting." -ForegroundColor Red
    exit 1
}

# ============================================================
# 5. BUILD GKINSTALL ARGUMENTS
# ============================================================
$gkInstallArgs = @{
    ComponentType   = $ComponentType
    storeId         = $storePrefix
    WorkstationId   = $workstationId
    Env             = $pvhEnvironment
    y               = $true
}

# Pass through optional parameters that were explicitly specified
if ($offline)                                             { $gkInstallArgs['offline']              = $true }
if ($PSBoundParameters.ContainsKey('base_url'))           { $gkInstallArgs['base_url']             = $base_url }
if ($PSBoundParameters.ContainsKey('UseDefaultVersions')) { $gkInstallArgs['UseDefaultVersions']   = $UseDefaultVersions }
if ($PSBoundParameters.ContainsKey('VersionSource'))      { $gkInstallArgs['VersionSource']        = $VersionSource }
# Note: -Env is always set from $pvhEnvironment above; CLI override still possible
if ($PSBoundParameters.ContainsKey('Env'))                { $gkInstallArgs['Env']                  = $Env }
if ($PSBoundParameters.ContainsKey('EnvironmentName'))    { $gkInstallArgs['EnvironmentName']      = $EnvironmentName }
if ($noOverrides)                                         { $gkInstallArgs['noOverrides']          = $true }
if ($skipCheckAlive)                                      { $gkInstallArgs['skipCheckAlive']       = $true }
if ($skipStartApplication)                                { $gkInstallArgs['skipStartApplication'] = $true }
if ($ListEnvironments)                                    { $gkInstallArgs['ListEnvironments']     = $true }
if ($PSBoundParameters.ContainsKey('rcsUrl'))             { $gkInstallArgs['rcsUrl']               = $rcsUrl }
if ($PSBoundParameters.ContainsKey('SslPassword'))        { $gkInstallArgs['SslPassword']          = $SslPassword }
if ($PSBoundParameters.ContainsKey('VersionOverride'))    { $gkInstallArgs['VersionOverride']      = $VersionOverride }

# ============================================================
# 6. DISPLAY COMMAND / DRY RUN
# ============================================================
$argsDisplay = ($gkInstallArgs.GetEnumerator() | ForEach-Object { "-$($_.Key) $($_.Value)" }) -join ' '

if ($WhatIfPreference) {
    Write-Host "[PVH] DRY RUN - Would execute:" -ForegroundColor Yellow
    Write-Host "  $gkInstallPath $argsDisplay" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[PVH] DRY RUN complete. No changes made." -ForegroundColor Yellow
    exit 0
}

Write-Host "[PVH] Calling GKInstall.ps1..."
Write-Host "[PVH] Command: GKInstall.ps1 $argsDisplay"
Write-Host ""

# ============================================================
# 7. CALL GKINSTALL
# ============================================================
$exitCode = 0
try {
    & $gkInstallPath @gkInstallArgs
    $scriptSucceeded = $?
    $exitCode = if ($LASTEXITCODE) { $LASTEXITCODE } else { if ($scriptSucceeded) { 0 } else { 1 } }
} catch {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 threw an exception: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}

# ============================================================
# 8. REPORT RESULT
# ============================================================
if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " GKInstall FAILED (exit code: $exitCode)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
} else {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 completed successfully (exit code: 0)." -ForegroundColor Green
}

exit $exitCode
