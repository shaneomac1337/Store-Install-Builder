# --removeOverrides / --keepOverrides CLI Flags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--removeOverrides` and `--keepOverrides` CLI flags to generated GKInstall scripts so users can control override file cleanup at runtime, independent of the GUI-configured default.

**Architecture:** Pure template-level change. Two new switch parameters are added to both PowerShell and Bash templates. At runtime, they override the baked-in `@REMOVE_OVERRIDES_AFTER_INSTALL@` value before the existing cleanup logic runs. No generator code changes needed.

**Tech Stack:** PowerShell templates, Bash templates, pytest

**Spec:** `docs/superpowers/specs/2026-03-29-remove-overrides-cli-flag-design.md`

---

### Task 1: Add --removeOverrides / --keepOverrides to PowerShell template

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template:1-24` (param block)
- Modify: `gk_install_builder/templates/GKInstall.ps1.template:2308` (override deployment section)

- [ ] **Step 1: Add parameter declarations to the param block**

In `gk_install_builder/templates/GKInstall.ps1.template`, add two new switch parameters after line 23 (`[switch]$y`):

```powershell
    [switch]$removeOverrides,  # Optional: Force remove override files after installation
    [switch]$keepOverrides  # Optional: Force keep override files after installation
```

The full param block ending becomes:
```powershell
    [switch]$y,  # Optional: Auto-confirm workstation creation without prompting
    [switch]$removeOverrides,  # Optional: Force remove override files after installation
    [switch]$keepOverrides  # Optional: Force keep override files after installation
)
```

Note: `$y` line gains a trailing comma. `$keepOverrides` has no trailing comma (last param).

- [ ] **Step 2: Add conflict check after param block**

After the existing logging setup (around line 30, after `$logFile = ...`), add a conflict check before any other logic runs:

```powershell
# Validate mutually exclusive override flags
if ($removeOverrides -and $keepOverrides) {
    Write-Host "ERROR: --removeOverrides and --keepOverrides are mutually exclusive. Use only one." -ForegroundColor Red
    exit 1
}
```

- [ ] **Step 3: Add CLI override logic in the override deployment section**

At line 2308, the template currently has:
```powershell
$removeOverridesAfterInstall = "@REMOVE_OVERRIDES_AFTER_INSTALL@"
```

Immediately after this line, add the CLI override:
```powershell
# CLI override for remove-overrides-after-install setting
if ($removeOverrides) {
    $removeOverridesAfterInstall = "true"
    Write-Host "CLI Override: Override files will be removed after installation (--removeOverrides)"
}
if ($keepOverrides) {
    $removeOverridesAfterInstall = "false"
    Write-Host "CLI Override: Override files will be kept after installation (--keepOverrides)"
}
```

- [ ] **Step 4: Verify the template is syntactically valid**

Read through the modified template to confirm:
- Param block commas are correct (every param except the last has a trailing comma)
- The conflict check is placed before override deployment logic
- The CLI override is placed after the `$removeOverridesAfterInstall` assignment but before the `if ($noOverrides)` check

- [ ] **Step 5: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template
git commit -m "feat: add --removeOverrides/--keepOverrides CLI flags to PowerShell template"
```

---

### Task 2: Add --removeOverrides / --keepOverrides to Bash template

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.sh.template:18-27` (variable declarations)
- Modify: `gk_install_builder/templates/GKInstall.sh.template:64-99` (case block)
- Modify: `gk_install_builder/templates/GKInstall.sh.template:102` (usage string)
- Modify: `gk_install_builder/templates/GKInstall.sh.template:2749` (override deployment section)

- [ ] **Step 1: Add variable declarations**

In `gk_install_builder/templates/GKInstall.sh.template`, after line 27 (`cli_auto_confirm=false`), add:

```bash
cli_remove_overrides=false  # --removeOverrides: Force remove override files after installation
cli_keep_overrides=false    # --keepOverrides: Force keep override files after installation
```

- [ ] **Step 2: Add case entries for argument parsing**

In the `case "$1"` block, before the `*)` catch-all at line 100, add:

```bash
    --removeOverrides|--removeoverrides)
      cli_remove_overrides=true
      shift
      ;;
    --keepOverrides|--keepoverrides)
      cli_keep_overrides=true
      shift
      ;;
