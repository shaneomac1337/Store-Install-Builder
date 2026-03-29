# Design: --removeOverrides / --keepOverrides CLI Flags

**Date:** 2026-03-29
**Status:** Approved
**Requested by:** End user who needs runtime control over override file cleanup

## Problem

The "remove overrides after install" setting is currently baked into generated scripts at generation time via the GUI checkbox. Users who generate scripts with removal OFF cannot later decide at runtime to clean up override files after a specific installation run — and vice versa. This forces regeneration of scripts just to change cleanup behavior.

**User scenario:** A user runs `--skipCheckAlive` for initial install, then wants to run the installer the "standard product way" on subsequent runs. They need to remove the override files that persist from the first run, without regenerating the scripts.

## Solution

Add two mutually exclusive CLI switch parameters to the generated GKInstall scripts:

- `--removeOverrides` — force removal of override files after installation completes
- `--keepOverrides` — force keeping override files after installation completes

These override the baked-in `@REMOVE_OVERRIDES_AFTER_INSTALL@` value at runtime.

## Priority Logic

```
CLI flag (--removeOverrides / --keepOverrides)   ← highest priority
    ↓ (if neither flag set)
Baked-in GUI config (@REMOVE_OVERRIDES_AFTER_INSTALL@)  ← fallback
```

## Behavior Matrix

| GUI Config (baked-in) | CLI Flag            | Result                          |
|-----------------------|---------------------|---------------------------------|
| Remove = OFF          | `--removeOverrides` | Overrides REMOVED after install |
| Remove = ON           | `--keepOverrides`   | Overrides KEPT after install    |
| Remove = OFF          | *(none)*            | Overrides KEPT (GUI default)    |
| Remove = ON           | *(none)*            | Overrides REMOVED (GUI default) |
| *Any*                 | Both flags          | Error message, script exits     |

## Scope of Changes

### Templates (modified)

**`gk_install_builder/templates/GKInstall.ps1.template`:**
1. Add `[switch]$removeOverrides` and `[switch]$keepOverrides` parameter declarations
2. Add conflict check — if both flags are set, print error and exit
3. In the cleanup section, apply CLI flag override to `$removeOverridesAfterInstall` before the existing removal logic runs

**`gk_install_builder/templates/GKInstall.sh.template`:**
1. Add `cli_remove_overrides=false` and `cli_keep_overrides=false` variable declarations
2. Add `--removeOverrides` and `--keepOverrides` to the argument parsing case block
3. Add conflict check — if both flags are set, print error and exit
4. In the cleanup section, apply CLI flag override to `remove_overrides_after_install` before the existing removal logic runs

### Tests (modified)

**`tests/unit/test_installer_overrides.py`:**
- Test that `--removeOverrides` flag declaration is present in generated scripts
- Test that `--keepOverrides` flag declaration is present in generated scripts

### No changes needed

- **Generator code** (`gk_install_generator.py`, `helper_file_generator.py`) — the `@REMOVE_OVERRIDES_AFTER_INSTALL@` token substitution already exists and is unaffected
- **Config** (`config.py`) — no new config keys needed; this is purely a runtime CLI feature
- **GUI** (`main.py`) — no UI changes needed

## Implementation Details

### PowerShell (GKInstall.ps1.template)

Parameter declaration (alongside existing params):
```powershell
[switch]$removeOverrides,
[switch]$keepOverrides
```

Conflict check (near other CLI validation):
```powershell
if ($removeOverrides -and $keepOverrides) {
    Write-Host "ERROR: --removeOverrides and --keepOverrides are mutually exclusive." -ForegroundColor Red
    exit 1
}
```

Override logic (before existing cleanup block):
```powershell
if ($removeOverrides) {
    $removeOverridesAfterInstall = "true"
}
if ($keepOverrides) {
    $removeOverridesAfterInstall = "false"
}
```

### Bash (GKInstall.sh.template)

Variable declarations:
```bash
cli_remove_overrides=false
cli_keep_overrides=false
```

Argument parsing (in the existing case block):
```bash
--removeOverrides) cli_remove_overrides=true ;;
--keepOverrides) cli_keep_overrides=true ;;
```

Conflict check:
```bash
if [ "$cli_remove_overrides" = "true" ] && [ "$cli_keep_overrides" = "true" ]; then
    echo "ERROR: --removeOverrides and --keepOverrides are mutually exclusive."
    exit 1
fi
```

Override logic (before existing cleanup block):
```bash
if [ "$cli_remove_overrides" = "true" ]; then
    remove_overrides_after_install="true"
fi
if [ "$cli_keep_overrides" = "true" ]; then
    remove_overrides_after_install="false"
fi
```

## Testing Strategy

1. Verify parameter declarations appear in generated scripts for both platforms
2. Manual testing: generate scripts and run with `--removeOverrides` / `--keepOverrides` to verify behavior
3. Existing override tests remain unchanged — no regression risk

## Risk Assessment

**Low risk.** The change is isolated to template files only. The override logic piggybacks on the existing `$removeOverridesAfterInstall` / `remove_overrides_after_install` variable that already controls cleanup behavior. No new code paths — just a variable reassignment before the existing logic runs.
