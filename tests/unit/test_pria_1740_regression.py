"""Regression test for PRIA-1740: RCS default version cannot be retrieved.

Bug: PowerShell pipeline `(... | Sort-Object ...)[0]` unwraps single-element
output to scalar string, then [0] indexes the string returning first char ('v')
instead of the version. Fix: use `Select-Object -First 1`.
"""
from pathlib import Path


TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "gk_install_builder"
    / "templates"
    / "GKInstall.ps1.template"
)


def _version_selection_block():
    """Return the lines around the Config-Service version-selection block."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "versionNameList -and" in line and ".Count -gt 0" in line:
            return "\n".join(lines[idx : idx + 8])
    raise AssertionError(
        "Could not locate the `versionNameList -and ... .Count -gt 0` block "
        "in the PS1 template — has the version-selection logic moved?"
    )


def test_ps1_template_no_indexed_sort_pattern():
    """The buggy `Sort-Object ... } -Descending)[0]` pattern must be gone.

    The script block in the original buggy line ends with `}` before
    `-Descending`. Match on that exact closing sequence to avoid false
    positives from unrelated `Sort-Object | ...)[0]` patterns elsewhere.
    """
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "} -Descending)[0]" not in content, (
        "PS1 template still contains the broken `} -Descending)[0]` pattern "
        "that triggers PowerShell scalar-unwrap on single-element pipelines. "
        "See PRIA-1740 — replace `(...)[0]` with `| Select-Object -First 1`."
    )


def test_ps1_template_version_selection_uses_select_object_first():
    """The version-selection block must use `Select-Object -First 1`.

    Scoped to the `versionNameList`/`Count -gt 0` block so an unrelated
    `Select-Object -First 1` elsewhere in the template cannot mask the bug.
    """
    block = _version_selection_block()
    assert "Select-Object -First 1" in block, (
        "Version-selection block must use `Select-Object -First 1` to avoid "
        "the PowerShell scalar-unwrap bug. See PRIA-1740."
    )