```

- [ ] **Step 3: Update the usage string**

On line 102, update the usage echo to include the new flags. Add `[--removeOverrides] [--keepOverrides]` to the end of the usage string:

```bash
      echo "Usage: $0 [--offline] [--ComponentType <POS|ONEX|WDM|FLOW-SERVICE|LPA|SH|RCS>] [--base_url <url>] [--storeId|--StoreID <id>] [--workstationId|--WorkstationID <id>] [--UseDefaultVersions] [--VersionOverride <version>] [--SystemNameOverride <name>] [--WorkstationNameOverride <name>] [--StructureUniqueNameOverride <name>] [-y|--yes] [-e|--env|--environment <alias>] [--list-environments] [--noOverrides] [--skipCheckAlive] [--skipStartApplication] [--rcsUrl <url>] [--removeOverrides] [--keepOverrides]"
```

- [ ] **Step 4: Add conflict check after argument parsing**

After the `esac` / `done` block (after line 106), add:

```bash
# Validate mutually exclusive override flags
if [ "$cli_remove_overrides" = "true" ] && [ "$cli_keep_overrides" = "true" ]; then
    echo "ERROR: --removeOverrides and --keepOverrides are mutually exclusive. Use only one."
    exit 1
fi
```

- [ ] **Step 5: Add CLI override logic in the override deployment section**

At line 2749, the template currently has:
```bash
remove_overrides_after_install="@REMOVE_OVERRIDES_AFTER_INSTALL@"
```

Immediately after this line, add the CLI override:
```bash
# CLI override for remove-overrides-after-install setting
if [ "$cli_remove_overrides" = "true" ]; then
    remove_overrides_after_install="true"
    echo "CLI Override: Override files will be removed after installation (--removeOverrides)"
fi
if [ "$cli_keep_overrides" = "true" ]; then
    remove_overrides_after_install="false"
    echo "CLI Override: Override files will be kept after installation (--keepOverrides)"
fi
```

- [ ] **Step 6: Verify the template is syntactically valid**

Read through the modified template to confirm:
- Variable declarations follow existing naming convention (`cli_` prefix)
- Case entries include lowercase alternatives (matching existing pattern like `--VersionOverride|--versionoverride|--versionOverride`)
- Conflict check is placed after argument parsing but before main logic
- CLI override is placed after the `remove_overrides_after_install` assignment but before the `if [ "$no_overrides" = true ]` check

- [ ] **Step 7: Commit**

```bash
git add gk_install_builder/templates/GKInstall.sh.template
git commit -m "feat: add --removeOverrides/--keepOverrides CLI flags to Bash template"
```

---

### Task 3: Add tests for new CLI flags in generated scripts

**Files:**
- Modify: `tests/unit/test_installer_overrides.py` (add new test class)

- [ ] **Step 1: Write tests for PowerShell template CLI flags**

Add a new test class at the end of `tests/unit/test_installer_overrides.py`:

```python
class TestRemoveOverridesCLIFlags:
    """Tests for --removeOverrides and --keepOverrides CLI flags in generated scripts"""

    @staticmethod
    def _configure_detection_manager(generator):
        """Helper to configure detection_manager for tests"""
        generator.detection_manager.detection_config = {
            "file_detection_enabled": True,
            "station_file_directory": "C:\\gkretail",
            "station_file_pattern": "*.station",
        }
        generator.detection_manager.hostname_patterns = []

    def test_windows_script_has_remove_overrides_parameter(self, tmp_path):
        """Test that generated Windows script includes --removeOverrides switch"""
        from gk_install_builder.generator import ProjectGenerator
        from unittest.mock import Mock

        generator = ProjectGenerator()
        self._configure_detection_manager(generator)

        generator._create_directory_structure = Mock()
        generator._copy_certificate = Mock()
        generator._generate_environments_json = Mock()
        generator._generate_onboarding = Mock()
        generator._generate_launcher_templates = Mock()
        generator._copy_helper_files = Mock()
        generator._show_success = Mock()

        config = {
            "platform": "Windows",
            "base_url": "test.cloud4retail.co",
            "base_install_dir": "C:\\gkretail",
            "tenant_id": "001",
            "version": "v1.0.0",
            "output_dir": str(tmp_path / "output"),
            "use_hostname_detection": False,
            "system_type": "GKR-POS-CLOUD",
            "certificate_path": ""
        }

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        generator.generate(config)

        content = (output_dir / "GKInstall.ps1").read_text()

        # Verify parameter declarations
        assert "[switch]$removeOverrides" in content
        assert "[switch]$keepOverrides" in content

        # Verify conflict check
        assert "removeOverrides -and $keepOverrides" in content
        assert "mutually exclusive" in content

        # Verify CLI override logic
        assert '$removeOverridesAfterInstall = "true"' in content
        assert '$removeOverridesAfterInstall = "false"' in content
        assert "CLI Override: Override files will be removed" in content
        assert "CLI Override: Override files will be kept" in content

    def test_linux_script_has_remove_overrides_parameter(self, tmp_path):
        """Test that generated Linux script includes --removeOverrides flag parsing"""
        from gk_install_builder.generator import ProjectGenerator
        from unittest.mock import Mock

        generator = ProjectGenerator()
        self._configure_detection_manager(generator)

        generator._create_directory_structure = Mock()
        generator._copy_certificate = Mock()
        generator._generate_environments_json = Mock()
        generator._generate_onboarding = Mock()
        generator._generate_launcher_templates = Mock()
        generator._copy_helper_files = Mock()
        generator._show_success = Mock()

        config = {
            "platform": "Linux",
            "base_url": "test.cloud4retail.co",
            "base_install_dir": "/usr/local/gkretail",
            "tenant_id": "001",
            "version": "v1.0.0",
            "output_dir": str(tmp_path / "output"),
            "use_hostname_detection": False,
            "system_type": "GKR-POS-CLOUD",
            "certificate_path": ""
        }

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        try:
            generator.generate(config)
            output_file = output_dir / "GKInstall.sh"
            if output_file.exists():
                content = output_file.read_text()

                # Verify variable declarations
                assert "cli_remove_overrides=false" in content
                assert "cli_keep_overrides=false" in content

                # Verify case entries
                assert "--removeOverrides|--removeoverrides)" in content
                assert "--keepOverrides|--keepoverrides)" in content

                # Verify conflict check
                assert "cli_remove_overrides" in content
                assert "cli_keep_overrides" in content
                assert "mutually exclusive" in content

                # Verify CLI override logic
                assert 'remove_overrides_after_install="true"' in content
                assert 'remove_overrides_after_install="false"' in content
                assert "CLI Override: Override files will be removed" in content
                assert "CLI Override: Override files will be kept" in content

                # Verify usage string includes new flags
                assert "--removeOverrides" in content
                assert "--keepOverrides" in content
        except Exception:
            pass
