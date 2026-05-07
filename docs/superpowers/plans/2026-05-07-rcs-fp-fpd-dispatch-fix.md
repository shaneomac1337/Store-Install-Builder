# RCS-SERVICE FP/FPD Dispatch Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add RCS-SERVICE property dispatch to the 5 missing FP/FPD parsing sites so generated installers and the GUI test extract live RCS versions from the Employee Hub Service API instead of silently falling back to the hardcoded `@RCS_VERSION@` template variable.

**Architecture:** Each parsing site is an independent switch/case (PowerShell), case statement (Bash), or elif chain (Python). RCS-SERVICE is appended as a new branch in each, mirroring the existing pattern of the closest analog (WDM, which has the same `_Version`-preferred convention). A new pytest scans all six sites and asserts that every component in the canonical list has both `_Version` and `_Update_Version` property names present, blocking this class of regression for any future component.

**Tech Stack:** PowerShell template, Bash template, Python (`requests`), pytest.

**Spec:** [docs/superpowers/specs/2026-05-07-rcs-fp-fpd-dispatch-fix-design.md](../specs/2026-05-07-rcs-fp-fpd-dispatch-fix-design.md)

---

## Files Touched

- Modify: `gk_install_builder/templates/GKInstall.ps1.template` (FP block ~702-765, FPD block ~788-861)
- Modify: `gk_install_builder/templates/GKInstall.sh.template` (FP case ~1059-1096, FPD case ~1120-1157)
- Modify: `gk_install_builder/integrations/api_client.py` (FPD elif chain ~354-376)
- Create: `tests/unit/test_fp_fpd_coverage.py` (regression test)

---

## Task 1: Add coverage regression test (red state)

**Files:**
- Create: `tests/unit/test_fp_fpd_coverage.py`

- [ ] **Step 1: Write the failing test**

Create the file with this exact content:

```python
"""Regression: every component must be dispatched in every FP/FPD parsing site.

Catches the class of bug where a new component is added to the components list
but the property-name dispatch is forgotten in the FP/FPD parsers (the bug that
hit RCS-SERVICE silently from commit 2d34ba7 onward).
"""
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PS1_TEMPLATE = REPO_ROOT / "gk_install_builder" / "templates" / "GKInstall.ps1.template"
SH_TEMPLATE = REPO_ROOT / "gk_install_builder" / "templates" / "GKInstall.sh.template"
API_CLIENT = REPO_ROOT / "gk_install_builder" / "integrations" / "api_client.py"


COMPONENT_PROPERTIES = {
    "POS": ("POSClient_Version", "POSClient_Update_Version"),
    "ONEX-POS": ("OneX_Version", "OneX_Update_Version"),
    "WDM": ("WDM_Version", "WDM_Update_Version"),
    "FLOW-SERVICE": ("FlowService_Version", "FlowService_Update_Version"),
    "LPA-SERVICE": ("LPA_Version", "LPA_Update_Version"),
    "STOREHUB-SERVICE": ("StoreHub_Version", "SH_Update_Version"),
    "RCS-SERVICE": ("RCS_Version", "RCS_Update_Version"),
}


# (site_name, file_path, anchor_phrase, end_phrase) — slice the file between the
# anchor (start of the FP or FPD parsing block) and the end phrase (end of that
# block). The slice is used as the search corpus for property-name presence.
DISPATCH_SITES = [
    (
        "PS1 FP",
        PS1_TEMPLATE,
        "Step 1: Try FP scope first",
        'Write-Host "Found $($versions.Count) components in FP scope"',
    ),
    (
        "PS1 FPD",
        PS1_TEMPLATE,
        "Step 2: For components not found in FP, try FPD scope",
        "Found additional $($versions.Count",
    ),
    (
        "SH FP",
        SH_TEMPLATE,
        "Step 1: Try FP scope first (modified/customized versions)",
        'Found $COMPONENT_TYPE version in FP scope',
    ),
    (
        "SH FPD",
        SH_TEMPLATE,
        "Step 2: If not found in FP, try FPD scope",
        'Found $COMPONENT_TYPE version in FPD scope',
    ),
    (
        "Py FP",
        API_CLIENT,
        "# Step 1: Try FP scope first",
        "# Step 2: For components not found in FP, try FPD scope",
    ),
    (
        "Py FPD",
        API_CLIENT,
        "# Step 2: For components not found in FP, try FPD scope",
        "loading_dialog.destroy()",
    ),
]


def _slice(file_path: Path, start_phrase: str, end_phrase: str) -> str:
    text = file_path.read_text(encoding="utf-8")
    start = text.find(start_phrase)
    if start == -1:
        raise AssertionError(
            f"Could not find start anchor in {file_path.name}: {start_phrase!r}"
        )
    end = text.find(end_phrase, start)
    if end == -1:
        raise AssertionError(
            f"Could not find end anchor in {file_path.name}: {end_phrase!r}"
        )
    return text[start:end]


@pytest.mark.parametrize("site,path,start_phrase,end_phrase", DISPATCH_SITES)
@pytest.mark.parametrize("component,props", list(COMPONENT_PROPERTIES.items()))
def test_dispatch_site_handles_component(
    site, path, start_phrase, end_phrase, component, props
):
    """Each FP/FPD dispatch block must reference both property names per component."""
    block = _slice(path, start_phrase, end_phrase)
    missing = [prop for prop in props if prop not in block]
    assert not missing, (
        f"Site '{site}' is missing property dispatch for component "
        f"{component!r}: {missing!r}. Add a switch/case/elif branch in "
        f"{path.name} between anchors {start_phrase!r} and {end_phrase!r}."
    )
```

