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
   - Copy-Item -Recurse C:\gkretail -> C:\gkretail_migration_backup

4. Run GKInstall.ps1 (existing wrapper logic)

5. Check GKInstall exit code
   5a. SUCCESS (exit code 0): Done. Backup stays at C:\gkretail_migration_backup.
   5b. FAILURE (non-zero exit code): Execute rollback (step 6)

6. Rollback (only if backup was created in step 3)
   - Remove failed C:\gkretail
   - Copy C:\gkretail_migration_backup -> C:\gkretail
   - Restart the service stopped in step 1 (SMInfoServer or SMInfoClient)
   - Launch C:\gkretail\pos-full\run_tpos_PVH.cmd
   - Exit with GKInstall's original error code
```

### Service Detection Logic

| Condition | Service to stop/restart |
|-----------|------------------------|
| `tillNumber -eq 1` | `SMInfoServer` |
| `tillNumber -ne 1` | `SMInfoClient` |

- Use `Stop-Service -Name <name> -Force -ErrorAction SilentlyContinue`
- Use `Get-Service -Name <name> -ErrorAction SilentlyContinue` to check existence before logging
- On rollback: `Start-Service -Name <name> -ErrorAction SilentlyContinue`

### POS Process Kill Logic

```powershell
$conn = Get-NetTCPConnection -LocalPort 3333 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
}
```

### Backup Behavior

- **Source**: `C:\gkretail`
- **Destination**: `C:\gkretail_migration_backup`
- If source does not exist: log `[PVH] No existing installation found at C:\gkretail - skipping backup` and proceed. Set a flag (`$backupCreated = $false`) so rollback is skipped on failure.
- If destination already exists: remove it before copying (each run gets a fresh backup of the current state)
- Copy is a full recursive copy of the entire directory

### Rollback Behavior

Only executes if:
- GKInstall exited with non-zero code, AND
- A backup was actually created (`$backupCreated -eq $true`)

Steps:
1. `Remove-Item -Recurse -Force C:\gkretail`
2. `Copy-Item -Recurse C:\gkretail_migration_backup C:\gkretail`
3. `Start-Service` the appropriate service (SMInfoServer or SMInfoClient)
4. `Start-Process C:\gkretail\pos-full\run_tpos_PVH.cmd`

If no backup was created (source didn't exist), rollback logs a message and skips restore.

### WhatIf / DryRun Support

The existing `-WhatIf` flag will display what would happen at each step without executing:
- Which service would be stopped
- Whether POS process on port 3333 would be killed
- Whether backup would be created (and whether source exists)
- The GKInstall command that would run

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

### Error Handling

- Service stop failures: logged as warnings, do not block execution
- POS kill failures: logged as warnings, do not block execution
- Backup copy failure: logged as error, exits (do not run GKInstall without a backup if the source existed)
- Rollback failures: logged as errors with guidance to manually restore from `C:\gkretail_migration_backup`

### Out of Scope

- Linux (`PVH-GKInstall.sh`) — not needed per requirements
- Automatic backup cleanup — backup persists indefinitely
- Timestamped/multiple backups — single backup at fixed path, overwritten each run
