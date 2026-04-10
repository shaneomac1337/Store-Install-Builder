# WSID Leading Zero Stripping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional checkbox that strips leading zeros from detected Workstation IDs in generated runtime scripts via integer conversion.

**Architecture:** New top-level boolean `strip_leading_zeros_wsid` in `detection_config`. The generator conditionally injects a single conversion line (`[int]` / `10#`) after all detection resolves in both PS1 and Bash templates. The Detection Settings dialog gets a checkbox and updated test preview with arrow notation.

**Tech Stack:** Python, CustomTkinter, PowerShell/Bash script generation, pytest

---

### Task 1: Add config setting and detection manager support with tests

**Goal:** Add `strip_leading_zeros_wsid` boolean to DetectionManager with getter/setter and config persistence.

**Files:**
- Modify: `gk_install_builder/detection.py:8-39` (default config dict)
- Modify: `gk_install_builder/detection.py:124-148` (set_config method)
- Modify: `tests/unit/test_detection.py` (add new test class)

**Acceptance Criteria:**
- [ ] `strip_leading_zeros_wsid` defaults to `False` in detection_config
- [ ] Getter and setter methods exist on DetectionManager
- [ ] `set_config()` correctly loads the setting from saved config
- [ ] Missing key in saved config defaults to `False` (backward compatibility)
- [ ] All existing tests still pass

**Verify:** `pytest tests/unit/test_detection.py -v` → all PASS

**Steps:**

- [ ] **Step 1: Write failing tests for the new config setting**

Add to `tests/unit/test_detection.py`:

```python
class TestWsidLeadingZeroStripping:
    """Test workstation ID leading zero stripping configuration"""

    def test_strip_leading_zeros_wsid_defaults_to_false(self):
        """Test that strip_leading_zeros_wsid defaults to False"""
        from gk_install_builder.detection import DetectionManager
        dm = DetectionManager()
        assert dm.is_strip_leading_zeros_wsid() is False

    def test_enable_strip_leading_zeros_wsid(self):
        """Test enabling strip_leading_zeros_wsid"""
        from gk_install_builder.detection import DetectionManager
        dm = DetectionManager()
        dm.set_strip_leading_zeros_wsid(True)
        assert dm.is_strip_leading_zeros_wsid() is True

    def test_disable_strip_leading_zeros_wsid(self):
        """Test disabling strip_leading_zeros_wsid after enabling"""
        from gk_install_builder.detection import DetectionManager
        dm = DetectionManager()
        dm.set_strip_leading_zeros_wsid(True)
        dm.set_strip_leading_zeros_wsid(False)
        assert dm.is_strip_leading_zeros_wsid() is False

    def test_strip_leading_zeros_wsid_in_get_config(self):
        """Test that strip_leading_zeros_wsid appears in get_config output"""
        from gk_install_builder.detection import DetectionManager
        dm = DetectionManager()
        config = dm.get_config()
        assert "strip_leading_zeros_wsid" in config
        assert config["strip_leading_zeros_wsid"] is False

    def test_set_config_loads_strip_leading_zeros_wsid(self):
        """Test that set_config correctly loads the setting"""
        from gk_install_builder.detection import DetectionManager
        dm = DetectionManager()
        dm.set_config({"strip_leading_zeros_wsid": True})
        assert dm.is_strip_leading_zeros_wsid() is True

    def test_set_config_without_strip_leading_zeros_preserves_default(self):
        """Test backward compatibility: missing key keeps default False"""
        from gk_install_builder.detection import DetectionManager
        dm = DetectionManager()
        dm.set_config({"file_detection_enabled": True})
        assert dm.is_strip_leading_zeros_wsid() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_detection.py::TestWsidLeadingZeroStripping -v`
Expected: FAIL with `AttributeError: 'DetectionManager' object has no attribute 'is_strip_leading_zeros_wsid'`

- [ ] **Step 3: Implement the config setting in DetectionManager**

