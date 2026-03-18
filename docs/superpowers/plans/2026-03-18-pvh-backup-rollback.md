# PVH Backup & Rollback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backup and automatic rollback capability to `PVH-GKInstall.ps1` so failed GKInstall runs can be recovered from automatically.

**Architecture:** All logic lives in `PVH-GKInstall.ps1`. New sections are inserted between the existing summary display (section 6) and argument building (section 7) for pre-install steps, and after execution (section 8) for post-install rollback. Uses `Rename-Item` for instant backup/restore on same volume.

**Tech Stack:** PowerShell 5.1+, Windows services API (`Stop-Service`/`Start-Service`/`Get-Service`), `Get-NetTCPConnection` for port-based process detection.

**Spec:** `docs/superpowers/specs/2026-03-18-pvh-backup-rollback-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `pvh_wrapper/PVH-GKInstall.ps1` | Modify | Add sections 6a (stop services), 6b (kill POS), 6c (backup), 9 (rollback). Update synopsis/examples. Wrap GKInstall call in try/catch. |

---

### Task 1: Update script synopsis and add new variables

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1:1-48` (synopsis block) and after line 166 (end of section 6)

- [ ] **Step 1: Update the synopsis comment block to document backup/rollback behavior**

Replace the `.DESCRIPTION` and add a new `.EXAMPLE` in the comment block at the top of the file (lines 1-24):

```powershell
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
```

- [ ] **Step 2: Add `-SkipBackup` parameter to the param block**

Add after line 47 (`[string]$HostnameOverride`):

```powershell
    [switch]$SkipBackup           # Skip backup/rollback mechanism
```

- [ ] **Step 3: Add backup/rollback variable declarations and early GKInstall.ps1 check after section 6 (after line 166)**

Insert after the closing `Write-Host ""` of section 6 (line 166). Note: the `GKInstall.ps1` existence check is moved here (before sections 6a/6b/6c) so we fail early without stopping services or creating backups unnecessarily:

```powershell
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
```

- [ ] **Step 4: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): add backup/rollback variables and update synopsis"
```

---

### Task 2: Add section 6a — Stop services

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1` (insert after the variable declarations from Task 1)

- [ ] **Step 1: Add section 6a — stop service logic**

Insert immediately after the variable declarations block from Task 1:

```powershell
# ============================================================
# 6a. STOP SERVICE (SMInfoServer on TILL01, SMInfoClient on others)
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
                $svc.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
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
```

- [ ] **Step 2: Verify script syntax**

Run: `powershell -NoProfile -Command "& { $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content 'pvh_wrapper/PVH-GKInstall.ps1' -Raw), [ref]$null) ; Write-Host 'Syntax OK' }"`

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): add section 6a — stop SMInfoServer/SMInfoClient service"
```

---

### Task 3: Add section 6b — Kill POS process on port 3333

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1` (insert after section 6a)

- [ ] **Step 1: Add section 6b — kill POS process logic**

Insert immediately after section 6a:

```powershell
# ============================================================
# 6b. KILL POS PROCESS (Java on port 3333)
# ============================================================
if (-not $SkipBackup) {
    $pids = Get-NetTCPConnection -LocalPort 3333 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    if ($pids) {
        if ($WhatIfPreference) {
            Write-Host "[PVH] DRY RUN - Would kill process(es) on port 3333: PID(s) $($pids -join ', ')" -ForegroundColor Yellow
        } else {
            foreach ($p in $pids) {
                Write-Host "[PVH] Killing process on port 3333 (PID: $p)..." -ForegroundColor Yellow
                Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            }
            Write-Host "[PVH] POS process(es) on port 3333 killed." -ForegroundColor Green
        }
    } else {
        Write-Host "[PVH] No process listening on port 3333 - skipping POS kill." -ForegroundColor Gray
    }
}
```

- [ ] **Step 2: Verify script syntax**

Run: `powershell -NoProfile -Command "& { $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content 'pvh_wrapper/PVH-GKInstall.ps1' -Raw), [ref]$null) ; Write-Host 'Syntax OK' }"`

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): add section 6b — kill POS process on port 3333"
```

---

### Task 4: Add section 6c — Backup via rename

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1` (insert after section 6b)

- [ ] **Step 1: Add section 6c — backup logic**

Insert immediately after section 6b:

```powershell
# ============================================================
# 6c. BACKUP C:\gkretail -> C:\gkretail_migration_backup
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
                Remove-Item -Path $backupDest -Recurse -Force -ErrorAction SilentlyContinue
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
```

- [ ] **Step 2: Verify script syntax**

