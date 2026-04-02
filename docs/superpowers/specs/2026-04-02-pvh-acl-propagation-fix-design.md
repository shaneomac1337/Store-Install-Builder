# PVH ACL Propagation Delay Fix

**Date:** 2026-04-02
**Status:** Approved
**Scope:** `pvh_wrapper/PVH-GKInstall.ps1` only

## Problem

After `icacls` grants Everyone full control recursively on `C:\gkretail` (section 4d, line 312), the `Rename-Item` in section 4e (line 355) fires immediately and intermittently hits "Access Denied" because Windows hasn't finished propagating the ACL changes across the directory tree. A manual re-run always succeeds because the ACLs have had time to take effect.

## Solution

**Approach A: Fixed sleep + 3 retries**

1. After icacls completes in section 4d, add a 10-second sleep to let ACLs propagate.
2. Wrap the `Rename-Item` in section 4e in a retry loop: 3 attempts with 10s between each.
3. If all 3 retries exhaust, abort with the existing error message (no behavior change on permanent failure).

## What Changes

- **Section 4d (after line 312):** Add `Start-Sleep -Seconds 10` with a log message after icacls grants permissions.
- **Section 4e (line 354-358):** Replace the single `Rename-Item` try/catch with a retry loop (3 attempts, 10s sleep between failures).

## What Does NOT Change

- Rollback renames (section 9) -- no issue reported there.
- `Remove-Item` of previous backup (line 344) -- user confirmed no previous backup scenario.
- Bash wrapper (`PVH-GKInstall.sh`) -- not affected.
- No new configurable variables -- hardcoded 10s sleep and 3 retries.

## Expected Log Output

### Happy path (no retry needed)

```
[PVH] Granted full control on C:\gkretail
[PVH] Waiting 10s for permission changes to propagate...
[PVH] Backing up C:\gkretail -> C:\gkretail_migration_backup...
[PVH] Backup complete.
```

### Retry path

```
[PVH] Granted full control on C:\gkretail
[PVH] Waiting 10s for permission changes to propagate...
[PVH] Backing up C:\gkretail -> C:\gkretail_migration_backup...
[PVH] WARNING: Backup rename failed (attempt 1/3): Access is denied.
[PVH]          Retrying in 10s...
[PVH] Backing up C:\gkretail -> C:\gkretail_migration_backup... (attempt 2/3)
[PVH] Backup complete.
```

### All retries exhausted (same as current behavior)

```
[PVH] WARNING: Backup rename failed (attempt 3/3): Access is denied.
[PVH] ERROR: Failed to backup C:\gkretail after 3 attempts.
[PVH]        Cannot proceed without backup. Aborting.
```

## Timing Budget

- Initial sleep: 10s (always)
- Max retry wait: 3 x 10s = 30s
- Total worst case: ~40s additional wait before abort
- Typical case: 10s initial sleep, rename succeeds on first attempt
