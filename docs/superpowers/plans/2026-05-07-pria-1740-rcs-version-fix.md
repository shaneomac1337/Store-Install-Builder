# PRIA-1740 RCS Version Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix PowerShell scalar-unwrap bug that causes single-version components (RCS-SERVICE) to retrieve only the literal character `v` from Config-Service instead of the full version string.

**Architecture:** Replace `(... | Sort-Object ...)[0]` indexing pattern with `... | Select-Object -First 1` in the PS1 template. Add a regression test that asserts the template contains the safe pattern. No generator code changes; no bash changes.

**Tech Stack:** PowerShell template (`gk_install_builder/templates/GKInstall.ps1.template`), pytest, plain string assertions.

**Reference:** [docs/superpowers/specs/2026-05-07-pria-1740-rcs-version-fix-design.md](../specs/2026-05-07-pria-1740-rcs-version-fix-design.md)

---

## Task 1: Add regression test for template version-parse pattern

**Files:**
- Create: `tests/unit/test_pria_1740_regression.py`

- [ ] **Step 1: Write the failing test**

```python
"""Regression test for PRIA-1740: RCS default version cannot be retrieved.

Bug: PowerShell pipeline `(... | Sort-Object ...)[0]` unwraps single-element
output to scalar string, then [0] indexes the string returning first char ('v')
instead of the version. Fix: use `Select-Object -First 1`.
"""
from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "gk_install_builder" / "templates" / "GKInstall.ps1.template"


def test_ps1_template_uses_select_object_first():
    """Template must use `Select-Object -First 1` for version selection."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "Select-Object -First 1" in content, (
        "PS1 template must use `Select-Object -First 1` for version selection. "
        "See PRIA-1740 — `(...)[0]` indexing is broken for single-element pipelines."
    )


def test_ps1_template_no_indexed_sort_pattern():
    """Template must not use the broken `Sort-Object ...)[0]` pattern."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    # Match the buggy pattern: closing paren of Sort-Object pipeline followed by [0].
    assert ") -Descending)[0]" not in content, (
        "PS1 template still contains the broken `Sort-Object -Descending)[0]` "
        "pattern that triggers PowerShell scalar-unwrap. See PRIA-1740."
    )
```

- [ ] **Step 2: Run test to verify the second assertion fails (current template still has the bug)**

Run: `pytest tests/unit/test_pria_1740_regression.py -v`

Expected output:
- `test_ps1_template_uses_select_object_first` FAILS — template does not yet contain `Select-Object -First 1`.
- `test_ps1_template_no_indexed_sort_pattern` FAILS — template still contains `) -Descending)[0]`.

- [ ] **Step 3: Commit the test (red state)**

```bash
git add tests/unit/test_pria_1740_regression.py
git commit -m "test: add PRIA-1740 regression test for PS1 version-parse pattern"
```

---

## Task 2: Apply the template fix

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template:937-938`

- [ ] **Step 1: Apply the edit**

Replace this block at line 936–938:

```powershell
                if ($response.versionNameList -and $response.versionNameList.Count -gt 0) {
                    # Sort versions and take the highest (latest)
                    $latestVersion = ($response.versionNameList | Sort-Object { [System.Version]($_ -replace '^v','') } -Descending)[0]
```

With this block:

```powershell
                if ($response.versionNameList -and $response.versionNameList.Count -gt 0) {
                    # Sort versions and take the highest (latest).
                    # Use Select-Object -First 1 — `(...)[0]` breaks for single-element
                    # pipelines because PowerShell unwraps the result to a scalar string
                    # and indexes the first character. See PRIA-1740.
                    $latestVersion = $response.versionNameList |
                        Sort-Object { [System.Version]($_ -replace '^v','') } -Descending |
                        Select-Object -First 1
```

- [ ] **Step 2: Run the regression test to verify it passes**

Run: `pytest tests/unit/test_pria_1740_regression.py -v`

Expected: both tests PASS.

- [ ] **Step 3: Run the full test suite to verify no regression**

Run: `pytest tests/`

Expected: 189/189 passing (187 prior + 2 new).

- [ ] **Step 4: Commit the fix**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template
git commit -m "fix(gkinstall): use Select-Object -First 1 to fix RCS version parse

PowerShell pipeline (... | Sort-Object ...)[0] unwraps single-element output
to a scalar string, then [0] indexes the string returning the first character
('v') instead of the version. Fix uses Select-Object -First 1 which returns
the actual collection element regardless of pipeline length.

Affects any component returning exactly one version on the Config-Service
path. RCS-SERVICE most exposed because it typically publishes a single
version. Both legacy (5.25) and new (5.27+) API endpoints affected.

Refs PRIA-1740"
```

---

## Task 3: Manual verification (post-merge sanity check)

**Files:** none modified.

- [ ] **Step 1: Regenerate scripts via the GUI**

Run: `python -m gk_install_builder.main`

Configure a sample project (any base URL, RCS-SERVICE selected, version source = Config-Service) and click Generate. Open the generated `GKInstall.ps1`.

- [ ] **Step 2: Eyeball the generated script**

Search for `versionNameList` in the generated `GKInstall.ps1`. Confirm:
- Block contains `Select-Object -First 1`.
- Block does not contain `) -Descending)[0]`.

- [ ] **Step 3: (Optional) PowerShell REPL synthetic check**

```powershell
$arr = @("v2.1.10")
$result = $arr | Sort-Object { [System.Version]($_ -replace '^v','') } -Descending | Select-Object -First 1
$result  # expected: v2.1.10 (full string, not 'v')
```

- [ ] **Step 4: Notify reporter**

Comment on PRIA-1740 with the fix commit hash and request the reporter regenerate scripts from the next build, rerun the RCS install, and confirm the log line shows `Found RCS-SERVICE: v2.1.10 (available: 1 versions)` (or whatever the actual published version is).

---

## Self-Review

Spec coverage check:
- Spec § "Fix" → Task 2 applies the exact replacement.
- Spec § "Testing Plan" item 1 (suite stays green) → Task 2 Step 3.
- Spec § "Testing Plan" item 2 (manual regeneration) → Task 3 Step 1–2.
- Spec § "Testing Plan" item 3 (REPL synthetic) → Task 3 Step 3.
- Spec § "Testing Plan" item 4 (field verification) → Task 3 Step 4.
- Spec § "Out of Scope" — bash, pre-release tags, DEBUG lines all explicitly excluded; no tasks for them. Correct.
- Spec § "Affected API Modes" — fix is in shared parsing block; both modes covered automatically. No mode-specific task needed.

Placeholder scan: no TBD, no TODO, no "implement later". Code blocks contain real content. Test code is complete. Commit messages are written.

Type consistency: `Select-Object -First 1` referenced identically in test, fix, and verification. Pattern strings in test match the actual template strings.
