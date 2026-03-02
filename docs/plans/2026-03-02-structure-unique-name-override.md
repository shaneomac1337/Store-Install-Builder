# StructureUniqueNameOverride CLI Parameter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `--StructureUniqueNameOverride` CLI parameter that conditionally injects `structureUniqueName` into the `newNode` object when creating workstation structures via `/structure/nodes`.

**Architecture:** Follows the identical three-tier pass-through pattern used by `--SystemNameOverride` and `--WorkstationNameOverride`: GKInstall accepts the param, passes to store-initialization, store-initialization injects it into the JSON payload before POST. The `create_structure.json` template is unchanged — injection is runtime-only.

**Tech Stack:** PowerShell templates, Bash templates, Python (pytest)

---

### Task 1: Add --StructureUniqueNameOverride to GKInstall.ps1.template

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template:1-22` (param block)
- Modify: `gk_install_builder/templates/GKInstall.ps1.template:1991-1998` (store-init pass-through)

**Step 1: Add parameter to param block**

In `GKInstall.ps1.template`, line 21, after `[string]$WorkstationNameOverride`, add a comma and the new parameter:

```powershell
    [string]$WorkstationNameOverride,  # Optional: Override workstation name (e.g., A319_OneXPOS1)
    [string]$StructureUniqueNameOverride  # Optional: Override structureUniqueName for structure node creation
```

Note: `$WorkstationNameOverride` line changes from no trailing comma to having a trailing comma.

**Step 2: Add pass-through to store-initialization**

After the `WorkstationNameOverride` pass-through block (around line 1998), add:

```powershell
                if (![string]::IsNullOrEmpty($StructureUniqueNameOverride)) {
                    $storeInitArgs['StructureUniqueNameOverride'] = $StructureUniqueNameOverride
                    Write-Host "Passing StructureUniqueNameOverride to store-initialization: $StructureUniqueNameOverride"
                }
```

**Step 3: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template
git commit -m "feat: add --StructureUniqueNameOverride param to GKInstall.ps1 template"
```

---

### Task 2: Add --StructureUniqueNameOverride to GKInstall.sh.template

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.sh.template:25` (variable declaration)
- Modify: `gk_install_builder/templates/GKInstall.sh.template:86-89` (case parsing)
- Modify: `gk_install_builder/templates/GKInstall.sh.template:92` (usage string)
- Modify: `gk_install_builder/templates/GKInstall.sh.template:2407-2410` (store-init pass-through)

**Step 1: Add variable declaration**

After line 25 (`cli_workstation_name_override=""`), add:

```bash
cli_structure_unique_name_override=""  # --StructureUniqueNameOverride: Override structureUniqueName for structure node creation
```

**Step 2: Add case parsing**

After the `--WorkstationNameOverride` case block (lines 86-89), before `*)`, add:

```bash
    --StructureUniqueNameOverride|--structureuniquenameoverride|--structureUniqueNameOverride)
      cli_structure_unique_name_override="$2"
      shift 2
      ;;
```

**Step 3: Update usage string**

Update the usage echo on line 92 to include `[--StructureUniqueNameOverride <name>]`.

**Step 4: Add pass-through to store-initialization**

After the `cli_workstation_name_override` pass-through block (around line 2410), add:

```bash
        if [ -n "$cli_structure_unique_name_override" ]; then
          store_init_args+=(--StructureUniqueNameOverride "$cli_structure_unique_name_override")
          echo "Passing StructureUniqueNameOverride to store-initialization: $cli_structure_unique_name_override"
        fi
```

**Step 5: Commit**

```bash
git add gk_install_builder/templates/GKInstall.sh.template
git commit -m "feat: add --StructureUniqueNameOverride param to GKInstall.sh template"
```

---

### Task 3: Add --StructureUniqueNameOverride to store-initialization.ps1.template

**Files:**
- Modify: `gk_install_builder/templates/store-initialization.ps1.template:1-16` (param block)
- Modify: `gk_install_builder/templates/store-initialization.ps1.template:311` (after placeholder replacements, before POST)

**Step 1: Add parameter to param block**

After line 15 (`[string]$WorkstationNameOverride`), add:

```powershell
    [Parameter(Mandatory=$false)]
    [string]$StructureUniqueNameOverride