Run: `powershell -NoProfile -Command "& { $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content 'pvh_wrapper/PVH-GKInstall.ps1' -Raw), [ref]$null) ; Write-Host 'Syntax OK' }"`

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): add section 6c — backup C:\gkretail via rename"
```

---

### Task 5: Wrap GKInstall execution in try/catch and add section 9 — rollback

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1` (section 8 — execute GKInstall, and add section 9)

- [ ] **Step 1: Replace the GKInstall execution and exit code handling**

Replace lines 217-229 of the original script — specifically from `Write-Host "[PVH] Calling GKInstall.ps1..."` through `exit $exitCode` at the end of the file. The `$gkInstallPath` assignment and the `Test-Path` check (lines 199-215) have been **moved to Task 1 Step 3** (early check before backup), so also **remove** the now-redundant `$gkInstallPath = Join-Path ...` and `if (-not (Test-Path $gkInstallPath))` block from section 8. The WhatIf block (lines 203-209) stays — it will be updated in Task 6.

Replace with:

```powershell
Write-Host "[PVH] Calling GKInstall.ps1..."
Write-Host "[PVH] Command: GKInstall.ps1 $argsDisplay"
Write-Host ""

$gkInstallFailed = $false
$exitCode = 0

try {
    & $gkInstallPath @gkInstallArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $gkInstallFailed = $true
    }
} catch {
    Write-Host ""
    Write-Host "[PVH] GKInstall.ps1 threw an exception: $($_.Exception.Message)" -ForegroundColor Red
    $gkInstallFailed = $true
    $exitCode = 1
}

# ============================================================
# 9. CHECK RESULT & ROLLBACK IF NEEDED
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
                $svc.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
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
```

- [ ] **Step 2: Verify script syntax**

Run: `powershell -NoProfile -Command "& { $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content 'pvh_wrapper/PVH-GKInstall.ps1' -Raw), [ref]$null) ; Write-Host 'Syntax OK' }"`

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): add try/catch GKInstall execution and section 9 — automatic rollback"
```

---

### Task 6: Update WhatIf dry-run output to include new sections

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1` (section 8 WhatIf block)

- [ ] **Step 1: Update the WhatIf block in section 8 to include backup/rollback summary**

The existing WhatIf block (currently around section 8) should be updated to also display:

```powershell
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
```

- [ ] **Step 2: Verify script syntax**

Run: `powershell -NoProfile -Command "& { $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content 'pvh_wrapper/PVH-GKInstall.ps1' -Raw), [ref]$null) ; Write-Host 'Syntax OK' }"`

Expected: `Syntax OK`

- [ ] **Step 3: Test dry-run output**

Run: `powershell -NoProfile -File pvh_wrapper/PVH-GKInstall.ps1 -HostnameOverride "DE-A319TILL01" -WhatIf`

Expected output should include:
- `[PVH] DRY RUN - Would stop service: SMInfoClient`
- `[PVH] DRY RUN - Would backup C:\gkretail -> C:\gkretail_migration_backup`
- `[PVH] DRY RUN - Would execute: ...GKInstall.ps1 ...`
- `[PVH] DRY RUN - On failure, would rollback: ...`

(Note: dry-run test will need a mapping file with A319 entry to get past section 4)

- [ ] **Step 4: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): update WhatIf output to include backup/rollback plan"
```

---

### Task 7: Final review and integration test

**Files:**
- Review: `pvh_wrapper/PVH-GKInstall.ps1` (full file)

- [ ] **Step 1: Read the complete script end-to-end to verify flow**

Verify:
1. Synopsis is accurate
2. Variables are declared before use
3. Sections flow: 1→2→3→4→5→6→vars(+GKInstall check)→6a→6b→6c→7→8→9
4. WhatIf checks are in sections 6a, 6b, 6c, and section 8
5. `$backupCreated` is only set to `$true` after successful rename
6. Rollback only triggers when `$gkInstallFailed -and $backupCreated`
7. `-SkipBackup` bypasses sections 6a, 6b, 6c

- [ ] **Step 2: Verify script parses cleanly**

Run: `powershell -NoProfile -Command "& { $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content 'pvh_wrapper/PVH-GKInstall.ps1' -Raw), [ref]$null) ; Write-Host 'Syntax OK' }"`

Expected: `Syntax OK`

- [ ] **Step 3: Run dry-run with TILL01 hostname (should target SMInfoServer)**

Run: `powershell -NoProfile -File pvh_wrapper/PVH-GKInstall.ps1 -HostnameOverride "DE-A319TILL01" -WhatIf`

Verify output mentions `SMInfoServer`

- [ ] **Step 4: Run dry-run with TILL02 hostname (should target SMInfoClient)**

Run: `powershell -NoProfile -File pvh_wrapper/PVH-GKInstall.ps1 -HostnameOverride "DE-A319TILL02" -WhatIf`

Verify output mentions `SMInfoClient`

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "feat(pvh): finalize backup/rollback implementation"
```
