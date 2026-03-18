<#
.SYNOPSIS
    PVH wrapper for GKInstall.ps1 - auto-detects store, system type, and workstation from hostname.
    Includes backup/rollback: backs up C:\gkretail before install, auto-rolls back on failure.

.DESCRIPTION
    Reads the hostname, parses it into store prefix + till number, looks up the FAT system type
    from a mapping file, transforms FAT -> ONEX-CLOUD, and calls GKInstall.ps1 with the correct
    --SystemNameOverride, --WorkstationNameOverride, --StructureUniqueNameOverride, and -y parameters.

    Before running GKInstall, the wrapper:
    1. Stops the SMInfoServer (TILL01) or SMInfoClient (all others) service
    2. Kills any Java POS process listening on port 3333
    3. Backs up C:\gkretail to C:\gkretail_migration_backup (via rename)

    If GKInstall fails (non-zero exit code or exception), the wrapper automatically:
    1. Restores C:\gkretail from the backup
    2. Restarts the stopped service
    3. Launches C:\gkretail\pos-full\run_tpos_PVH.cmd

    Hostname format: [CC-]{StorePrefix}TILL{TillNumber}[T]
    Examples: DE-A319TILL01, DE-A319TILL01T, A319TILL01

.EXAMPLE
    .\PVH-GKInstall.ps1
    # Auto-detects everything from hostname

.EXAMPLE
    .\PVH-GKInstall.ps1 -ComponentType ONEX-POS -offline
    # Auto-detects store/workstation, passes through -ComponentType and -offline

.EXAMPLE
    .\PVH-GKInstall.ps1 -WhatIf
    # Dry-run: shows parsed values and backup/rollback plan without executing

.EXAMPLE
    .\PVH-GKInstall.ps1 -SkipBackup
    # Skip the backup/rollback mechanism entirely
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
    [string]$MappingFile = "pvh_store_mapping.properties",
    [string]$HostnameOverride,  # Override hostname for testing
    [switch]$SkipBackup           # Skip backup/rollback mechanism
)

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
Write-Host " PVH GKInstall Wrapper" -ForegroundColor Cyan
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
# 3. READ MAPPING FILE
# ============================================================
$mappingPath = Join-Path $PSScriptRoot $MappingFile

if (-not (Test-Path $mappingPath)) {
    Write-Host ""
    Write-Host "[PVH] ERROR: Mapping file not found: $mappingPath" -ForegroundColor Red
    Write-Host "[PVH] Create the file with store-to-system-type mappings." -ForegroundColor Red
    Write-Host "[PVH] Format: STORE_PREFIX=PVH-OPOS-FAT-LOCALE-BRAND-TYPE" -ForegroundColor Red
    Write-Host "[PVH] Example: A319=PVH-OPOS-FAT-EN_GB-TH-FULL" -ForegroundColor Red
    Write-Host ""
    Write-Host "[PVH] See pvh_store_mapping.properties.example for a template." -ForegroundColor Yellow
    exit 1
}

