# RCS-SERVICE FP/FPD Dispatch Fix

**Date**: 2026-05-07
**Status**: Design approved
**Related**: Reported verbally by Soeren Mothes alongside [PRIA-1740](https://jira.gk-software.com/browse/PRIA-1740)

## Problem

Generated installer scripts and the GUI API test silently fail to fetch the RCS-SERVICE version from the Employee Hub Service Function Pack API. RCS-SERVICE is included in the components list but has no property-name dispatch case in 5 of 6 parsing sites. The downstream code falls back to the hardcoded `@RCS_VERSION@` template variable, which is whatever the user happened to set in the GUI (often stale).

The reporter's symptom: RCS install with FP/FPD as the version source uses the hardcoded value rather than the live API value, with no clear error.

## Root Cause

Commit `2d34ba7` ("feat: add RCS (Resource Cache Service) component support") added RCS-SERVICE to the `$allComponents` array and the various component-mapping switches but never added the property-name dispatch (`RCS_Version` / `RCS_Update_Version`) to the FP and FPD parsers. The bug has existed since the RCS rollout.

## Coverage Audit

| Component | PS1 FP | PS1 FPD | SH FP | SH FPD | Py FP | Py FPD |
|---|---|---|---|---|---|---|
| POS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ONEX-POS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| WDM | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FLOW-SERVICE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LPA-SERVICE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| STOREHUB-SERVICE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **RCS-SERVICE** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

Only RCS-SERVICE is incomplete. Other components are fully covered.

## Property Names

The Employee Hub Service returns these properties for RCS (confirmed via `gk_install_builder/default_versions.json:283-296`):
- `RCS_Update_Version` — scope FPD, value e.g. `v2.0.3`
- `RCS_Version` — scope FPD, value e.g. `v2.0.5`

## Preference Order

`RCS_Version` preferred, `RCS_Update_Version` fallback. Rationale:
- Matches existing Python FP code at `api_client.py:294` which is the only RCS dispatch already in production.
- Matches the convention of the majority of components (ONEX, WDM, FlowService, LPA all prefer `_Version`).

## Fix

Add RCS-SERVICE handling to the 5 missing dispatch sites.

### Site 1: PS1 FP — `gk_install_builder/templates/GKInstall.ps1.template:702-765`

Add inside the FP `switch ($property.propertyId)` block:

```powershell
"RCS_Version" {
    $versions["RCS-SERVICE"] = $property.value
    $versionSources["RCS-SERVICE"] = "FP (Modified)"
}
"RCS_Update_Version" {
    if (-not $versions.ContainsKey("RCS-SERVICE")) {
        $versions["RCS-SERVICE"] = $property.value
        $versionSources["RCS-SERVICE"] = "FP (Modified)"
    }
}
```

### Site 2: PS1 FPD — `gk_install_builder/templates/GKInstall.ps1.template:788-861`

Add inside the FPD `switch` block (both branches guarded by `ContainsKey`):

```powershell
"RCS_Version" {
    if (-not $versions.ContainsKey("RCS-SERVICE")) {
        $versions["RCS-SERVICE"] = $property.value
        $versionSources["RCS-SERVICE"] = "FPD (Default)"
    }
}
"RCS_Update_Version" {
    if (-not $versions.ContainsKey("RCS-SERVICE")) {
        $versions["RCS-SERVICE"] = $property.value
        $versionSources["RCS-SERVICE"] = "FPD (Default)"
    }
}
```

### Site 3: SH FP — `gk_install_builder/templates/GKInstall.sh.template:1059-1096`

Add inside the FP `case "$COMPONENT_TYPE"` block:

```bash
"RCS-SERVICE")
    result_version=$(echo "$fp_response" | grep -o '"propertyId":"RCS_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
    if [ -z "$result_version" ]; then
      result_version=$(echo "$fp_response" | grep -o '"propertyId":"RCS_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
    fi
    ;;
```

### Site 4: SH FPD — `gk_install_builder/templates/GKInstall.sh.template:1120-1157`

Add inside the FPD `case "$COMPONENT_TYPE"` block:

```bash
"RCS-SERVICE")
    result_version=$(echo "$fpd_response" | grep -o '"propertyId":"RCS_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
    if [ -z "$result_version" ]; then
      result_version=$(echo "$fpd_response" | grep -o '"propertyId":"RCS_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
    fi
    ;;
```

### Site 5: Python FPD — `gk_install_builder/integrations/api_client.py:354-376`

Add this elif at the end of the FPD elif chain:

```python
# RCS: try Version first, fallback to Update_Version
elif prop_id in ["RCS_Version", "RCS_Update_Version"] and value and versions["RCS-SERVICE"]["value"] is None:
    versions["RCS-SERVICE"] = {"value": value, "source": "FPD (Default)"}
    print(f"[TEST API]     -> Matched RCS ({prop_id}): {value}")
```

## Regression Test

New file `tests/unit/test_fp_fpd_coverage.py`. The test parses each of the 6 dispatch sites and asserts that each of the 7 components has both `*_Version` and `*_Update_Version` property names present in the relevant block. This catches the same class of bug for any future component addition.

The test reuses the audit logic that was used to discover the bug — read each file, slice the relevant line range, search for required substrings.

## Out of Scope

- Refactor of dispatch architecture (each site stays its own switch/case — YAGNI, no demand to centralize).
- Changes to Config-Service path (already addressed by PRIA-1740 fix).
- Changes to bash function logic outside the case branch.
- Changes to other generators or `version_manager.py` (no RCS gap there).

## Testing Plan

1. Run the new regression test — must pass after fix.
2. Run the full pytest suite — must remain green (currently 324 passes + 1 pre-existing infra error).
3. Manual: regenerate scripts via GUI with FP version source for RCS-SERVICE, eyeball that the new switch/case branches are present in the generated PS1/SH.
4. PowerShell synthetic check (no API needed): instantiate a fake response with `[{propertyId="RCS_Version"; value="v2.0.5"}, {propertyId="RCS_Update_Version"; value="v2.0.3"}]` and confirm `$latestVersion` resolves to `v2.0.5`.

## Risk

Low.
- New switch branches only — does not modify existing parser logic.
- Each site change is independent and isolated.
- Regression test guards against the same class of mistake for future components.