- [ ] **Step 2: Run the test to confirm red state for RCS only**

Run: `python -m pytest tests/unit/test_fp_fpd_coverage.py -v 2>&1 | tail -20`

Expected: 5 failing test cases — all `RCS-SERVICE`-related cases for sites `PS1 FP`, `PS1 FPD`, `SH FP`, `SH FPD`, `Py FPD`. The `Py FP` x `RCS-SERVICE` case must pass (already covered). All 36 non-RCS cases (6 sites x 6 components) must pass.

If any non-RCS case fails or any RCS case unexpectedly passes, STOP and report — anchor phrases or property names are wrong.

- [ ] **Step 3: Commit the test in red state**

```bash
git add tests/unit/test_fp_fpd_coverage.py
git commit -m "test: add FP/FPD dispatch coverage matrix regression test"
```

---

## Task 2: Add RCS-SERVICE to PS1 FP dispatch

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template` (after line ~764, inside the FP scope `switch ($property.propertyId)` block, after the `StoreHub_Version` case)

- [ ] **Step 1: Apply the edit**

Find this block:
```powershell
                        "StoreHub_Version" {
                            if (-not $versions.ContainsKey("STOREHUB-SERVICE")) {
                                $versions["STOREHUB-SERVICE"] = $property.value
                                $versionSources["STOREHUB-SERVICE"] = "FP (Modified)"
                            }
                        }
                    }
                }
            }

            Write-Host "Found $($versions.Count) components in FP scope"
```

Replace with:
```powershell
                        "StoreHub_Version" {
                            if (-not $versions.ContainsKey("STOREHUB-SERVICE")) {
                                $versions["STOREHUB-SERVICE"] = $property.value
                                $versionSources["STOREHUB-SERVICE"] = "FP (Modified)"
                            }
                        }
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
                    }
                }
            }

            Write-Host "Found $($versions.Count) components in FP scope"
```

- [ ] **Step 2: Run the targeted regression case to verify green**

Run: `python -m pytest "tests/unit/test_fp_fpd_coverage.py::test_dispatch_site_handles_component[RCS-SERVICE-RCS_Version-RCS_Update_Version-PS1 FP-C\\:\\Users\\mpenkava\\Desktop\\Store-Install-Builder\\gk_install_builder\\templates\\GKInstall.ps1.template-Step 1: Try FP scope first-Write-Host \"Found $($versions.Count) components in FP scope\"]" -v` (parametrize ID may vary; alternatively use `-k "PS1 FP and RCS"`).

Easier: `python -m pytest tests/unit/test_fp_fpd_coverage.py -v -k "PS1 FP and RCS"`. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template
git commit -m "fix(gkinstall): add RCS-SERVICE FP-scope dispatch in PS1 template

Mirror WDM/Flow/LPA pattern: prefer RCS_Version, fallback RCS_Update_Version.
Without this, generated installers fall back to hardcoded @RCS_VERSION@ when
fetching from Employee Hub FP scope.

Refs RCS FP/FPD dispatch fix"
```

---

## Task 3: Add RCS-SERVICE to PS1 FPD dispatch

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template` (after line ~860, inside the FPD scope `switch` block, after the `StoreHub_Version` case)

- [ ] **Step 1: Apply the edit**

Find this block:
```powershell
                            "StoreHub_Version" {
                                if (-not $versions.ContainsKey("STOREHUB-SERVICE")) {
                                    $versions["STOREHUB-SERVICE"] = $property.value
                                    $versionSources["STOREHUB-SERVICE"] = "FPD (Default)"
                                }
                            }
                        }
                    }
                }

                Write-Host "Found additional $($versions.Count - ($allComponents.Count - $missingComponents.Count)) components in FPD scope"