```

Note: `$WorkstationNameOverride` line needs a trailing comma added.

**Step 2: Inject structureUniqueName into JSON before POST**

After line 311 (`$processedContent | Set-Content ...`) and before line 314 (`$structureCreateUrl = ...`), add:

```powershell
                        # Inject structureUniqueName into newNode if CLI override provided
                        if (![string]::IsNullOrEmpty($StructureUniqueNameOverride)) {
                            Write-Host "CLI Override: Adding structureUniqueName '$StructureUniqueNameOverride' to create structure request"
                            $jsonObj = $processedContent | ConvertFrom-Json
                            $jsonObj.newNode | Add-Member -NotePropertyName "structureUniqueName" -NotePropertyValue $StructureUniqueNameOverride -Force
                            $processedContent = $jsonObj | ConvertTo-Json -Depth 10
                            $processedContent | Set-Content -Path $processedCreateStructurePath -NoNewline
                        }
```

**Step 3: Commit**

```bash
git add gk_install_builder/templates/store-initialization.ps1.template
git commit -m "feat: add --StructureUniqueNameOverride to store-initialization.ps1 template"
```

---

### Task 4: Add --StructureUniqueNameOverride to store-initialization.sh.template

**Files:**
- Modify: `gk_install_builder/templates/store-initialization.sh.template:42-43` (variable declarations)
- Modify: `gk_install_builder/templates/store-initialization.sh.template:75-78` (case parsing)
- Modify: `gk_install_builder/templates/store-initialization.sh.template:81` (usage string)
- Modify: `gk_install_builder/templates/store-initialization.sh.template:398-399` (after replacements, before POST)

**Step 1: Add variable declaration**

After line 43 (`WORKSTATION_NAME_OVERRIDE=""`), add:

```bash
STRUCTURE_UNIQUE_NAME_OVERRIDE=""
```

**Step 2: Add case parsing**

After the `--WorkstationNameOverride` case block (lines 75-78), before `*)`, add:

```bash
    --StructureUniqueNameOverride)
      STRUCTURE_UNIQUE_NAME_OVERRIDE="$2"
      shift 2
      ;;
```

**Step 3: Update usage string**

Update the usage echo on line 81 to include `[--StructureUniqueNameOverride <name>]`.

**Step 4: Inject structureUniqueName into JSON before POST**

After line 398 (`cp "$temp_structure_file" "$processed_template_path"`) and the echo on line 399, but before line 402 (`structure_create_url=...`), add:

```bash
          # Inject structureUniqueName into newNode if CLI override provided
          if [ -n "$STRUCTURE_UNIQUE_NAME_OVERRIDE" ]; then
            echo "CLI Override: Adding structureUniqueName '$STRUCTURE_UNIQUE_NAME_OVERRIDE' to create structure request"
            if command -v jq &> /dev/null; then
              jq --arg sun "$STRUCTURE_UNIQUE_NAME_OVERRIDE" '.newNode.structureUniqueName = $sun' "$processed_template_path" > "${processed_template_path}.tmp"
              mv "${processed_template_path}.tmp" "$processed_template_path"
            else
              # Fallback: use sed to inject before the closing brace of newNode
              sed -i 's/"name": *"[^"]*"/&,\n        "structureUniqueName": "'"$STRUCTURE_UNIQUE_NAME_OVERRIDE"'"/' "$processed_template_path"
            fi
          fi
