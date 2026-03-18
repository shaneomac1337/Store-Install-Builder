# PVH Wrapper: Backup & Rollback Feature

**Date**: 2026-03-18
**Scope**: `pvh_wrapper/PVH-GKInstall.ps1` (Windows only)
**Branch**: `feature/pvh-customization`

## Problem

When PVH stores migrate from FAT to ONEX-CLOUD via the PVH wrapper, a failed GKInstall run can leave the POS in a broken state with no way to recover. The wrapper needs to back up the existing installation before running GKInstall and automatically rollback if the install fails.

## Design

### Execution Flow

```
1. Stop services
   - TILL01 (tillNumber == 1): Stop SMInfoServer
   - All others: Stop SMInfoClient
   - Graceful: ignore if service not found or already stopped

2. Kill POS process
   - Find Java process listening on TCP port 3333
   - Stop-Process -Force on the owning PID
   - Ignore if nothing is listening on 3333

3. Backup C:\gkretail -> C:\gkretail_migration_backup
   - If C:\gkretail does NOT exist: log warning, skip backup, proceed to step 4
   - If C:\gkretail_migration_backup already exists: remove it first
   - If C:\gkretail_failed exists from a prior run: remove it first
   - Rename-Item C:\gkretail -> C:\gkretail_migration_backup (instant, same volume)
   - GKInstall will create a fresh C:\gkretail during installation

4. Run GKInstall.ps1 (existing wrapper logic)

5. Check GKInstall exit code
   5a. SUCCESS (exit code 0): Done. Backup stays at C:\gkretail_migration_backup.
   5b. FAILURE (non-zero exit code): Execute rollback (step 6)

6. Rollback (only if backup was created in step 3)
   - Rename failed C:\gkretail -> C:\gkretail_failed
   - Rename C:\gkretail_migration_backup -> C:\gkretail (instant, same volume)
   - Remove C:\gkretail_failed (best-effort)
   - Restart the service stopped in step 1 (SMInfoServer or SMInfoClient)
   - Launch C:\gkretail\pos-full\run_tpos_PVH.cmd (fire-and-forget, skip if file missing)
   - Exit with GKInstall's original error code
```

### Service Detection Logic

| Condition | Service to stop/restart |
|-----------|------------------------|
| `tillNumber -eq 1` | `SMInfoServer` |
| `tillNumber -ne 1` | `SMInfoClient` |

- Use `Stop-Service -Name <name> -Force -ErrorAction SilentlyContinue`
- Use `Get-Service -Name <name> -ErrorAction SilentlyContinue` to check existence before logging
- Timeout: wait up to 30 seconds for service to stop, then proceed regardless
- On rollback: `Start-Service -Name <name> -ErrorAction SilentlyContinue`

### POS Process Kill Logic

Kill all processes listening on port 3333 (handles child processes / multiple listeners):

```powershell
$pids = Get-NetTCPConnection -LocalPort 3333 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
foreach ($pid in $pids) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}
```

### Backup Behavior

- **Source**: `C:\gkretail`
- **Destination**: `C:\gkretail_migration_backup`
- If source does not exist: log `[PVH] No existing installation found at C:\gkretail - skipping backup` and proceed. Set a flag (`$backupCreated = $false`) so rollback is skipped on failure.
- If destination already exists: remove it before renaming (each run gets a fresh backup of the current state)
- If `C:\gkretail_failed` exists from a prior run: remove it (best-effort cleanup)
- Uses `Rename-Item` (not copy) — instant on same volume, avoids partial-copy risks and disk space issues. GKInstall creates a fresh `C:\gkretail` during installation so the original does not need to remain in place.
- **Assumption**: `C:\gkretail` is on the C: drive (not a junction/symlink to another volume). This is the standard PVH deployment.

### Rollback Behavior

Only executes if:
- GKInstall exited with non-zero code, AND
- A backup was actually created (`$backupCreated -eq $true`)

Steps:
1. Rename failed `C:\gkretail` to `C:\gkretail_failed` — if rename fails (locked files), log error with manual recovery instructions and exit
2. Rename `C:\gkretail_migration_backup` to `C:\gkretail` (instant on same volume)
3. Remove `C:\gkretail_failed` (best-effort, warn if it fails — will be cleaned up on next run)
4. `Start-Service` the appropriate service (SMInfoServer or SMInfoClient) — log warning if service does not reach Running state
5. Launch `C:\gkretail\pos-full\run_tpos_PVH.cmd` via `Start-Process` (fire-and-forget, skip with warning if file not found via `Test-Path`)

If no backup was created (source didn't exist), rollback logs a message and skips restore.

### WhatIf / DryRun Support

Each new section (6a, 6b, 6c) checks `$WhatIfPreference` independently and outputs what it would do without executing. Section 9 (rollback) never executes in WhatIf mode since GKInstall doesn't run.

Display includes:
- Which service would be stopped
- Whether POS process on port 3333 would be killed
- Whether backup would be created (and whether source exists)
- The GKInstall command that would run

### GKInstall Exit Code Capture

The wrapper uses `& $gkInstallPath @gkInstallArgs` which sets `$LASTEXITCODE` when GKInstall calls `exit N`. Additionally wrap the call in try/catch to handle terminating errors — treat thrown exceptions as failures (trigger rollback). Default exit code for exception path: `1`.

### Script Structure (insertion points in PVH-GKInstall.ps1)

New logic is inserted between the existing "DISPLAY SUMMARY" (section 6) and "BUILD GKINSTALL ARGUMENTS" (section 7):

```
Existing sections 1-6 (hostname parse, mapping lookup, summary display)
  NEW: Section 6a - Stop services
  NEW: Section 6b - Kill POS process
  NEW: Section 6c - Backup
Existing sections 7-8 (build args, execute GKInstall)
  NEW: Section 9 - Check result & rollback if needed
```

### Variables Added

| Variable | Type | Purpose |
|----------|------|---------|
| `$serviceName` | string | Service to stop/restart (`SMInfoServer` or `SMInfoClient`) |
| `$backupCreated` | bool | Whether backup was actually created (controls rollback) |
| `$backupSource` | string | `C:\gkretail` |
| `$backupDest` | string | `C:\gkretail_migration_backup` |
| `$backupFailed` | string | `C:\gkretail_failed` (temp name during rollback) |

### Error Handling

- Service stop failures: logged as warnings, do not block execution
- POS kill failures: logged as warnings, do not block execution
- Backup copy failure: logged as error, exits (do not run GKInstall without a backup if the source existed)
- Rollback failures: logged as errors with guidance to manually restore from `C:\gkretail_migration_backup`

### Out of Scope

- Linux (`PVH-GKInstall.sh`) — not needed per requirements
- Automatic backup cleanup — backup persists indefinitely
- Timestamped/multiple backups — single backup at fixed path, overwritten each run
- Transcript/file logging — console output only
- Re-entrancy safety (detecting corrupted `C:\gkretail` before overwriting a good backup) — operator responsibility
