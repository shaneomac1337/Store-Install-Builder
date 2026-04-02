# PVH ACL Propagation Delay Fix - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent "Access Denied" on backup rename by waiting for ACL propagation after icacls and retrying on failure.

**Architecture:** Add a 10s sleep after icacls in section 4d, then replace the single Rename-Item try/catch in section 4e with a 3-attempt retry loop with 10s between retries.

**Tech Stack:** PowerShell

---

## File Structure

- Modify: `pvh_wrapper/PVH-GKInstall.ps1:312-363` (sections 4d and 4e)

No new files. No test files (this is a deployment wrapper script, not unit-testable).

---

### Task 1: Add ACL propagation sleep after icacls

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1:312-313`

- [ ] **Step 1: Add 10s sleep after icacls completes**

After line 313 (`Write-Host "[PVH] Granted full control on $backupSource"`), insert:

```powershell
                # Wait for ACL changes to propagate across the directory tree
                Write-Host "[PVH] Waiting 10s for permission changes to propagate..." -ForegroundColor Gray
                Start-Sleep -Seconds 10
```

This goes inside the existing `try` block, right after the "Granted full control" message on line 313, before the closing `} catch {` on line 314.

- [ ] **Step 2: Verify dry-run still works**

Run: `powershell -File pvh_wrapper/PVH-GKInstall.ps1 -HostnameOverride "A319TILL01" -WhatIf`

Expected: Dry-run output shows the same as before (sleep is inside the `else` branch, not the WhatIf branch). No errors.

- [ ] **Step 3: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "fix(pvh): add 10s sleep after icacls for ACL propagation"
```

---

### Task 2: Replace backup rename with 3-attempt retry loop

**Files:**
- Modify: `pvh_wrapper/PVH-GKInstall.ps1:353-363`

- [ ] **Step 1: Replace the single Rename-Item try/catch with a retry loop**

Replace lines 353-363 (the current backup rename block):

```powershell
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
```

With this retry loop:

```powershell
            $backupMaxRetries = 3
            $backupRetryDelay = 10
            $backupSucceeded  = $false

            for ($attempt = 1; $attempt -le $backupMaxRetries; $attempt++) {
                if ($attempt -eq 1) {
                    Write-Host "[PVH] Backing up $backupSource -> $backupDest..." -ForegroundColor Yellow
                } else {
                    Write-Host "[PVH] Backing up $backupSource -> $backupDest... (attempt $attempt/$backupMaxRetries)" -ForegroundColor Yellow
                }
                try {
                    Rename-Item -Path $backupSource -NewName (Split-Path $backupDest -Leaf) -ErrorAction Stop
                    $backupCreated  = $true
                    $backupSucceeded = $true
                    Write-Host "[PVH] Backup complete." -ForegroundColor Green
                    break
                } catch {
                    if ($attempt -lt $backupMaxRetries) {
                        Write-Host "[PVH] WARNING: Backup rename failed (attempt $attempt/$backupMaxRetries): $($_.Exception.Message)" -ForegroundColor Yellow
                        Write-Host "[PVH]          Retrying in ${backupRetryDelay}s..." -ForegroundColor Yellow
                        Start-Sleep -Seconds $backupRetryDelay
                    } else {
                        Write-Host "[PVH] ERROR: Failed to backup $backupSource after $backupMaxRetries attempts." -ForegroundColor Red
                        Write-Host "[PVH]        Error: $($_.Exception.Message)" -ForegroundColor Red
                        Write-Host "[PVH]        Cannot proceed without backup. Aborting." -ForegroundColor Red
                        exit 1
                    }
                }
            }
```

- [ ] **Step 2: Verify dry-run still works**

Run: `powershell -File pvh_wrapper/PVH-GKInstall.ps1 -HostnameOverride "A319TILL01" -WhatIf`

Expected: Same dry-run output as before. The retry loop is inside the `else` branch (not WhatIf).

- [ ] **Step 3: Commit**

```bash
git add pvh_wrapper/PVH-GKInstall.ps1
git commit -m "fix(pvh): add 3-attempt retry loop for backup rename after ACL change"
```