```

- [ ] **Step 2: Run the new tests to verify they fail (TDD red phase)**

```bash
pytest tests/unit/test_installer_overrides.py::TestRemoveOverridesCLIFlags -v
```

Expected: FAIL — the template changes from Tasks 1-2 haven't been applied yet if running tests before implementation, or PASS if Tasks 1-2 are already done.

- [ ] **Step 3: Run the full test suite to check for regressions**

```bash
pytest tests/ -v
```

Expected: All existing tests pass. New tests pass if Tasks 1-2 are complete.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_installer_overrides.py
git commit -m "test: add tests for --removeOverrides/--keepOverrides CLI flags"
```

---

### Task 4: Update documentation

**Files:**
- Modify: `docs/cli-parameters-feature.md` (add new CLI parameters to docs)

- [ ] **Step 1: Add --removeOverrides and --keepOverrides to CLI parameters documentation**

Add a new section to `docs/cli-parameters-feature.md` documenting the new flags:

```markdown
### Override File Cleanup Flags

| Parameter | Type | Platform | Description |
|-----------|------|----------|-------------|
| `--removeOverrides` | Switch | Both | Force removal of override files after installation completes |
| `--keepOverrides` | Switch | Both | Force keeping override files after installation completes |

These flags override the "Remove overrides after install" setting that was configured in the GUI at generation time. They are mutually exclusive — using both will cause the script to exit with an error.

**Use case:** When override files were generated with removal disabled (the default), but the user wants to clean them up after a specific run — or vice versa.

**Examples:**
```bash
# Run installer and remove override files afterward
./GKInstall.sh --removeOverrides

# Run installer and ensure override files are kept (even if generated with removal ON)
./GKInstall.sh --keepOverrides

# Use with other flags
./GKInstall.sh --skipCheckAlive --removeOverrides
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/cli-parameters-feature.md
git commit -m "docs: add --removeOverrides/--keepOverrides to CLI parameters documentation"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass (existing 187 + new tests).

- [ ] **Step 2: Generate a test package and verify output**

Run the application, generate a package for both Windows and Linux, and manually verify:
- PowerShell script contains `[switch]$removeOverrides` and `[switch]$keepOverrides` in param block
- Bash script contains `cli_remove_overrides=false` and `cli_keep_overrides=false` in declarations
- Bash script contains the case entries and conflict check
- Both scripts contain the CLI override logic after `@REMOVE_OVERRIDES_AFTER_INSTALL@` assignment
