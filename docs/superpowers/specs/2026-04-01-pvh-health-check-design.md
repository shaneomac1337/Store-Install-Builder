# PVH Post-Install Health Check

**Date**: 2026-04-01
**Scope**: `pvh_wrapper/PVH-GKInstall.ps1` (primary), `pvh_wrapper/PVH-GKInstall.sh` (secondary)

## Problem

GKInstall can exit with code 0 but leave the system in a broken state — missing files, application not running. The wrapper currently only triggers rollback on non-zero exit codes. We need a post-install health check that verifies the installation actually works, and rolls back if it doesn't.

## Design

### Configuration

New variables at the top of each wrapper, grouped with existing configurable settings:

**PowerShell:**
```powershell
$enableHealthCheck  = $true    # Set to $false to skip health checks
$healthCheckTimeout = 600      # Max wait for port check (seconds)
$healthCheckInterval = 30      # Poll interval for port check (seconds)
```

**Bash:**
```bash
ENABLE_HEALTH_CHECK=true
HEALTH_CHECK_TIMEOUT=600
HEALTH_CHECK_INTERVAL=30
```

New CLI parameter: `-SkipHealthCheck` (PS1 switch) / `--skip-health-check` (bash flag) to override at runtime.

### Health Check Sequence (Approach A — fail fast on filesystem, poll for port)

After GKInstall exits 0, if health check is enabled:

1. **Check 1 — Folder exists**: `C:\gkretail\onex` (immediate, no polling)
2. **Check 2 — Key file exists**: `C:\gkretail\onex\station.properties` (immediate, no polling)
3. **Check 3 — Java on port 3333**: Poll every 30s for up to 10 minutes (20 attempts). Verify both that port 3333 has a listener AND that the owning process is Java.

If check 1 or 2 fails, skip remaining checks — go straight to rollback.
If check 3 times out, trigger rollback.
If all pass, proceed to normal success exit.

### Rollback Integration

On health check failure, set `$gkInstallFailed = $true` and let the existing rollback logic handle it. No code duplication — the health check section just sets the failure flag with a descriptive message.

### Port + Java Verification

**PowerShell:**
```powershell
$conn = Get-NetTCPConnection -LocalPort 3333 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc.ProcessName -like "*java*") { # pass }
}
```

**Bash:**
```bash
pid=$(ss -tlnp sport = :3333 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
if [ -n "$pid" ]; then
    comm=$(cat /proc/$pid/comm 2>/dev/null)
    [[ "$comm" == "java" ]] && # pass
fi
```

### Display Output

```
[PVH] === Post-Install Health Check ===
[PVH] [1/3] Checking C:\gkretail\onex exists... OK
[PVH] [2/3] Checking C:\gkretail\onex\station.properties exists... OK
[PVH] [3/3] Waiting for Java process on port 3333 (timeout: 10m)...
[PVH]        Attempt 1/20 (0:30 elapsed)... not yet
[PVH]        Attempt 2/20 (1:00 elapsed)... not yet
[PVH]        Attempt 3/20 (1:30 elapsed)... Java process detected on port 3333. OK
[PVH] === Health Check PASSED ===
```

On failure:
```
[PVH] === Post-Install Health Check ===
[PVH] [1/3] Checking C:\gkretail\onex exists... FAILED
[PVH] === Health Check FAILED — triggering rollback ===
```

### Dry-Run Support

`-WhatIf` / `--dry-run` displays what health checks would be performed without executing them, consistent with existing dry-run behavior.

### Files Modified

- `pvh_wrapper/PVH-GKInstall.ps1` — primary implementation
- `pvh_wrapper/PVH-GKInstall.sh` — secondary implementation (same logic)
