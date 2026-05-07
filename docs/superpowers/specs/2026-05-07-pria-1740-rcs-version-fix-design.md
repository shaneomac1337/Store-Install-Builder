# PRIA-1740 — RCS Default Version Cannot Be Retrieved

**Ticket**: [PRIA-1740](https://jira.gk-software.com/browse/PRIA-1740)
**Reporter**: Soeren Mothes
**Date**: 2026-05-07
**Status**: Design approved

## Problem

Generated `GKInstall.ps1` retrieves only the literal character `v` instead of the full version string (e.g., `v2.1.10`) when the Config-Service returns a single-element `versionNameList`. The RCS-SERVICE component is the most exposed because it typically publishes only one version. The bug breaks installation: downstream API calls and DSG download URLs use `v` as the version, producing 404 errors such as:

```
{"message":"System type version 'v' for system 'GKR-Resource-Cache-Service' does not exist."}
```

## Evidence

From the user-supplied `GKInstall_RCS_20260506_121726.log`:

```
DEBUG: Raw response for RCS-SERVICE: @{versionNameList=System.Object[]}
DEBUG: versionNameList: v2.1.10
DEBUG: versionNameList type: System.Object[]
DEBUG: versionNameList Count: 1
Found RCS-SERVICE: v (available: 1 versions)
```

The API response contains the full version `v2.1.10`, but the parsed `$latestVersion` is `v`.

## Root Cause

`gk_install_builder/templates/GKInstall.ps1.template:938`:

```powershell
$latestVersion = ($response.versionNameList | Sort-Object { [System.Version]($_ -replace '^v','') } -Descending)[0]
```

PowerShell pipeline behavior:

1. `$response.versionNameList` is `System.Object[]` of length 1 containing `"v2.1.10"`.
2. The `Sort-Object` pipeline emits one object.
3. PowerShell unwraps single-element pipeline output to a scalar `string`.
4. `(scalar_string)[0]` indexes the string, returning `[char]'v'` (first character).
5. `$latestVersion` becomes `'v'`, which propagates to all downstream URL/payload construction.

The `[System.Version]` sort-key cast itself is not the issue here — `2.1.10` casts cleanly. The bug is purely the scalar-unwrap-then-index pattern.

## Affected API Modes

Both Legacy (5.25, `/config-service/...`) and New (5.27+, `/api/config/...`) API versions are affected. The endpoint URL differs but the parsing code is identical, so the bug fires regardless of `api_version` config setting.

## Affected Platforms

- **Windows (PowerShell)**: affected. Bug confirmed in field.
- **Linux (Bash)**: not affected. `gk_install_builder/templates/GKInstall.sh.template:1218` uses `grep | tr | sort -V | head -1`, a line-based pipeline that handles n=1 correctly.

## Fix

**File**: `gk_install_builder/templates/GKInstall.ps1.template`
**Line**: 938

Replace the index-based selection with `Select-Object -First 1`:

```powershell
# Before
$latestVersion = ($response.versionNameList | Sort-Object { [System.Version]($_ -replace '^v','') } -Descending)[0]

# After
$latestVersion = $response.versionNameList |
    Sort-Object { [System.Version]($_ -replace '^v','') } -Descending |
    Select-Object -First 1
```

### Why this works

- `Select-Object -First 1` returns the actual collection element, not a string-character index.
- Behavior is correct for n=1 (returns the single version string) and n≥2 (returns highest-sorted version string).
- Idiomatic PowerShell. Avoids the scalar/array-unwrap trap entirely.

## Scope

- 1 file changed: `gk_install_builder/templates/GKInstall.ps1.template`
- ~3 lines of diff
- No generator (`generators/gk_install_generator.py`) changes required
- No template variable additions
- No bash template changes (verified safe)
- No `api_client.py` changes (Python-side already correct)

## Out of Scope

The following were considered and explicitly deferred:

- **Pre-release tag handling** (`-RC1`, `-SNAPSHOT`) — `[System.Version]` cast would throw on these, but RCS and similar single-version components do not publish such tags. No field reports. Defer until evidence surfaces.
- **Bash template parity work** — bash logic confirmed correct via inspection.
- **DEBUG-line additions** seen in user's log (lines 69–72) — those were added by the reporter while debugging and are not in current template. Could be added later as a separate observability improvement.

## Testing Plan

1. **Test suite**: run `pytest tests/`. Must stay at 187/187 passing — refactor invariant.
2. **Manual regeneration**: generate scripts via the GUI, inspect `GKInstall.ps1` line ~938, confirm new pattern is present.
3. **Synthetic verification** (PowerShell REPL):
   ```powershell
   $arr = @("v2.1.10")
   $arr | Sort-Object {...} -Descending | Select-Object -First 1
   # expected: v2.1.10
   ```
4. **Field verification**: reporter reruns RCS installer with regenerated script. Expected log line:
   ```
   Found RCS-SERVICE: v2.1.10 (available: 1 versions)
   ```
   Expected: no 404 from Config-Service / DSG.

## Risk

Near-zero.

- Idiomatic PowerShell pattern.
- Semantically equivalent to existing code for n≥2.
- Fixes n=1 case.
- No template variable surface area changes — generator does not need to know about this.

## Locations Referenced

- `gk_install_builder/templates/GKInstall.ps1.template:938` — fix site
- `gk_install_builder/templates/GKInstall.sh.template:1218` — bash equivalent (no change)
- `gk_install_builder/generators/gk_install_generator.py:208,230` — API endpoint URL mapping (no change)
- `gk_install_builder/integrations/api_client.py:610,613` — Python GUI test path (no change, already correct)
