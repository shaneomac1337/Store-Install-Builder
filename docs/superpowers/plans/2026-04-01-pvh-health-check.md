# PVH Post-Install Health Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable post-install health check to PVH wrapper scripts that verifies the ONEX installation is functional after GKInstall succeeds, triggering rollback if it isn't.

**Architecture:** After GKInstall exits 0, run a sequential health check: immediate filesystem checks (folder + key file), then a polling port+process check. On any failure, set the existing `$gkInstallFailed` flag and fall through to existing rollback logic — no code duplication.

**Tech Stack:** PowerShell (primary), Bash (secondary)

**Spec:** `docs/superpowers/specs/2026-04-01-pvh-health-check-design.md`

---

### Task 1: Add health check configuration and CLI parameter (PowerShell)

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1:63-64` (param block)
- Modify: `pvh_wrapper/PVH-GKInstall.ps1:76-81` (config variables section)

- [ ] **Step 1: Add `-SkipHealthCheck` switch to param block**

In `pvh_wrapper/PVH-GKInstall.ps1`, change the PVH-specific parameters section at lines 61-64 from:

```powershell
    # PVH-specific parameters
    [string]$HostnameOverride,  # Override hostname for testing
    [switch]$SkipBackup           # Skip backup/rollback mechanism
)
```

to:

```powershell
    # PVH-specific parameters
    [string]$HostnameOverride,    # Override hostname for testing
    [switch]$SkipBackup,          # Skip backup/rollback mechanism
    [switch]$SkipHealthCheck      # Skip post-install health check
)
```

- [ ] **Step 2: Add health check configuration variables**

In `pvh_wrapper/PVH-GKInstall.ps1`, after the `$pvhEnvironment` block (line 81), add:

```powershell
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
```

- [ ] **Step 3: Add health check to summary display**

In `pvh_wrapper/PVH-GKInstall.ps1`, after the `Environment` line in the Resolved Values display (line 135), add:

```powershell
Write-Host "  Health Check:       $(if ($SkipHealthCheck -or -not $enableHealthCheck) { 'Disabled' } else { 'Enabled (port timeout: ' + $healthCheckTimeout + 's)' })" -ForegroundColor $(if ($SkipHealthCheck -or -not $enableHealthCheck) { 'Yellow' } else { 'Green' })
```

- [ ] **Step 4: Add health check to dry-run output**

In `pvh_wrapper/PVH-GKInstall.ps1`, after the existing dry-run rollback display (around line 396), before `"[PVH] Dry run complete."`, add:

```powershell
    if (-not $SkipHealthCheck -and $enableHealthCheck) {
        Write-Host ""
        Write-Host "[PVH] DRY RUN - After successful GKInstall, would perform health checks:" -ForegroundColor Yellow
        Write-Host "  1. Check folder exists: $healthCheckOnexPath" -ForegroundColor Yellow
        Write-Host "  2. Check file exists: $healthCheckStationFile" -ForegroundColor Yellow
        Write-Host "  3. Poll for Java process on port $healthCheckPort (every ${healthCheckInterval}s, up to ${healthCheckTimeout}s)" -ForegroundColor Yellow
        Write-Host "  4. On failure: trigger rollback" -ForegroundColor Yellow
    }
```

- [ ] **Step 5: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): add health check config variables and -SkipHealthCheck param"
```

---

### Task 2: Implement health check logic (PowerShell)

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1:520-526` (success path)

- [ ] **Step 1: Add health check section after GKInstall success**

In `pvh_wrapper/PVH-GKInstall.ps1`, replace the success block at lines 520-526:

```powershell
} else {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 completed successfully." -ForegroundColor Green
    if ($backupCreated) {
        Write-Host "[PVH] Backup preserved at: $backupDest" -ForegroundColor Gray
    }
}
```

with:

```powershell
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

    # Final success message (only if health check passed or was skipped)
    if (-not $gkInstallFailed) {
        if ($backupCreated) {
            Write-Host "[PVH] Backup preserved at: $backupDest" -ForegroundColor Gray
        }
    }
}

