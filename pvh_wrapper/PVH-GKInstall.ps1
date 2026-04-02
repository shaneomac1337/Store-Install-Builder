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
    3. Releases open file handles on C:\gkretail (via Sysinternals handle.exe)
    4. Fixes permissions on C:\gkretail (grants Everyone full control via icacls)
    5. Backs up C:\gkretail to C:\gkretail_migration_backup (via rename)

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
    [string]$HostnameOverride,    # Override hostname for testing
    [switch]$SkipBackup,          # Skip backup/rollback mechanism
    [switch]$SkipHealthCheck      # Skip post-install health check
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
# CONFIGURABLE ENVIRONMENT
# Change this value when creating copies for other environments.
# Example: "PVHTST2" for test, "PVHPRD" for production
# ============================================================
$pvhEnvironment = "PVHTST2"

# ============================================================
# CONFIGURABLE HEALTH CHECK
# Post-install verification: checks ONEX folder, station.properties,
# and Java process on port 3333. Triggers rollback on failure.
# ============================================================
$enableHealthCheck    = $true    # Set to $false to disable health checks entirely
$healthCheckTimeout   = 600      # Max seconds to wait for port 3333 (default: 10 minutes)
$healthCheckInterval  = 30       # Seconds between port check attempts (default: 30s)
$healthCheckOnexPath  = "C:\gkretail\onex"
$healthCheckStationFile = "C:\gkretail\onex\station.properties"
$healthCheckPort      = 3333

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
Write-Host "  Environment:        $pvhEnvironment" -ForegroundColor Green
Write-Host "  Health Check:       $(if ($SkipHealthCheck -or -not $enableHealthCheck) { 'Disabled' } else { 'Enabled (port timeout: ' + $healthCheckTimeout + 's)' })" -ForegroundColor $(if ($SkipHealthCheck -or -not $enableHealthCheck) { 'Yellow' } else { 'Green' })
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
# 4c. KILL FILE HANDLES on C:\gkretail (using Sysinternals handle.exe)
# ============================================================
if (-not $SkipBackup) {
    $handleExe = Join-Path $PSScriptRoot "handle.exe"
    if (Test-Path $backupSource) {
        if (Test-Path $handleExe) {
            if ($WhatIfPreference) {
                Write-Host "[PVH] DRY RUN - Would kill open file handles in $backupSource using $handleExe" -ForegroundColor Yellow
            } else {
                Write-Host "[PVH] Releasing open file handles in $backupSource..." -ForegroundColor Yellow
                $handleCount = 0
                try {
                    $handleOutput = & $handleExe /accepteula -nobanner $backupSource 2>&1
                    foreach ($line in $handleOutput) {
                        # handle.exe output format: "process.exe  pid: 1234  type: File  1A4: C:\gkretail\..."
                        if ($line -match 'pid:\s*(\d+)\s+type:\s*\w+\s+([0-9A-Fa-f]+):') {
                            $handlePid = $Matches[1]
                            $handleId  = $Matches[2]
                            Write-Host "[PVH]   Releasing handle $handleId in PID $handlePid" -ForegroundColor Gray
                            & $handleExe -c $handleId -y -p $handlePid 2>&1 | Out-Null
                            $handleCount++
                        }
                    }
                    if ($handleCount -gt 0) {
                        Write-Host "[PVH] Released $handleCount file handle(s)." -ForegroundColor Green
                    } else {
                        Write-Host "[PVH] No open file handles found in $backupSource." -ForegroundColor Gray
                    }
                } catch {
                    Write-Host "[PVH] WARNING: handle.exe failed: $($_.Exception.Message)" -ForegroundColor Yellow
                    Write-Host "[PVH]          Proceeding anyway - backup rename may fail if files are locked." -ForegroundColor Yellow
                }
            }
        } else {
            # Auto-download handle.exe from Sysinternals
            Write-Host "[PVH] handle.exe not found - downloading from Sysinternals..." -ForegroundColor Yellow
            $handleZip = Join-Path $PSScriptRoot "Handle.zip"
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                Invoke-WebRequest -Uri "https://download.sysinternals.com/files/Handle.zip" -OutFile $handleZip -UseBasicParsing -ErrorAction Stop
                Expand-Archive -Path $handleZip -DestinationPath $PSScriptRoot -Force -ErrorAction Stop
                Remove-Item -Path $handleZip -Force -ErrorAction SilentlyContinue
                if (Test-Path $handleExe) {
                    Write-Host "[PVH] handle.exe downloaded successfully." -ForegroundColor Green
                    # Now run it
                    Write-Host "[PVH] Releasing open file handles in $backupSource..." -ForegroundColor Yellow
                    $handleCount = 0
                    $handleOutput = & $handleExe /accepteula -nobanner $backupSource 2>&1
                    foreach ($line in $handleOutput) {
                        if ($line -match 'pid:\s*(\d+)\s+type:\s*\w+\s+([0-9A-Fa-f]+):') {
                            $handlePid = $Matches[1]
                            $handleId  = $Matches[2]
                            Write-Host "[PVH]   Releasing handle $handleId in PID $handlePid" -ForegroundColor Gray
                            & $handleExe -c $handleId -y -p $handlePid 2>&1 | Out-Null
                            $handleCount++
                        }
                    }
                    if ($handleCount -gt 0) {
                        Write-Host "[PVH] Released $handleCount file handle(s)." -ForegroundColor Green
                    } else {
                        Write-Host "[PVH] No open file handles found in $backupSource." -ForegroundColor Gray
                    }
                } else {
                    Write-Host "[PVH] WARNING: Download succeeded but handle.exe not found in archive." -ForegroundColor Yellow
                }
            } catch {
                Write-Host "[PVH] WARNING: Could not download handle.exe: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "[PVH]          Proceeding without file handle release." -ForegroundColor Yellow
            }
        }
    }
}