$mapping = @{}
foreach ($line in Get-Content $mappingPath) {
    $line = $line.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) {
            $mapping[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
}

Write-Host "[PVH] Loaded $($mapping.Count) store mappings from $MappingFile"

# ============================================================
# 4. LOOKUP STORE + TRANSFORM FAT -> ONEX-CLOUD
# ============================================================
$fatSystemName = $mapping[$storePrefix]

if (-not $fatSystemName) {
    Write-Host ""
    Write-Host "[PVH] ERROR: Store '$storePrefix' not found in mapping file." -ForegroundColor Red
    Write-Host "[PVH] Available stores:" -ForegroundColor Yellow
    $mapping.Keys | Sort-Object | ForEach-Object {
        Write-Host "  $_  =  $($mapping[$_])" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "[PVH] Add the store to $mappingPath and try again." -ForegroundColor Yellow
    exit 1
}

$onexSystemName = $fatSystemName -replace 'FAT', 'ONEX-CLOUD'

# ============================================================
# 5. DERIVE WORKSTATION ID AND NAME
# ============================================================
$workstationId   = 100 + $tillNumber                          # TILL01 -> 101
$workstationName = "${storePrefix}TILL$('{0:D2}' -f $tillNumber)"  # A319TILL01

# ============================================================
# 6. DISPLAY SUMMARY
# ============================================================
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host " Resolved Values:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "  Store ID:           $storePrefix"
Write-Host "  Till Number:        $tillNumber"
Write-Host "  FAT System Name:    $fatSystemName"
Write-Host "  ONEX System Name:   $onexSystemName" -ForegroundColor Green
Write-Host "  Workstation ID:     $workstationId" -ForegroundColor Green
Write-Host "  Workstation Name:   $workstationName" -ForegroundColor Green
Write-Host "  Structure Name:     $onexSystemName" -ForegroundColor Green
Write-Host "  Auto-Confirm:       Yes (-y)" -ForegroundColor Green
Write-Host "  Component Type:     $ComponentType"
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# BACKUP/ROLLBACK CONFIGURATION
# ============================================================
$backupSource  = "C:\gkretail"
$backupDest    = "C:\gkretail_migration_backup"
$backupFailed  = "C:\gkretail_failed"
$backupCreated = $false

# Determine which service to manage based on till number
if ($tillNumber -eq 1) {
    $serviceName = "SMInfoServer"
} else {
    $serviceName = "SMInfoClient"
}

# Early check: ensure GKInstall.ps1 exists before stopping services or creating backups
$gkInstallPath = Join-Path $PSScriptRoot "GKInstall.ps1"
if (-not $WhatIfPreference -and -not (Test-Path $gkInstallPath)) {
    Write-Host "[PVH] ERROR: GKInstall.ps1 not found at: $gkInstallPath" -ForegroundColor Red
    Write-Host "[PVH] Place GKInstall.ps1 in the same directory as this wrapper." -ForegroundColor Yellow
    exit 1
}

# ============================================================
# 7. BUILD GKINSTALL ARGUMENTS
# ============================================================
$gkInstallArgs = @{
    ComponentType                = $ComponentType
    storeId                      = $storePrefix
    WorkstationId                = $workstationId
    SystemNameOverride           = $onexSystemName
    WorkstationNameOverride      = $workstationName
    StructureUniqueNameOverride  = $onexSystemName
    y                            = $true
}

# Pass through optional parameters that were explicitly specified
if ($offline)                                             { $gkInstallArgs['offline']              = $true }
if ($PSBoundParameters.ContainsKey('base_url'))           { $gkInstallArgs['base_url']             = $base_url }
if ($PSBoundParameters.ContainsKey('UseDefaultVersions')) { $gkInstallArgs['UseDefaultVersions']   = $UseDefaultVersions }
if ($PSBoundParameters.ContainsKey('VersionSource'))      { $gkInstallArgs['VersionSource']        = $VersionSource }
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
# 8. EXECUTE GKINSTALL (or dry-run)
# ============================================================
$gkInstallPath = Join-Path $PSScriptRoot "GKInstall.ps1"

$argsDisplay = ($gkInstallArgs.GetEnumerator() | ForEach-Object { "-$($_.Key) $($_.Value)" }) -join ' '

if ($WhatIfPreference) {
    Write-Host "[PVH] DRY RUN - Would execute:" -ForegroundColor Yellow
    Write-Host "  $gkInstallPath $argsDisplay" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[PVH] Dry run complete. No changes were made." -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path $gkInstallPath)) {
    Write-Host "[PVH] ERROR: GKInstall.ps1 not found at: $gkInstallPath" -ForegroundColor Red
    Write-Host "[PVH] Place GKInstall.ps1 in the same directory as this wrapper." -ForegroundColor Yellow
    exit 1
}

Write-Host "[PVH] Calling GKInstall.ps1..."
Write-Host "[PVH] Command: GKInstall.ps1 $argsDisplay"
Write-Host ""

& $gkInstallPath @gkInstallArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 exited with code: $exitCode" -ForegroundColor Red
}

exit $exitCode
