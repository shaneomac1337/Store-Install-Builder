# Update-mode RCS detection for wait message

**Date**: 2026-05-14
**Status**: Approved (pending user review)

## Problem

During update mode (`$isUpdate=true`), the GKInstall script's "Waiting for installer log file to be created..." progress message shows "Downloading installation files from \<base_url\> DSG" even when the underlying installation will actually pull packages from an RCS instance. The installer determines RCS usage automatically based on `rcs.url` in `station.properties`, but the wait message ignores that signal and only switches to "Downloading from RCS" when the user explicitly passes `--rcsUrl` on the command line.

Operators watching the log are misled: the message says DSG, but the installer is actually using RCS.

This change makes the wait message reflect reality during update mode by parsing `rcs.url` from `station.properties` and showing the RCS URL in the progress message.

## Constraints

- Cosmetic / log-message change only. No side effects on:
  - `$rcsUrl` script variable (NOT auto-set from station.properties)
  - `installationtoken.txt` (NO `rcs.url=` line auto-appended)
  - onboarding token request body (NOT auto-injected — onboarding is skipped in update mode anyway)
- CLI `--rcsUrl` continues to take precedence over the station.properties value
- Cross-platform: both PowerShell and Bash
- Reuses already-loaded `station.properties` content (no duplicate I/O)
- Java property escaping (`\:` → `:`, `\=` → `=`) handled the same way the existing `configServiceUrl` extraction handles it

## Design

### Architecture

Single in-memory parse of `station.properties` in the existing update-mode block populates a new local variable (`$stationRcsUrl` / `station_rcs_url`). The wait-message logic adds an `elseif` branch that uses this variable when CLI `$rcsUrl` is not set.

### Extraction

Added in the existing update-mode parse block (PowerShell around line 1107; Bash equivalent), alongside the current extractions for `storeId`, `workstationId`, and `configServiceUrl`. The `station.properties` file is already loaded into `$stationPropertiesContent` (PowerShell) / `station_properties_content` (Bash) at that point.

**PowerShell:**
```powershell
if ($stationPropertiesContent -match 'rcs\.url=([^\r\n]+)') {
    $stationRcsUrl = $matches[1].Trim() -replace '\\:', ':' -replace '\\=', '='
    Write-Host "Found RCS URL in station.properties: $stationRcsUrl"
}
```

**Bash:**
```bash
station_rcs_url=$(echo "$station_properties_content" | grep '^rcs\.url=' | sed 's/^rcs\.url=//;s/\\:/:/g;s/\\=/=/g' | tr -d '\r')
if [ -n "$station_rcs_url" ]; then
  echo "Found RCS URL in station.properties: $station_rcs_url"
fi
```

### Wait message logic

Update the existing `if (-not $offline.IsPresent)` block (PS1 line ~2655) and the equivalent Bash branch (line ~3109). Precedence:

1. `$rcsUrl` CLI set and not the literal `"autodetect"` → show RCS with `$rcsUrl`
2. Else `$stationRcsUrl` non-empty → show RCS with `$stationRcsUrl`
3. Else → show DSG (current default)

**PowerShell:**
```powershell
$waitMessage = if (-not $offline.IsPresent) {
    if ($rcsUrl -and $rcsUrl -ne "autodetect") {
        "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from RCS ($rcsUrl)"
    } elseif ($stationRcsUrl) {
        "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from RCS ($stationRcsUrl)"
    } else {
        "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from $base_url DSG"
    }
} else {
    "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed)"
}
```

**Bash:**
```bash
if [ "$offline_mode" = false ]; then
  if [ -n "$rcs_url" ] && [ "$rcs_url" != "autodetect" ]; then
    echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from RCS ($rcs_url)"
  elif [ -n "$station_rcs_url" ]; then
    echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from RCS ($station_rcs_url)"
  else
    echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from $base_url DSG"
  fi
else
  echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed)"
fi
```

### Variable scope

PowerShell and Bash scripts use single-script scope. `$stationRcsUrl` / `station_rcs_url` set in the update-mode parse block (line ~1107) is visible at the wait-message logic (line ~2655). Same pattern already used by `$storeNumber`, `$workstationId`, and `$configServiceUrl`.

## Data flow

| Step | Source | Output |
|------|--------|--------|
| 1. Update mode detected | `$install_dir/station.properties` exists | `$isUpdate=true` |
| 2. Read station.properties | Filesystem | `$stationPropertiesContent` |
| 3. Extract rcs.url | regex match on content | `$stationRcsUrl` (empty if no match) |
| 4. Compose wait message | `$rcsUrl`, `$stationRcsUrl`, `$base_url`, offline flag | log line |

## Error handling

- **`rcs.url` not in station.properties** → match fails → `$stationRcsUrl` stays empty/`$null` → wait message falls through to DSG (current behavior preserved)
- **Malformed line** (e.g., `rcs.url=` with no value) → `$matches[1]` is empty → `$stationRcsUrl` empty after Trim → falls through to DSG
- **Java-escape decode fails** → operates on whatever the regex captured; worst case the URL displays with literal `\:` which is still informative

## Testing

Add `TestUpdateModeRcsDetection` class in `tests/unit/test_rcs_afteronboarding.py` (or new file `tests/unit/test_update_mode_rcs_detection.py`):

| Test | Expectation |
|------|-------------|
| Generated PS1 contains `'rcs\.url=([^\r\n]+)'` regex extraction | Pattern present in update-mode parse block |
| Generated PS1 contains `elseif ($stationRcsUrl)` branch | Wait message has the new branch |
| Generated PS1 contains unescape `-replace '\\:', ':'` for station rcs.url | Matches `configServiceUrl` pattern |
| Generated SH contains `station_rcs_url=$(...grep '^rcs\.url='...)` | Extraction present |
| Generated SH contains `elif [ -n "$station_rcs_url" ]` branch | Wait message has the new branch |
| Order check: extraction appears BEFORE wait-message section | Variable in scope when used |

All assertions on generated script content (existing test pattern in this codebase).

## Files Changed

1. `gk_install_builder/templates/GKInstall.ps1.template` — add ~5 lines in update-mode parse block; add `elseif` branch (~3 lines) in wait-message block
2. `gk_install_builder/templates/GKInstall.sh.template` — mirror for bash
3. `tests/unit/test_rcs_afteronboarding.py` — add `TestUpdateModeRcsDetection` class with ~6 assertions

Total: ~15 lines of production code per platform + ~50 lines of tests.

## Out of scope

- No change to `installationtoken.txt` append logic
- No auto-set of `$rcsUrl` from station.properties
- No change to onboarding flow
- No change to autodetect behavior on fresh install
- No new CLI parameters

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Regex extraction captures trailing whitespace or comment | Low | `.Trim()` / `tr -d '\r'` strips; `[^\r\n]+` excludes newlines |
| Variable name collision with `$rcsUrl` | Low | Distinct name (`$stationRcsUrl`) avoids shadowing |
| Bash `grep '^rcs\.url='` matches commented-out lines starting with `#rcs.url=` | Low | `^` anchor at line start excludes `# rcs.url=`; if hash is followed by no space (`#rcs.url=`), still excluded by leading `#` mismatch |
| Java unescape misses other escaped characters (`\\\\`, `\n`) | Low | Same limitation as existing configServiceUrl extraction; values in practice are URLs with only `\:` escaping |

## Open questions

None. Design complete pending user review.
