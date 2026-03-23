<#
.SYNOPSIS
    PVH wrapper for GKInstall.ps1 - auto-detects store ID and workstation ID from hostname.
    Includes backup/rollback: backs up C:\gkretail before install, auto-rolls back on failure.

.DESCRIPTION
    Reads the hostname, parses it into store prefix + till number, derives storeId and workstationId,
    and calls GKInstall.ps1 with --storeId, --workstationId, and -y parameters.

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
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# BACKUP/ROLLBACK CONFIGURATION (sections 4a-4c below)
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
# 4a. STOP SERVICE (SMInfoServer on TILL01, SMInfoClient on others)
# ============================================================
if (-not $SkipBackup) {
    $svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($svc) {
        if ($WhatIfPreference) {
            Write-Host "[PVH] DRY RUN - Would stop service: $serviceName (current status: $($svc.Status))" -ForegroundColor Yellow
        } else {
            Write-Host "[PVH] Stopping service: $serviceName..." -ForegroundColor Yellow
            try {
                Stop-Service -Name $serviceName -Force -ErrorAction Stop
                (Get-Service -Name $serviceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
                Write-Host "[PVH] Service $serviceName stopped." -ForegroundColor Green
            } catch {
                Write-Host "[PVH] WARNING: Could not stop service $serviceName within 30s. Proceeding anyway." -ForegroundColor Yellow
                Write-Host "[PVH]          Error: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "[PVH] Service $serviceName not found - skipping. (This is normal if the service is not installed on this machine)" -ForegroundColor Gray
    }
}

# ============================================================
# 4b. KILL POS PROCESS (Java on port 3333)
# ============================================================
if (-not $SkipBackup) {
    $posProcessIds = Get-NetTCPConnection -LocalPort 3333 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    if ($posProcessIds) {
        if ($WhatIfPreference) {
            Write-Host "[PVH] DRY RUN - Would kill process(es) on port 3333: PID(s) $($posProcessIds -join ', ')" -ForegroundColor Yellow
        } else {
            foreach ($p in $posProcessIds) {
                Write-Host "[PVH] Killing process on port 3333 (PID: $p)..." -ForegroundColor Yellow
                Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            }
            Write-Host "[PVH] POS process(es) on port 3333 killed." -ForegroundColor Green
        }
    } else {
        Write-Host "[PVH] No process listening on port 3333 - skipping POS kill." -ForegroundColor Gray
    }
}

# ============================================================
# 4c. BACKUP C:\gkretail -> C:\gkretail_migration_backup
# ============================================================
if (-not $SkipBackup) {
    if (-not (Test-Path $backupSource)) {
        Write-Host "[PVH] No existing installation found at $backupSource - skipping backup." -ForegroundColor Yellow
        Write-Host "[PVH] GKInstall will create a fresh installation." -ForegroundColor Yellow
        if ($WhatIfPreference) {
            Write-Host "[PVH] DRY RUN - No backup needed (source does not exist)." -ForegroundColor Yellow
        }
    } else {
        if ($WhatIfPreference) {
            Write-Host "[PVH] DRY RUN - Would backup $backupSource -> $backupDest (via rename)" -ForegroundColor Yellow
        } else {
            # Clean up stale directories from prior runs
            if (Test-Path $backupFailed) {
                Write-Host "[PVH] Removing stale $backupFailed from prior run..." -ForegroundColor Gray
                Remove-Item -Path $backupFailed -Recurse -Force -ErrorAction SilentlyContinue
            }
            if (Test-Path $backupDest) {
                Write-Host "[PVH] Removing previous backup at $backupDest..." -ForegroundColor Gray
                try {
                    Remove-Item -Path $backupDest -Recurse -Force -ErrorAction Stop
                } catch {
                    Write-Host "[PVH] ERROR: Cannot remove previous backup at $backupDest" -ForegroundColor Red
                    Write-Host "[PVH]        Error: $($_.Exception.Message)" -ForegroundColor Red
                    Write-Host "[PVH]        Cannot proceed. Aborting." -ForegroundColor Red
                    exit 1
                }
            }

            Write-Host "[PVH] Backing up $backupSource -> $backupDest..." -ForegroundColor Yellow
            try {
                Rename-Item -Path $backupSource -NewName (Split-Path $backupDest -Leaf) -ErrorAction Stop
                $backupCreated = $true
                Write-Host "[PVH] Backup complete." -ForegroundColor Green
            } catch {
                Write-Host "[PVH] ERROR: Failed to backup $backupSource" -ForegroundColor Red
                Write-Host "[PVH]        Error: $($_.Exception.Message)" -ForegroundColor Red
                Write-Host "[PVH]        Cannot proceed without backup. Aborting." -ForegroundColor Red
                exit 1
            }
        }
    }
}

# ============================================================
# 5. BUILD GKINSTALL ARGUMENTS
# ============================================================
$gkInstallArgs = @{
    ComponentType   = $ComponentType
    storeId         = $storePrefix
    WorkstationId   = $workstationId
    y               = $true
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
# 6. EXECUTE GKINSTALL (or dry-run)
# ============================================================
$argsDisplay = ($gkInstallArgs.GetEnumerator() | ForEach-Object { "-$($_.Key) $($_.Value)" }) -join ' '

if ($WhatIfPreference) {
    Write-Host "[PVH] DRY RUN - Would execute:" -ForegroundColor Yellow
    Write-Host "  $gkInstallPath $argsDisplay" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[PVH] DRY RUN - On failure, would rollback:" -ForegroundColor Yellow
    Write-Host "  1. Rename $backupSource -> $backupFailed" -ForegroundColor Yellow
    Write-Host "  2. Rename $backupDest -> $backupSource" -ForegroundColor Yellow
    Write-Host "  3. Start-Service $serviceName" -ForegroundColor Yellow
    Write-Host "  4. Launch $backupSource\pos-full\run_tpos_PVH.cmd" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[PVH] Dry run complete. No changes were made." -ForegroundColor Yellow
    exit 0
}

Write-Host "[PVH] Calling GKInstall.ps1..."
Write-Host "[PVH] Command: GKInstall.ps1 $argsDisplay"
Write-Host ""

$gkInstallFailed = $false
$exitCode = 0

try {
    & $gkInstallPath @gkInstallArgs
    $scriptSucceeded = $?
    $exitCode = if ($LASTEXITCODE) { $LASTEXITCODE } else { if ($scriptSucceeded) { 0 } else { 1 } }
    if (-not $scriptSucceeded -or $exitCode -ne 0) {
        $gkInstallFailed = $true
    }
} catch {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 threw an exception: $($_.Exception.Message)" -ForegroundColor Red
    $gkInstallFailed = $true
    $exitCode = 1
}

# ============================================================
# 7. CHECK RESULT & ROLLBACK IF NEEDED
# ============================================================
if ($gkInstallFailed) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " GKInstall FAILED (exit code: $exitCode)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red

    if ($backupCreated) {
        Write-Host ""
        Write-Host "[PVH] Rolling back to pre-migration state..." -ForegroundColor Yellow

        # Step 1: Rename failed installation out of the way
        if (Test-Path $backupSource) {
            try {
                Rename-Item -Path $backupSource -NewName (Split-Path $backupFailed -Leaf) -ErrorAction Stop
                Write-Host "[PVH] Renamed failed installation to $backupFailed" -ForegroundColor Gray
            } catch {
                Write-Host "[PVH] ERROR: Cannot rename failed $backupSource to $backupFailed" -ForegroundColor Red
                Write-Host "[PVH]        Error: $($_.Exception.Message)" -ForegroundColor Red
                Write-Host "[PVH]        MANUAL RECOVERY: Restore from $backupDest" -ForegroundColor Red
                exit $exitCode
            }
        }

        # Step 2: Restore backup
        try {
            Rename-Item -Path $backupDest -NewName (Split-Path $backupSource -Leaf) -ErrorAction Stop
            Write-Host "[PVH] Restored backup to $backupSource" -ForegroundColor Green
        } catch {
            Write-Host "[PVH] ERROR: Cannot restore backup from $backupDest" -ForegroundColor Red
            Write-Host "[PVH]        Error: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "[PVH]        MANUAL RECOVERY: Rename $backupDest to $backupSource" -ForegroundColor Red
            exit $exitCode
        }

        # Step 3: Clean up failed installation (best-effort)
        if (Test-Path $backupFailed) {
            Remove-Item -Path $backupFailed -Recurse -Force -ErrorAction SilentlyContinue
            if (Test-Path $backupFailed) {
                Write-Host "[PVH] WARNING: Could not remove $backupFailed (locked files). Will be cleaned up on next run." -ForegroundColor Yellow
            }
        }

        # Step 4: Restart service
        $svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($svc) {
            Write-Host "[PVH] Restarting service: $serviceName..." -ForegroundColor Yellow
            try {
                Start-Service -Name $serviceName -ErrorAction Stop
                (Get-Service -Name $serviceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
                Write-Host "[PVH] Service $serviceName started." -ForegroundColor Green
            } catch {
                Write-Host "[PVH] WARNING: Service $serviceName did not reach Running state." -ForegroundColor Yellow
                Write-Host "[PVH]          Error: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "[PVH]          You may need to start it manually." -ForegroundColor Yellow
            }
        }

        # Step 5: Launch POS application
        $runTposPath = Join-Path $backupSource "pos-full\run_tpos_PVH.cmd"
        if (Test-Path $runTposPath) {
            Write-Host "[PVH] Launching $runTposPath..." -ForegroundColor Yellow
            Start-Process -FilePath $runTposPath
            Write-Host "[PVH] POS application launched." -ForegroundColor Green
        } else {
            Write-Host "[PVH] WARNING: $runTposPath not found - skipping POS launch." -ForegroundColor Yellow
        }

        Write-Host ""
        Write-Host "[PVH] Rollback complete. System restored to pre-migration state." -ForegroundColor Green
    } else {
        Write-Host "[PVH] No backup was created (source did not exist) - nothing to rollback." -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 completed successfully." -ForegroundColor Green
    if ($backupCreated) {
        Write-Host "[PVH] Backup preserved at: $backupDest" -ForegroundColor Gray
    }
}

exit $exitCode