```

**Step 5: Commit**

```bash
git add gk_install_builder/templates/store-initialization.sh.template
git commit -m "feat: add --StructureUniqueNameOverride to store-initialization.sh template"
```

---

### Task 5: Write tests for StructureUniqueNameOverride

**Files:**
- Modify: `tests/unit/test_generator_core.py` (add new test class after `TestWorkstationNameCLIOverride` at line 1564)

**Step 1: Write the test class**

Add after line 1564 in `test_generator_core.py`, following the exact pattern of `TestSystemNameCLIOverride` (lines 1322-1441) and `TestWorkstationNameCLIOverride` (lines 1444-1563):

```python
class TestStructureUniqueNameCLIOverride:
    """Test that generated scripts contain --StructureUniqueNameOverride CLI parameter override logic"""

    @staticmethod
    def _configure_detection_manager(generator):
        """Configure detection manager with hostname detection enabled"""
        generator.detection_manager = Mock()
        generator.detection_manager.get_hostname_detection = Mock(return_value=True)
        generator.detection_manager.get_store_id_group = Mock(return_value=1)
        generator.detection_manager.get_workstation_id_group = Mock(return_value=2)
        generator.detection_manager.get_hostname_env_detection = Mock(return_value=False)

    def test_windows_script_has_structure_unique_name_override(self, tmp_path):
        """Test that generated Windows script includes $StructureUniqueNameOverride parameter and splatting"""
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        self._configure_detection_manager(generator)

        config = {
            "platform": "windows",
            "base_url": "test.example.com",
            "tenant_id": "001",
            "system_type": "GKR-POS-CLOUD",
            "ssl_password": "test",
            "auth_service_ba_user": "user",
            "auth_service_ba_password": "pass",
            "base_install_dir": "C:\\gkretail",
            "firebird_server_path": "C:\\Program Files\\Firebird\\Firebird_3_0",
            "jaybird_path": "C:\\gkretail\\Jaybird",
            "api_version": "new",
            "use_default_versions": True,
            "version_source": "FP",
        }

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        generator.generate(config, str(output_dir))

        content = (output_dir / "GKInstall.ps1").read_text()

        # Verify $StructureUniqueNameOverride parameter in param block
        assert "[string]$StructureUniqueNameOverride" in content
        # Verify splatted pass-through
        assert "storeInitArgs['StructureUniqueNameOverride']" in content
        assert "Passing StructureUniqueNameOverride to store-initialization" in content

    def test_linux_script_has_structure_unique_name_override(self, tmp_path):
        """Test that generated Linux script includes --StructureUniqueNameOverride CLI parsing"""
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        self._configure_detection_manager(generator)

        config = {
            "platform": "linux",
            "base_url": "test.example.com",
            "tenant_id": "001",
            "system_type": "GKR-POS-CLOUD",
            "ssl_password": "test",
            "auth_service_ba_user": "user",
            "auth_service_ba_password": "pass",
            "base_install_dir": "/usr/local/gkretail",
            "firebird_server_path": "/opt/firebird",
            "jaybird_path": "/usr/local/gkretail/Jaybird",
            "api_version": "new",
            "use_default_versions": True,
            "version_source": "FP",
        }

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        try:
            generator.generate(config, str(output_dir))

            content = (output_dir / "GKInstall.sh").read_text()

            if content:
                # Verify cli_structure_unique_name_override variable
                assert 'cli_structure_unique_name_override=""' in content
                # Verify case entry for --StructureUniqueNameOverride
                assert "--StructureUniqueNameOverride|--structureuniquenameoverride|--structureUniqueNameOverride)" in content
                assert 'cli_structure_unique_name_override="$2"' in content
                # Verify pass-through to store-initialization
                assert "Passing StructureUniqueNameOverride to store-initialization" in content
                # Verify usage string includes --StructureUniqueNameOverride
                assert "--StructureUniqueNameOverride <name>" in content
        except Exception:
            pass
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_generator_core.py::TestStructureUniqueNameCLIOverride -v`
Expected: FAIL (assertions won't find the strings in templates yet)

**Step 3: Run tests after all template changes are made (Tasks 1-4)**

Run: `pytest tests/unit/test_generator_core.py::TestStructureUniqueNameCLIOverride -v`
Expected: PASS

**Step 4: Run full test suite to verify no regressions**

Run: `pytest tests/ -v`
Expected: All tests PASS (187 existing + new tests)

**Step 5: Commit**

```bash
git add tests/unit/test_generator_core.py
git commit -m "test: add tests for --StructureUniqueNameOverride CLI parameter"
```

---

### Task 6: Final verification and cleanup

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Verify generated output manually**

Generate a sample project and verify:
1. `GKInstall.ps1` has `[string]$StructureUniqueNameOverride` in param block
2. `GKInstall.sh` has `cli_structure_unique_name_override` variable and case parsing
3. `store-initialization.ps1` has `[string]$StructureUniqueNameOverride` param
4. `store-initialization.sh` has `STRUCTURE_UNIQUE_NAME_OVERRIDE` variable and case parsing
5. `create_structure.json` is **unchanged** (no `structureUniqueName` field)

**Step 3: Commit all remaining changes**

```bash
git add -A
git commit -m "feat: add --StructureUniqueNameOverride CLI parameter for structure node creation"
```