# ============================================================
# 4d. FIX PERMISSIONS on C:\gkretail (grant Everyone full control)
# ============================================================
if (-not $SkipBackup) {
    if (Test-Path $backupSource) {
        $logPath = Join-Path $backupSource "pos-client\log"
        if ($WhatIfPreference) {
            Write-Host "[PVH] DRY RUN - Would grant Everyone (S-1-1-0) full control on $backupSource" -ForegroundColor Yellow
        } else {
            Write-Host "[PVH] Fixing permissions on $backupSource..." -ForegroundColor Yellow
            try {
                # Grant Everyone full control recursively on the log folder (often has restrictive ACLs)
                if (Test-Path $logPath) {
                    & icacls.exe $logPath /c /grant "*S-1-1-0:(OI)(CI)F" /t 2>&1 | Out-Null
                    Write-Host "[PVH] Granted full control on $logPath" -ForegroundColor Green
                }
                # Grant Everyone full control on the top-level folder to ensure rename succeeds
                & icacls.exe $backupSource /c /grant "*S-1-1-0:(OI)(CI)F" /t 2>&1 | Out-Null
                Write-Host "[PVH] Granted full control on $backupSource" -ForegroundColor Green
                # Wait for ACL changes to propagate across the directory tree
                Write-Host "[PVH] Waiting 10s for permission changes to propagate..." -ForegroundColor Gray
                Start-Sleep -Seconds 10
            } catch {
                Write-Host "[PVH] WARNING: icacls failed: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "[PVH]          Proceeding anyway - backup rename may fail due to permissions." -ForegroundColor Yellow
            }
        }
    }
}

# ============================================================
# 4e. BACKUP C:\gkretail -> C:\gkretail_migration_backup
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
# 6. EXECUTE GKINSTALL (or dry-run)
# ============================================================
$argsDisplay = ($gkInstallArgs.GetEnumerator() | ForEach-Object { "-$($_.Key) $($_.Value)" }) -join ' '