# ============================================================
# 9. ROLLBACK IF HEALTH CHECK FAILED
# ============================================================
if ($gkInstallFailed -and $exitCode -ne 0 -and -not $backupRolledBack) {
```

**Important:** This requires restructuring section 7. The existing rollback `if ($gkInstallFailed)` block (lines 426-519) needs to be extracted into a reusable block. The simplest approach: after the health check sets `$gkInstallFailed = $true`, we need the rollback logic to execute. See Step 2 for the restructuring.

- [ ] **Step 2: Restructure rollback to run after health check too**

The current structure is:

```
if ($gkInstallFailed) {
    # rollback
} else {
    # success + health check
}
exit $exitCode
```

Replace the entire section 7 through end of file (lines 423-528) with:

```powershell
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
```

- [ ] **Step 3: Verify the script parses correctly**

Run: `powershell -NoProfile -Command "& { $null = [System.Management.Automation.Language.Parser]::ParseFile('pvh_wrapper/PVH-GKInstall.ps1', [ref]$null, [ref]$null) ; Write-Host 'Parse OK' }"`

Expected: `Parse OK` with no errors.

- [ ] **Step 4: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): implement post-install health check with rollback on failure"
```

---

### Task 3: Implement health check in Bash wrapper

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.sh:38-43` (defaults section)
- Modify: `pvh_wrapper/PVH-GKInstall.sh:50-86` (arg parsing)
- Modify: `pvh_wrapper/PVH-GKInstall.sh:177-184` (execution section)

- [ ] **Step 1: Add health check config variables and CLI flag**

In `pvh_wrapper/PVH-GKInstall.sh`, after the `PVH_ENVIRONMENT` block (line 36), the existing DEFAULTS section starts. Add the health check config before DEFAULTS, and add `SKIP_HEALTH_CHECK` to defaults:

After line 36 (`PVH_ENVIRONMENT="PVHTST2"`), add:

```bash
# ============================================================
# CONFIGURABLE HEALTH CHECK
# Post-install verification: checks ONEX folder, station.properties,
# and Java process on port 3333. Triggers rollback on failure.
# ============================================================
ENABLE_HEALTH_CHECK=true
HEALTH_CHECK_TIMEOUT=600
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_ONEX_PATH="/usr/local/gkretail/onex"
HEALTH_CHECK_STATION_FILE="/usr/local/gkretail/onex/station.properties"
HEALTH_CHECK_PORT=3333
```

In the DEFAULTS section (line 40-43), add after `PASSTHROUGH_ARGS=()`:

```bash
SKIP_HEALTH_CHECK=false
```

- [ ] **Step 2: Add `--skip-health-check` to arg parsing**

In `pvh_wrapper/PVH-GKInstall.sh`, add a new case in the argument parser (after the `--dry-run` case around line 52):

```bash
        --skip-health-check|--SkipHealthCheck)
            SKIP_HEALTH_CHECK=true
            shift
            ;;
```

- [ ] **Step 3: Add health check to summary display**

In `pvh_wrapper/PVH-GKInstall.sh`, after the `Environment` line (line 149), add:

```bash
if [ "$SKIP_HEALTH_CHECK" = true ] || [ "$ENABLE_HEALTH_CHECK" != true ]; then
    echo "  Health Check:       Disabled"
else
    echo "  Health Check:       Enabled (port timeout: ${HEALTH_CHECK_TIMEOUT}s)"
fi
```

- [ ] **Step 4: Add health check to dry-run output**

In `pvh_wrapper/PVH-GKInstall.sh`, in the dry-run block (around line 177), before `"[PVH] Dry run complete."`, add:

```bash
    if [ "$SKIP_HEALTH_CHECK" != true ] && [ "$ENABLE_HEALTH_CHECK" = true ]; then
        echo ""
        echo "[PVH] DRY RUN - After successful GKInstall, would perform health checks:"
        echo "  1. Check folder exists: $HEALTH_CHECK_ONEX_PATH"
        echo "  2. Check file exists: $HEALTH_CHECK_STATION_FILE"
        echo "  3. Poll for Java process on port $HEALTH_CHECK_PORT (every ${HEALTH_CHECK_INTERVAL}s, up to ${HEALTH_CHECK_TIMEOUT}s)"
        echo "  4. On failure: trigger rollback"
    fi
```

- [ ] **Step 5: Replace `exec` with health check logic**

In `pvh_wrapper/PVH-GKInstall.sh`, replace the final execution block (lines 184-188):

```bash
echo "[PVH] Calling GKInstall.sh..."
echo "[PVH] Command: GKInstall.sh ${gkinstall_args[*]}"
echo ""

exec "$gkinstall_path" "${gkinstall_args[@]}"
```

with:

```bash
echo "[PVH] Calling GKInstall.sh..."
echo "[PVH] Command: GKInstall.sh ${gkinstall_args[*]}"
echo ""

set +e
"$gkinstall_path" "${gkinstall_args[@]}"
gk_exit_code=$?
set -e

if [ $gk_exit_code -ne 0 ]; then
    echo ""
    echo "========================================"
    echo " GKInstall FAILED (exit code: $gk_exit_code)"
    echo "========================================"
    exit $gk_exit_code
fi

echo ""
echo "[PVH] GKInstall.sh completed successfully (exit code: 0)."

# ============================================================
# 8. POST-INSTALL HEALTH CHECK
# ============================================================
health_check_passed=true
health_check_reason=""