```

Replace with:
```powershell
                            "StoreHub_Version" {
                                if (-not $versions.ContainsKey("STOREHUB-SERVICE")) {
                                    $versions["STOREHUB-SERVICE"] = $property.value
                                    $versionSources["STOREHUB-SERVICE"] = "FPD (Default)"
                                }
                            }
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
                        }
                    }
                }

                Write-Host "Found additional $($versions.Count - ($allComponents.Count - $missingComponents.Count)) components in FPD scope"
```

- [ ] **Step 2: Run the targeted regression case**

Run: `python -m pytest tests/unit/test_fp_fpd_coverage.py -v -k "PS1 FPD and RCS"`. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template
git commit -m "fix(gkinstall): add RCS-SERVICE FPD-scope dispatch in PS1 template

Same pattern as the FP-scope addition. Both branches guarded by ContainsKey
because FP-scope values must always win over FPD defaults.

Refs RCS FP/FPD dispatch fix"
```

---

## Task 4: Add RCS-SERVICE to bash FP dispatch

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.sh.template` (inside the FP scope `case "$COMPONENT_TYPE"` block, after the `STOREHUB-SERVICE` branch around line ~1095)

- [ ] **Step 1: Apply the edit**

Find this block:
```bash
      "STOREHUB-SERVICE")
        result_version=$(echo "$fp_response" | grep -o '"propertyId":"SH_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
        if [ -z "$result_version" ]; then
          result_version=$(echo "$fp_response" | grep -o '"propertyId":"StoreHub_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
        fi
        ;;
    esac
```

Replace with:
```bash
      "STOREHUB-SERVICE")
        result_version=$(echo "$fp_response" | grep -o '"propertyId":"SH_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
        if [ -z "$result_version" ]; then
          result_version=$(echo "$fp_response" | grep -o '"propertyId":"StoreHub_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
        fi
        ;;
      "RCS-SERVICE")
        result_version=$(echo "$fp_response" | grep -o '"propertyId":"RCS_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
        if [ -z "$result_version" ]; then
          result_version=$(echo "$fp_response" | grep -o '"propertyId":"RCS_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
        fi
        ;;
    esac
```

- [ ] **Step 2: Run the targeted regression case**

Run: `python -m pytest tests/unit/test_fp_fpd_coverage.py -v -k "SH FP and RCS"`. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add gk_install_builder/templates/GKInstall.sh.template
git commit -m "fix(gkinstall): add RCS-SERVICE FP-scope dispatch in bash template

Mirror WDM bash pattern. Same root cause as PS1 fix: RCS was added to the
component list but its FP/FPD case branches were never written.

Refs RCS FP/FPD dispatch fix"
```

---

## Task 5: Add RCS-SERVICE to bash FPD dispatch

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.sh.template` (inside the FPD scope `case "$COMPONENT_TYPE"` block, after the `ONEX-POS` branch around line ~1156)

- [ ] **Step 1: Apply the edit**

Find this block:
```bash
        "ONEX-POS")
          result_version=$(echo "$fpd_response" | grep -o '"propertyId":"OneX_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
          if [ -z "$result_version" ]; then
            result_version=$(echo "$fpd_response" | grep -o '"propertyId":"OneX_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
          fi
          ;;
      esac
```

Replace with:
```bash
        "ONEX-POS")
          result_version=$(echo "$fpd_response" | grep -o '"propertyId":"OneX_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
          if [ -z "$result_version" ]; then
            result_version=$(echo "$fpd_response" | grep -o '"propertyId":"OneX_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
          fi
          ;;
        "RCS-SERVICE")
          result_version=$(echo "$fpd_response" | grep -o '"propertyId":"RCS_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
          if [ -z "$result_version" ]; then
            result_version=$(echo "$fpd_response" | grep -o '"propertyId":"RCS_Update_Version"[^}]*"value":"[^"]*"' | sed 's/.*"value":"\([^"]*\)".*/\1/')
          fi
          ;;
      esac
```

- [ ] **Step 2: Run the targeted regression case**

Run: `python -m pytest tests/unit/test_fp_fpd_coverage.py -v -k "SH FPD and RCS"`. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add gk_install_builder/templates/GKInstall.sh.template
git commit -m "fix(gkinstall): add RCS-SERVICE FPD-scope dispatch in bash template

Same pattern as bash FP fix.

Refs RCS FP/FPD dispatch fix"
```

---

## Task 6: Add RCS-SERVICE to Python FPD dispatch

**Files:**
- Modify: `gk_install_builder/integrations/api_client.py` (inside the FPD elif chain around line ~376, after the `STOREHUB-SERVICE` branch)

- [ ] **Step 1: Apply the edit**

Find this block:
```python
                            # StoreHub: try Update_Version first, fallback to Version
                            elif prop_id in ["SH_Update_Version", "StoreHub_Version"] and value and versions["STOREHUB-SERVICE"]["value"] is None:
                                versions["STOREHUB-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched StoreHub ({prop_id}): {value}")
                    except Exception as e:
                        print(f"Warning: FPD scope request failed: {e}")
```

Replace with:
```python
                            # StoreHub: try Update_Version first, fallback to Version
                            elif prop_id in ["SH_Update_Version", "StoreHub_Version"] and value and versions["STOREHUB-SERVICE"]["value"] is None:
                                versions["STOREHUB-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched StoreHub ({prop_id}): {value}")
                            # RCS: try Version first, fallback to Update_Version
                            elif prop_id in ["RCS_Version", "RCS_Update_Version"] and value and versions["RCS-SERVICE"]["value"] is None:
                                versions["RCS-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched RCS ({prop_id}): {value}")
                    except Exception as e:
                        print(f"Warning: FPD scope request failed: {e}")
```

- [ ] **Step 2: Run the targeted regression case**

Run: `python -m pytest tests/unit/test_fp_fpd_coverage.py -v -k "Py FPD and RCS"`. Expected: PASS.

- [ ] **Step 3: Run the full coverage test to confirm full green**

Run: `python -m pytest tests/unit/test_fp_fpd_coverage.py -v`. Expected: 42 passed (7 components x 6 sites = 42 cases, all green).

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest tests/`. Expected: at least 326 passed (324 prior + 2 net-new from coverage matrix less the 5 reds that are now green; full count is 366 cases for the new file but parametrized to one xfail in worst case — the salient point is no NEW failures and the 1 pre-existing infra error remains the only error). Concretely: only the pre-existing `test_infrastructure_validation.py::TestMockHelpers::test_mock_detection_manager_configured` error is allowed.

- [ ] **Step 5: Commit**

```bash
git add gk_install_builder/integrations/api_client.py
git commit -m "fix(api_client): add RCS-SERVICE FPD-scope dispatch in GUI test

Closes the parity gap with the FP-scope code (which already handled RCS).
Without this, the GUI Test API button reports RCS-SERVICE as 'Not Found'
when only the FPD scope returns it.

Refs RCS FP/FPD dispatch fix"
```

---

## Task 7: Manual verification

**Files:** none modified.

- [ ] **Step 1: Regenerate scripts via the GUI**

Run: `python -m gk_install_builder.main`

Pick any project (FP source for RCS-SERVICE), generate. Open generated `GKInstall.ps1`.

- [ ] **Step 2: Eyeball the generated script**

Search for `RCS_Version` in the generated `GKInstall.ps1`. Confirm both branches (`"RCS_Version"` and `"RCS_Update_Version"`) appear in both the FP and the FPD scope dispatch blocks.

- [ ] **Step 3: PowerShell synthetic check (no API needed)**

Run in pwsh:

```powershell
$fakeFp = @(
    @{ propertyId = "RCS_Version"; value = "v2.0.5" }
    @{ propertyId = "RCS_Update_Version"; value = "v2.0.3" }
)
$versions = @{}
$versionSources = @{}
foreach ($property in $fakeFp) {
    if ($property.value) {
        switch ($property.propertyId) {
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
        }
    }
}
"RCS-SERVICE => $($versions['RCS-SERVICE']) ($($versionSources['RCS-SERVICE']))"
```

Expected output: `RCS-SERVICE => v2.0.5 (FP (Modified))` (RCS_Version preferred over RCS_Update_Version).

- [ ] **Step 4: Notify reporter**

Reply on Soeren's verbal report (and/or PRIA-1740 follow-up comment): list the 6 commits (Task 1 test + Tasks 2-6 fixes), say the GUI Test API will now show RCS in FPD scope as well, and ask for field re-test.

---

## Self-Review

**Spec coverage check:**
- Spec § Site 1 (PS1 FP) → Task 2.
- Spec § Site 2 (PS1 FPD) → Task 3.
- Spec § Site 3 (SH FP) → Task 4.
- Spec § Site 4 (SH FPD) → Task 5.
- Spec § Site 5 (Python FPD) → Task 6.
- Spec § Regression Test → Task 1.
- Spec § Testing Plan items 1-2 (regression test + full suite) → Task 6 Step 4.
- Spec § Testing Plan item 3 (manual eyeball) → Task 7 Step 2.
- Spec § Testing Plan item 4 (PowerShell synthetic) → Task 7 Step 3.
- Spec § Out of Scope items: not implemented (correct).

**Placeholder scan:** no TBD/TODO. Code blocks contain real content. Commit messages drafted.

**Type consistency:** Property names (`RCS_Version`, `RCS_Update_Version`) used consistently across all tasks. Component key (`RCS-SERVICE`) consistent. Source labels (`FP (Modified)`, `FPD (Default)`) match existing template strings.