if ($WhatIfPreference) {
    Write-Host "[PVH] DRY RUN - Would execute:" -ForegroundColor Yellow
    Write-Host "  $gkInstallPath $argsDisplay" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[PVH] DRY RUN - On failure, would rollback:" -ForegroundColor Yellow
    Write-Host "  1. Release file handles via handle.exe" -ForegroundColor Yellow
    Write-Host "  2. Fix permissions via icacls" -ForegroundColor Yellow
    Write-Host "  3. Rename $backupSource -> $backupFailed" -ForegroundColor Yellow
    Write-Host "  4. Rename $backupDest -> $backupSource" -ForegroundColor Yellow
    Write-Host "  5. Start-Service $serviceName" -ForegroundColor Yellow
    Write-Host "  6. Launch $backupSource\pos-full\run_tpos_PVH.cmd" -ForegroundColor Yellow
    if (-not $SkipHealthCheck -and $enableHealthCheck) {
        Write-Host ""
        Write-Host "[PVH] DRY RUN - After successful GKInstall, would perform health checks:" -ForegroundColor Yellow
        Write-Host "  1. Check folder exists: $healthCheckOnexPath" -ForegroundColor Yellow
        Write-Host "  2. Check file exists: $healthCheckStationFile" -ForegroundColor Yellow
        Write-Host "  3. Poll for Java process on port $healthCheckPort (every ${healthCheckInterval}s, up to ${healthCheckTimeout}s)" -ForegroundColor Yellow
        Write-Host "  4. On failure: trigger rollback" -ForegroundColor Yellow
    }
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
# 7. CHECK GKINSTALL RESULT
# ============================================================
if ($gkInstallFailed) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " GKInstall FAILED (exit code: $exitCode)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
} else {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 completed successfully (exit code: 0)." -ForegroundColor Green

    # ============================================================
    # 8. POST-INSTALL HEALTH CHECK
    # ============================================================
    if (-not $SkipHealthCheck -and $enableHealthCheck -and -not $SkipBackup) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host " Post-Install Health Check" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        $healthCheckPassed = $true
        $healthCheckReason = ""

        # Check 1: ONEX folder exists
        Write-Host "[PVH] [1/3] Checking $healthCheckOnexPath exists... " -NoNewline
        if (Test-Path $healthCheckOnexPath) {
            Write-Host "OK" -ForegroundColor Green
        } else {
            Write-Host "FAILED" -ForegroundColor Red
            $healthCheckPassed = $false
            $healthCheckReason = "ONEX folder not found at $healthCheckOnexPath"
        }

        # Check 2: station.properties exists (only if check 1 passed)
        if ($healthCheckPassed) {
            Write-Host "[PVH] [2/3] Checking $healthCheckStationFile exists... " -NoNewline
            if (Test-Path $healthCheckStationFile) {
                Write-Host "OK" -ForegroundColor Green
            } else {
                Write-Host "FAILED" -ForegroundColor Red
                $healthCheckPassed = $false
                $healthCheckReason = "station.properties not found at $healthCheckStationFile"
            }
        }

        # Check 3: Java process on port (only if checks 1-2 passed)
        if ($healthCheckPassed) {
            $maxAttempts = [math]::Ceiling($healthCheckTimeout / $healthCheckInterval)
            Write-Host "[PVH] [3/3] Waiting for Java process on port $healthCheckPort (timeout: $($healthCheckTimeout / 60)m)..."
            $portCheckPassed = $false

            for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
                Start-Sleep -Seconds $healthCheckInterval
                $elapsed = $attempt * $healthCheckInterval
                $minutes = [math]::Floor($elapsed / 60)
                $seconds = $elapsed % 60
                $timeStr = "${minutes}:$("{0:D2}" -f $seconds)"

                Write-Host "[PVH]        Attempt $attempt/$maxAttempts ($timeStr elapsed)... " -NoNewline

                $conn = Get-NetTCPConnection -LocalPort $healthCheckPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($conn) {
                    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                    if ($proc -and $proc.ProcessName -like "*java*") {
                        Write-Host "Java process detected on port $healthCheckPort (PID: $($proc.Id)). OK" -ForegroundColor Green
                        $portCheckPassed = $true
                        break
                    } else {
                        $procName = if ($proc) { $proc.ProcessName } else { "unknown" }
                        Write-Host "port in use but not Java (process: $procName)" -ForegroundColor Yellow
                    }
                } else {
                    Write-Host "not yet" -ForegroundColor Gray
                }
            }

            if (-not $portCheckPassed) {
                $healthCheckPassed = $false
                $healthCheckReason = "No Java process listening on port $healthCheckPort after $healthCheckTimeout seconds"
            }
        }

        # Result
        if ($healthCheckPassed) {
            Write-Host ""
            Write-Host "[PVH] === Health Check PASSED ===" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "[PVH] === Health Check FAILED ===" -ForegroundColor Red
            Write-Host "[PVH] Reason: $healthCheckReason" -ForegroundColor Red
            $gkInstallFailed = $true
            $exitCode = 1
        }
    } elseif ($SkipHealthCheck -or -not $enableHealthCheck) {
        Write-Host "[PVH] Health check skipped." -ForegroundColor Yellow
    }
}