if [ "$SKIP_HEALTH_CHECK" != true ] && [ "$ENABLE_HEALTH_CHECK" = true ]; then
    echo ""
    echo "========================================"
    echo " Post-Install Health Check"
    echo "========================================"

    # Check 1: ONEX folder exists
    printf "[PVH] [1/3] Checking %s exists... " "$HEALTH_CHECK_ONEX_PATH"
    if [ -d "$HEALTH_CHECK_ONEX_PATH" ]; then
        echo "OK"
    else
        echo "FAILED"
        health_check_passed=false
        health_check_reason="ONEX folder not found at $HEALTH_CHECK_ONEX_PATH"
    fi

    # Check 2: station.properties exists (only if check 1 passed)
    if [ "$health_check_passed" = true ]; then
        printf "[PVH] [2/3] Checking %s exists... " "$HEALTH_CHECK_STATION_FILE"
        if [ -f "$HEALTH_CHECK_STATION_FILE" ]; then
            echo "OK"
        else
            echo "FAILED"
            health_check_passed=false
            health_check_reason="station.properties not found at $HEALTH_CHECK_STATION_FILE"
        fi
    fi

    # Check 3: Java process on port (only if checks 1-2 passed)
    if [ "$health_check_passed" = true ]; then
        max_attempts=$(( HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL ))
        echo "[PVH] [3/3] Waiting for Java process on port $HEALTH_CHECK_PORT (timeout: $(( HEALTH_CHECK_TIMEOUT / 60 ))m)..."
        port_check_passed=false

        for attempt in $(seq 1 $max_attempts); do
            sleep "$HEALTH_CHECK_INTERVAL"
            elapsed=$(( attempt * HEALTH_CHECK_INTERVAL ))
            minutes=$(( elapsed / 60 ))
            seconds=$(( elapsed % 60 ))
            time_str=$(printf "%d:%02d" $minutes $seconds)

            printf "[PVH]        Attempt %d/%d (%s elapsed)... " "$attempt" "$max_attempts" "$time_str"

            pid=$(ss -tlnp sport = :$HEALTH_CHECK_PORT 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
            if [ -n "$pid" ]; then
                comm=$(cat /proc/$pid/comm 2>/dev/null || echo "unknown")
                if [ "$comm" = "java" ]; then
                    echo "Java process detected on port $HEALTH_CHECK_PORT (PID: $pid). OK"
                    port_check_passed=true
                    break
                else
                    echo "port in use but not Java (process: $comm)"
                fi
            else
                echo "not yet"
            fi
        done

        if [ "$port_check_passed" != true ]; then
            health_check_passed=false
            health_check_reason="No Java process listening on port $HEALTH_CHECK_PORT after $HEALTH_CHECK_TIMEOUT seconds"
        fi
    fi

    # Result
    if [ "$health_check_passed" = true ]; then
        echo ""
        echo "[PVH] === Health Check PASSED ==="
    else
        echo ""
        echo "[PVH] === Health Check FAILED ==="
        echo "[PVH] Reason: $health_check_reason"
        exit 1
    fi
else
    echo "[PVH] Health check skipped."
fi
```

- [ ] **Step 6: Verify syntax**

Run: `bash -n pvh_wrapper/PVH-GKInstall.sh && echo "Syntax OK"`

Expected: `Syntax OK`

- [ ] **Step 7: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.sh
git commit -m "feat(pvh): implement post-install health check in bash wrapper"
```

---

### Task 4: Update documentation

**Files:**
- Modify: `pvh_wrapper/CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md with health check info**

In `pvh_wrapper/CLAUDE.md`, add a new section after the "Key Design Decisions" section:

```markdown
### Post-Install Health Check
- **Purpose**: Verify ONEX installation is functional even when GKInstall exits 0
- **Configurable**: `$enableHealthCheck` / `ENABLE_HEALTH_CHECK` (default: true)
- **CLI override**: `-SkipHealthCheck` (PS1) / `--skip-health-check` (bash)
- **Checks (sequential, fail-fast)**:
  1. `C:\gkretail\onex` folder exists (immediate)
  2. `C:\gkretail\onex\station.properties` file exists (immediate)
  3. Java process listening on port 3333 (poll every 30s, up to 10min)
- **On failure**: Sets `$gkInstallFailed = $true` and triggers existing rollback logic
- **Paths configurable**: `$healthCheckOnexPath`, `$healthCheckStationFile`, `$healthCheckPort`
```

- [ ] **Step 2: Update testing section**

Add to the Testing section in CLAUDE.md:

```markdown
# Test with health check disabled
.\PVH-GKInstall.ps1 -HostnameOverride "A319TILL01" -SkipHealthCheck -WhatIf

# Bash with health check disabled
./PVH-GKInstall.sh --hostname-override "A319TILL01" --skip-health-check --dry-run
```

- [ ] **Step 3: Commit**

```bash
git add pvh_wrapper/CLAUDE.md
git commit -m "docs(pvh): document post-install health check feature"
```