In `gk_install_builder/detection.py`, add `"strip_leading_zeros_wsid": False` as a top-level key in `self.detection_config` (line 8-39, alongside `file_detection_enabled`).

Add getter/setter methods after the existing `is_file_detection_enabled` method (around line 109):

```python
def set_strip_leading_zeros_wsid(self, enabled=True):
    """Enable or disable stripping leading zeros from workstation ID"""
    self.detection_config["strip_leading_zeros_wsid"] = enabled

def is_strip_leading_zeros_wsid(self):
    """Check if leading zeros should be stripped from workstation ID"""
    return self.detection_config.get("strip_leading_zeros_wsid", False)
```

In `set_config()` method (around line 124), add handling for the new key:

```python
if "strip_leading_zeros_wsid" in config:
    self.detection_config["strip_leading_zeros_wsid"] = config["strip_leading_zeros_wsid"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_detection.py -v`
Expected: All PASS (both new and existing)

- [ ] **Step 5: Commit**

```bash
git add gk_install_builder/detection.py tests/unit/test_detection.py
git commit -m "feat: add strip_leading_zeros_wsid config to DetectionManager"
```

---

### Task 2: Add WSID stripping injection to generated scripts with tests

**Goal:** Generator conditionally injects integer conversion line into PowerShell and Bash scripts after all detection resolves.

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template:1902` (add placeholder)
- Modify: `gk_install_builder/templates/GKInstall.sh.template:2346` (add placeholder)
- Modify: `gk_install_builder/generators/gk_install_generator.py:585` (add placeholder replacement)
- Modify: `tests/unit/test_generator_integration.py` (add new tests)

**Acceptance Criteria:**
- [ ] When `strip_leading_zeros_wsid` is `True`, generated PS1 contains `[string][int]$workstationId`
- [ ] When `strip_leading_zeros_wsid` is `True`, generated Bash contains `workstationId=$(( 10#$workstationId ))`
- [ ] When `strip_leading_zeros_wsid` is `False` (default), neither line appears
- [ ] Stripping line is placed after CLI overrides and before "Print final results"
- [ ] Both platforms tested

**Verify:** `pytest tests/unit/test_generator_integration.py -v -k "strip_leading_zeros"` → all PASS

**Steps:**

- [ ] **Step 1: Write failing tests for generated script output**

Add to `tests/unit/test_generator_integration.py`:

```python
class TestWsidLeadingZeroStrippingGeneration:
    """Test that strip_leading_zeros_wsid setting affects generated scripts"""

    def test_ps1_contains_stripping_when_enabled(self, tmp_path):
        """Test PowerShell script contains integer conversion when enabled"""
        config = create_config(
            platform="Windows",
            use_hostname_detection=True,
            detection_config={
                "file_detection_enabled": True,
                "use_base_directory": True,
                "base_directory": "C:\\gkretail\\stations",
                "strip_leading_zeros_wsid": True,
                "hostname_detection": {
                    "windows_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "linux_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "test_hostname": "1234-101",
                    "detect_environment": False,
                    "store_group": 1,
                    "workstation_group": 2
                }
            },
            output_dir=str(tmp_path)
        )
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        generator.generate_project(config)

        ps1_path = tmp_path / "GKInstall.ps1"
        content = ps1_path.read_text()
        assert "[string][int]$workstationId" in content

    def test_ps1_no_stripping_when_disabled(self, tmp_path):
        """Test PowerShell script does NOT contain integer conversion when disabled"""
        config = create_config(
            platform="Windows",
            use_hostname_detection=True,
            detection_config={
                "file_detection_enabled": True,
                "use_base_directory": True,
                "base_directory": "C:\\gkretail\\stations",
                "strip_leading_zeros_wsid": False,
                "hostname_detection": {
                    "windows_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "linux_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "test_hostname": "1234-101",
                    "detect_environment": False,
                    "store_group": 1,
                    "workstation_group": 2
                }
            },
            output_dir=str(tmp_path)
        )
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        generator.generate_project(config)

        ps1_path = tmp_path / "GKInstall.ps1"
        content = ps1_path.read_text()
        assert "[string][int]$workstationId" not in content

    def test_bash_contains_stripping_when_enabled(self, tmp_path):
        """Test Bash script contains integer conversion when enabled"""
        config = create_config(
            platform="Linux",
            use_hostname_detection=True,
            detection_config={
                "file_detection_enabled": True,
                "use_base_directory": True,
                "base_directory": "/usr/local/gkretail/stations",
                "strip_leading_zeros_wsid": True,
                "hostname_detection": {
                    "windows_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "linux_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "test_hostname": "1234-101",
                    "detect_environment": False,
                    "store_group": 1,
                    "workstation_group": 2
                }
            },
            output_dir=str(tmp_path)
        )
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        generator.generate_project(config)

        sh_path = tmp_path / "GKInstall.sh"
        content = sh_path.read_text()
        assert "workstationId=$(( 10#$workstationId ))" in content

    def test_bash_no_stripping_when_disabled(self, tmp_path):
        """Test Bash script does NOT contain integer conversion when disabled"""
        config = create_config(
            platform="Linux",
            use_hostname_detection=True,
            detection_config={
                "file_detection_enabled": True,
                "use_base_directory": True,
                "base_directory": "/usr/local/gkretail/stations",
                "strip_leading_zeros_wsid": False,
                "hostname_detection": {
                    "windows_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "linux_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "test_hostname": "1234-101",
                    "detect_environment": False,
                    "store_group": 1,
                    "workstation_group": 2
                }
            },
            output_dir=str(tmp_path)
        )
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        generator.generate_project(config)

        sh_path = tmp_path / "GKInstall.sh"
        content = sh_path.read_text()
        assert "workstationId=$(( 10#$workstationId ))" not in content

    def test_ps1_stripping_before_print_results(self, tmp_path):
        """Test that stripping line appears before Print final results in PS1"""
        config = create_config(
            platform="Windows",
            use_hostname_detection=True,
            detection_config={
                "file_detection_enabled": True,
                "use_base_directory": True,
                "base_directory": "C:\\gkretail\\stations",
                "strip_leading_zeros_wsid": True,
                "hostname_detection": {
                    "windows_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "linux_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "test_hostname": "1234-101",
                    "detect_environment": False,
                    "store_group": 1,
                    "workstation_group": 2
                }
            },
            output_dir=str(tmp_path)
        )
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        generator.generate_project(config)

        ps1_path = tmp_path / "GKInstall.ps1"
        content = ps1_path.read_text()
        strip_pos = content.index("[string][int]$workstationId")
        print_pos = content.index("# Print final results")
        assert strip_pos < print_pos

    def test_bash_stripping_before_print_results(self, tmp_path):
        """Test that stripping line appears before Print final results in Bash"""
        config = create_config(
            platform="Linux",
            use_hostname_detection=True,
            detection_config={
                "file_detection_enabled": True,
                "use_base_directory": True,
                "base_directory": "/usr/local/gkretail/stations",
                "strip_leading_zeros_wsid": True,
                "hostname_detection": {
                    "windows_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "linux_regex": r"^([0-9]{4})-([0-9]{3})$",
                    "test_hostname": "1234-101",
                    "detect_environment": False,
                    "store_group": 1,
                    "workstation_group": 2
                }
            },
            output_dir=str(tmp_path)
        )
        from gk_install_builder.generator import ProjectGenerator
        generator = ProjectGenerator()
        generator.generate_project(config)

        sh_path = tmp_path / "GKInstall.sh"
        content = sh_path.read_text()
        strip_pos = content.index("workstationId=$(( 10#$workstationId ))")
        print_pos = content.index("# Print final results")
        assert strip_pos < print_pos
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_generator_integration.py -v -k "strip_leading_zeros"`
Expected: FAIL (stripping lines not found in generated output)

- [ ] **Step 3: Add placeholder to PowerShell template**

In `gk_install_builder/templates/GKInstall.ps1.template`, add placeholder after line 1901 (after CLI override block, before "# Print final results"):

```powershell
}

# WSID_STRIP_LEADING_ZEROS_PLACEHOLDER

# Print final results
```

- [ ] **Step 4: Add placeholder to Bash template**

In `gk_install_builder/templates/GKInstall.sh.template`, add placeholder after line 2345 (after CLI override block, before "# Print final results"):

```bash
fi

# WSID_STRIP_LEADING_ZEROS_PLACEHOLDER

# Print final results
```

- [ ] **Step 5: Add placeholder replacement in generator**

In `gk_install_builder/generators/gk_install_generator.py`, after the existing hostname detection placeholder replacements (around line 585), add:

```python
# Handle WSID leading zero stripping
strip_wsid_zeros = detection_manager.is_strip_leading_zeros_wsid()
if strip_wsid_zeros:
    if platform == "Windows":
        wsid_strip_code = """# Strip leading zeros from Workstation ID (integer conversion)
if ($workstationId -match '^[0-9]+$') {
    $workstationId = [string][int]$workstationId
    Write-Host "Workstation ID after leading zero removal: $workstationId"
}"""
    else:
        wsid_strip_code = """# Strip leading zeros from Workstation ID (integer conversion)
if [[ "$workstationId" =~ ^[0-9]+$ ]]; then
  workstationId=$(( 10#$workstationId ))
  echo "Workstation ID after leading zero removal: $workstationId"
fi"""
    template = template.replace("# WSID_STRIP_LEADING_ZEROS_PLACEHOLDER", wsid_strip_code)
else:
    template = template.replace("# WSID_STRIP_LEADING_ZEROS_PLACEHOLDER", "")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_generator_integration.py -v -k "strip_leading_zeros"`
Expected: All PASS

Run: `pytest tests/ -v`
Expected: All existing tests still PASS

- [ ] **Step 7: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template gk_install_builder/templates/GKInstall.sh.template gk_install_builder/generators/gk_install_generator.py tests/unit/test_generator_integration.py
git commit -m "feat: inject WSID leading zero stripping into generated scripts"
```

---

### Task 3: Add UI checkbox and update test preview in Detection Settings dialog

**Goal:** Add "Remove leading zeros from Workstation ID" checkbox with tooltip, and update the regex test preview to show arrow notation (e.g., `01 → 1`) when enabled.

**Files:**
- Modify: `gk_install_builder/dialogs/detection_settings.py:607-640` (add checkbox after env detection frame)
- Modify: `gk_install_builder/dialogs/detection_settings.py:1008-1033` (update test preview display)

**Acceptance Criteria:**
- [ ] Checkbox labeled "Remove leading zeros from Workstation ID" appears in Detection Settings
- [ ] Checkbox has a descriptive tooltip
- [ ] Checkbox state is persisted to/from DetectionManager config
- [ ] Test preview shows `Workstation ID: 01 → 1` when enabled and WSID has leading zeros
- [ ] Test preview shows `Workstation ID: 10` normally when WSID has no leading zeros (no arrow)
- [ ] Test preview shows `Workstation ID: 101` when disabled (no arrow regardless)

**Verify:** Manual verification — open Detection Settings, toggle checkbox, test regex preview

**Steps:**

- [ ] **Step 1: Add the checkbox frame after the environment detection frame**

In `gk_install_builder/dialogs/detection_settings.py`, after the environment detection frame section (around line 662), add a new frame:

```python
# WSID Leading Zero Stripping
wsid_strip_frame = ctk.CTkFrame(tab_regex)
wsid_strip_frame.pack(fill="x", padx=10, pady=10)

ctk.CTkLabel(
    wsid_strip_frame,
    text="Workstation ID Transformation",
    font=("Helvetica", 12, "bold")
).pack(anchor="w", padx=10, pady=(5, 5))

# Create BooleanVar for WSID zero stripping
self.strip_wsid_zeros_var = ctk.BooleanVar(
    value=self.detection_manager.is_strip_leading_zeros_wsid()
)

# Checkbox
strip_wsid_checkbox = ctk.CTkCheckBox(
    wsid_strip_frame,
    text="Remove leading zeros from Workstation ID",
    variable=self.strip_wsid_zeros_var,
    command=self.on_strip_wsid_toggle,
    onvalue=True,
    offvalue=False
)
strip_wsid_checkbox.pack(anchor="w", padx=10, pady=5)

# Tooltip/explanation label
ctk.CTkLabel(
    wsid_strip_frame,
    text="Useful when hostname patterns produce zero-padded workstation IDs (e.g., '01' becomes '1'). "
         "Applies to all detection sources: hostname, file, CLI, and manual input.",
    text_color="#b0b0b0",
    font=("Helvetica", 11),
    wraplength=650,
    justify="left"
).pack(anchor="w", padx=10, pady=(0, 5))
```

- [ ] **Step 2: Add the toggle handler method**

Add to the DetectionSettingsDialog class:

```python
def on_strip_wsid_toggle(self):
    """Handle WSID leading zero stripping checkbox toggle"""
    enabled = self.strip_wsid_zeros_var.get()
    self.detection_manager.set_strip_leading_zeros_wsid(enabled)
```

- [ ] **Step 3: Initialize the BooleanVar in __init__**

Add `self.strip_wsid_zeros_var = None` to the `__init__` method alongside `self.hostname_env_detection_var = None` (around line 54).

- [ ] **Step 4: Update test preview to show arrow notation**

In the `test_regex` method, update the Workstation ID display lines (around lines 1012 and 1024). Replace the simple display with conditional arrow notation:

```python
# For both Windows (line 1012) and Linux (line 1024) blocks:
ws_id = result['workstation_id']
if self.strip_wsid_zeros_var and self.strip_wsid_zeros_var.get() and ws_id.lstrip('0') and ws_id != ws_id.lstrip('0'):
    stripped = str(int(ws_id))
    results_text.insert("end", f"Workstation ID: {ws_id} \u2192 {stripped}\n")
elif self.strip_wsid_zeros_var and self.strip_wsid_zeros_var.get() and ws_id == '0':
    results_text.insert("end", f"Workstation ID: {ws_id}\n")
else:
    results_text.insert("end", f"Workstation ID: {ws_id}\n")
```

- [ ] **Step 5: Verify manually and run existing tests**

Run: `pytest tests/ -v`
Expected: All existing tests still PASS

Manually: Open app, go to Detection Settings, verify checkbox appears and preview works.

- [ ] **Step 6: Commit**

```bash
git add gk_install_builder/dialogs/detection_settings.py
git commit -m "feat: add WSID zero stripping checkbox and preview in Detection Settings"
```

---

### Task 4: Full integration verification and cleanup

**Goal:** Verify end-to-end that all pieces work together — config persistence, generation, and UI.

**Files:**
- Verify: All modified files
- Cleanup: `PRD-wsid-leading-zero-stripping.md` (move or delete if desired)

**Acceptance Criteria:**
- [ ] All 187+ tests pass (existing + new)
- [ ] Generated PS1 with stripping enabled contains the conversion line in correct position
- [ ] Generated Bash with stripping enabled contains the conversion line in correct position
- [ ] Config round-trips correctly (save → load → setting preserved)

**Verify:** `pytest tests/ -v` → all PASS

**Steps:**

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Manual smoke test**

1. Run `python -m gk_install_builder.main`
2. Open Detection Settings
3. Enable "Remove leading zeros from Workstation ID"
4. Test with hostname `1234-001` — verify preview shows `001 → 1`
5. Generate a Windows package — verify `[string][int]$workstationId` in GKInstall.ps1
6. Generate a Linux package — verify `workstationId=$(( 10#$workstationId ))` in GKInstall.sh
7. Close and reopen app — verify checkbox state persisted

- [ ] **Step 3: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "feat: complete WSID leading zero stripping feature"
```