# ============================================================
# 9. ROLLBACK IF NEEDED (GKInstall failure OR health check failure)
# ============================================================
if ($gkInstallFailed -and $backupCreated) {
    Write-Host ""
    Write-Host "[PVH] Rolling back to pre-migration state..." -ForegroundColor Yellow

    # Step 0: Release file handles before rollback renames
    $handleExeRollback = Join-Path $PSScriptRoot "handle.exe"
    if (Test-Path $handleExeRollback) {
        foreach ($rollbackDir in @($backupSource, $backupDest)) {
            if (Test-Path $rollbackDir) {
                Write-Host "[PVH] Releasing file handles in $rollbackDir..." -ForegroundColor Yellow
                try {
                    $handleOutput = & $handleExeRollback /accepteula -nobanner $rollbackDir 2>&1
                    foreach ($line in $handleOutput) {
                        if ($line -match 'pid:\s*(\d+)\s+type:\s*\w+\s+([0-9A-Fa-f]+):') {
                            & $handleExeRollback -c $Matches[2] -y -p $Matches[1] 2>&1 | Out-Null
                        }
                    }
                } catch {
                    Write-Host "[PVH] WARNING: handle.exe failed during rollback: $($_.Exception.Message)" -ForegroundColor Yellow
                }
            }
        }
    }

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

    # Step 5: Launch POS application (cd into directory first, then run)
    $posFullDir  = Join-Path $backupSource "pos-full"
    $runTposCmd  = "run_tpos_PVH.cmd"
    $runTposPath = Join-Path $posFullDir $runTposCmd
    if (Test-Path $runTposPath) {
        Write-Host "[PVH] Launching $runTposCmd from $posFullDir..." -ForegroundColor Yellow
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$posFullDir`" && $runTposCmd" -WorkingDirectory $posFullDir
        Write-Host "[PVH] POS application launched." -ForegroundColor Green
    } else {
        Write-Host "[PVH] WARNING: $runTposPath not found - skipping POS launch." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "[PVH] Rollback complete. System restored to pre-migration state." -ForegroundColor Green
} elseif ($gkInstallFailed -and -not $backupCreated) {
    Write-Host "[PVH] No backup was created (source did not exist) - nothing to rollback." -ForegroundColor Yellow
} else {
    # Success
    if ($backupCreated) {
        Write-Host "[PVH] Backup preserved at: $backupDest" -ForegroundColor Gray
    }
}

exit $exitCode
