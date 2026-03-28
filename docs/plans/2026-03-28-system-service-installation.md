# System Service Installation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow Tomcat-based components (WDM, Flow, LPA, StoreHub, RCS) to be installed as Windows/Linux system services by passing CLI arguments to the Launcher executable.

**Architecture:** Per-component service settings are stored in the existing `{component}_launcher_settings` config dict. At generation time, `gk_install_generator.py` reads these settings and injects CLI argument strings into the GKInstall templates. The Launcher.exe/Launcher.run receives `--runAsService 1 --appServiceName ... --updaterServiceName ... --runAsServiceStartType ...` as CLI arguments alongside the existing `--defaultsFile` and `--mode unattended` args.

**Tech Stack:** Python 3.7+, CustomTkinter, `@VARIABLE@` template replacement

**Design doc:** `docs/plans/2026-03-28-system-service-installation-design.md`

---

### Task 1: Create feature branch

**Step 1: Create and switch to feature branch**

```bash
cd D:/Projects/Store-Install-Builder
git checkout -b feature/system-services
```

---

### Task 2: Add service section to Launcher Settings dialog

**Files:**
- Modify: `gk_install_builder/dialogs/launcher_settings.py`

**Step 1: Add service parameters to `parameter_labels` dict (line ~27)**

Add these entries to the `self.parameter_labels` dict in `__init__`:

```python
"runAsService": "Install as System Service",
"appServiceName": "Application Service Name",
"updaterServiceName": "Updater Service Name",
"runAsServiceStartType": "Service Start Type (Windows only)",
```

**Step 2: Add service tooltips to `parameter_tooltips` dict (line ~44)**

Add these entries to the `self.parameter_tooltips` dict in `__init__`:

```python
"runAsService": "Register the application as a system service. Requires running GKInstall as Administrator (Windows) or root (Linux).",
"appServiceName": "Name of the Windows/Linux service for the application server",
"updaterServiceName": "Name of the Windows/Linux service for the updater",
"runAsServiceStartType": "Windows only. 'auto' starts the service on boot, 'manual' requires manual start.",
```

**Step 3: Add service defaults to Tomcat component settings in `load_default_settings` (line ~239)**

For each Tomcat-based component (WDM, FLOW-SERVICE, LPA-SERVICE, STOREHUB-SERVICE, RCS-SERVICE), add service keys to the settings dict. Insert them at the **beginning** of each dict so they appear at the top of the tab. The short names are: `wdm`, `flow`, `lpa`, `sh`, `rcs`.

For WDM (modify the existing `self.settings["WDM"]` dict):
```python
self.settings["WDM"] = {
    "runAsService": "0",
    "appServiceName": "Tomcat-wdm",
    "updaterServiceName": "Updater-wdm",
    "runAsServiceStartType": "auto",
    "applicationServerHttpPort": "8080",
    "applicationServerHttpsPort": "8443",
    "applicationServerShutdownPort": "8005",
    "applicationServerJmxPort": "52222",
    "updaterJmxPort": "4333",
    "keepFiles": "0"
}
```

For FLOW-SERVICE:
```python
self.settings["FLOW-SERVICE"] = {
    "runAsService": "0",
    "appServiceName": "Tomcat-flow",
    "updaterServiceName": "Updater-flow",
    "runAsServiceStartType": "auto",
    "applicationServerHttpPort": "8180",
    "applicationServerHttpsPort": "8543",
    "applicationServerShutdownPort": "8005",
    "applicationServerJmxPort": "52222",
    "updaterJmxPort": "4333",
    "keepFiles": "0"
}
```

For LPA-SERVICE:
```python
self.settings["LPA-SERVICE"] = {
    "runAsService": "0",
    "appServiceName": "Tomcat-lpa",
    "updaterServiceName": "Updater-lpa",
    "runAsServiceStartType": "auto",
    "applicationServerHttpPort": "8180",
    "applicationServerHttpsPort": "8543",
    "applicationServerShutdownPort": "8005",
    "applicationServerJmxPort": "52222",
    "updaterJmxPort": "4333",
    "keepFiles": "0"
}
```

For STOREHUB-SERVICE (insert at the beginning, before existing Firebird keys):
```python
self.settings["STOREHUB-SERVICE"] = {
    "runAsService": "0",
    "appServiceName": "Tomcat-sh",
    "updaterServiceName": "Updater-sh",
    "runAsServiceStartType": "auto",
    "applicationServerHttpPort": "8180",
    "applicationServerHttpsPort": "8543",
    "applicationServerShutdownPort": "8005",
    "applicationServerJmxPort": "52222",
    "applicationJmsPort": "7001",
    "updaterJmxPort": "4333",
    "firebirdServerPath": firebird_path,
    "firebirdServerPort": "3050",
    "firebirdServerUser": "SYSDBA",
    "firebirdServerPassword": "masterkey",
    "keepFiles": "0"
}
```

For RCS-SERVICE:
```python
self.settings["RCS-SERVICE"] = {
    "runAsService": "0",
    "appServiceName": "Tomcat-rcs",
    "updaterServiceName": "Updater-rcs",
    "runAsServiceStartType": "auto",
    "applicationServerHttpPort": "8180",
    "applicationServerHttpsPort": "8543",
    "applicationServerShutdownPort": "8005",
    "applicationServerJmxPort": "52222",
    "updaterJmxPort": "4333",
    "keepFiles": "0"
}
```

**Step 4: Add admin warning in the tab rendering loop**

In the `open_editor` method, inside the `for component_type in component_types:` loop (line ~101), after the instructions label and before the scrollable frame, add a conditional admin warning for Tomcat-based components:

```python
# Add service admin warning for Tomcat-based components
tomcat_components = ["WDM", "FLOW-SERVICE", "LPA-SERVICE", "STOREHUB-SERVICE", "RCS-SERVICE"]
if component_type in tomcat_components:
    warning_label = ctk.CTkLabel(
        settings_frame,
        text="Note: 'Install as System Service' requires running GKInstall as Administrator (Windows) or root (Linux).",
        wraplength=700,
        text_color="orange"
    )
    warning_label.pack(pady=(0, 5), padx=10, anchor="w")
```

**Step 5: Use dropdown for runAsServiceStartType instead of text entry**

In the tab rendering loop where entries are created (line ~124), add special handling for `runAsServiceStartType` to render a dropdown instead of a text entry, and for `runAsService` to render a dropdown with `0`/`1` values:

Replace the entry creation block inside the `for key, value in self.settings[component_type].items():` loop with:

```python
for key, value in self.settings[component_type].items():
    frame = ctk.CTkFrame(scrollable_settings, fg_color="transparent")
    frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
    frame.grid_columnconfigure(1, weight=1)

    display_label = self.parameter_labels.get(key, key)
    label = ctk.CTkLabel(frame, text=display_label, width=250, anchor="w")
    label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

    if key == "runAsService":
        entry = ctk.CTkComboBox(frame, width=400, values=["0", "1"], state="readonly")
        entry.set(value)
    elif key == "runAsServiceStartType":
        entry = ctk.CTkComboBox(frame, width=400, values=["auto", "manual"], state="readonly")
        entry.set(value)
    else:
        entry = ctk.CTkEntry(frame, width=400)
        entry.insert(0, value)

    entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

    if key in self.parameter_tooltips:
        create_tooltip(label, self.parameter_tooltips[key], parent_window=self.window)
        create_tooltip(entry, self.parameter_tooltips[key], parent_window=self.window)

    self.settings[component_type][key] = {"value": value, "entry": entry}

    row += 1
```

**Step 6: Update `save_settings` to handle ComboBox widgets**

In the `save_settings` method (line ~356), the entry reading already uses `item["entry"].get()` which works for both `CTkEntry` and `CTkComboBox`. No change needed here.

**Step 7: Test the dialog manually**

Run: `cd D:/Projects/Store-Install-Builder && python -m gk_install_builder.main`
- Open Launcher Settings dialog
- Verify WDM/Flow/LPA/StoreHub/RCS tabs show service fields at the top
- Verify POS/ONEX-POS tabs do NOT show service fields
- Verify dropdowns work for runAsService and runAsServiceStartType
- Verify orange admin warning appears on Tomcat tabs
- Save settings, reopen dialog, verify values persist

**Step 8: Commit**

```bash
git add gk_install_builder/dialogs/launcher_settings.py
git commit -m "feat: add service installation settings to Launcher Settings dialog"
```

---

### Task 3: Modify GKInstall.ps1.template — inject service args

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template`

**Step 1: Add service args variable before the Launcher invocation (line ~2412)**

Replace lines 2412-2430:

```
# Start Launcher with appropriate arguments for new installation or update
if ($isUpdate) {
    Write-Host "================================================================="
    Write-Host "                     RUNNING IN UPDATE MODE                      " -ForegroundColor Cyan
    Write-Host "================================================================="
    $launchArgs = @(
        "--mode", "unattended",
        "--forceDownload", "false",
        "--station.applicationVersion", $component_version,
        "--station.propertiesPath", $install_dir
    )
    Write-Host "Running Launcher with update arguments: $($launchArgs -join ' ')"
    $launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList $launchArgs -PassThru
} else {
    Write-Host "================================================================="
    Write-Host "                 RUNNING IN FULL INSTALLATION MODE               " -ForegroundColor Green
    Write-Host "================================================================="
    $launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList "--defaultsFile", "launcher.properties", "--mode", "unattended" -PassThru
}
```

With:

```
# Service installation arguments (injected by generator)
$serviceArgs = @()
@SERVICE_ARGS_PS@

# Start Launcher with appropriate arguments for new installation or update
if ($isUpdate) {
    Write-Host "================================================================="
    Write-Host "                     RUNNING IN UPDATE MODE                      " -ForegroundColor Cyan
    Write-Host "================================================================="
    $launchArgs = @(
        "--mode", "unattended",
        "--forceDownload", "false",
        "--station.applicationVersion", $component_version,
        "--station.propertiesPath", $install_dir
    )
    Write-Host "Running Launcher with update arguments: $($launchArgs -join ' ')"
    $launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList $launchArgs -PassThru
} else {
    Write-Host "================================================================="
    Write-Host "                 RUNNING IN FULL INSTALLATION MODE               " -ForegroundColor Green
    Write-Host "================================================================="
    $installArgs = @("--defaultsFile", "launcher.properties", "--mode", "unattended") + $serviceArgs
    if ($serviceArgs.Count -gt 0) {
        Write-Host "Service installation enabled: $($serviceArgs -join ' ')" -ForegroundColor Yellow
    }
    $launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList $installArgs -PassThru
}
```

**Step 2: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template
git commit -m "feat: add @SERVICE_ARGS_PS@ token to PowerShell template"
```

---

### Task 4: Modify GKInstall.sh.template — inject service args

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.sh.template`

**Step 1: Add service args variable before the Launcher invocation (line ~2878)**

Replace lines 2878-2892:

```
# Start Launcher based on whether this is an update or new installation
if [ "$isUpdate" = true ]; then
    echo -e "\033[1;36m=================================================================\033[0m"
    echo -e "\033[1;36m                     RUNNING IN UPDATE MODE                      \033[0m"
    echo -e "\033[1;36m=================================================================\033[0m"
    echo "Running Launcher with update arguments: --mode unattended --forceDownload false --station.applicationVersion $component_version --station.propertiesPath $install_dir"
    ./Launcher.run --mode unattended --forceDownload false --station.applicationVersion "$component_version" --station.propertiesPath "$install_dir" &
    launcher_pid=$!
else
    echo -e "\033[1;32m=================================================================\033[0m"
    echo -e "\033[1;32m                 RUNNING IN FULL INSTALLATION MODE               \033[0m"
    echo -e "\033[1;32m=================================================================\033[0m"
    ./Launcher.run --defaultsFile launcher.properties --mode unattended &
    launcher_pid=$!
fi
```

With:

```
# Service installation arguments (injected by generator)
service_args=""
@SERVICE_ARGS_SH@

# Start Launcher based on whether this is an update or new installation
if [ "$isUpdate" = true ]; then
    echo -e "\033[1;36m=================================================================\033[0m"
    echo -e "\033[1;36m                     RUNNING IN UPDATE MODE                      \033[0m"
    echo -e "\033[1;36m=================================================================\033[0m"
    echo "Running Launcher with update arguments: --mode unattended --forceDownload false --station.applicationVersion $component_version --station.propertiesPath $install_dir"
    ./Launcher.run --mode unattended --forceDownload false --station.applicationVersion "$component_version" --station.propertiesPath "$install_dir" &
    launcher_pid=$!
else
    echo -e "\033[1;32m=================================================================\033[0m"
    echo -e "\033[1;32m                 RUNNING IN FULL INSTALLATION MODE               \033[0m"
    echo -e "\033[1;32m=================================================================\033[0m"
    if [ -n "$service_args" ]; then
        echo -e "\033[1;33mService installation enabled: $service_args\033[0m"
    fi
    ./Launcher.run --defaultsFile launcher.properties --mode unattended $service_args &
    launcher_pid=$!
fi
```

**Step 2: Commit**

```bash
git add gk_install_builder/templates/GKInstall.sh.template
git commit -m "feat: add @SERVICE_ARGS_SH@ token to Bash template"
```

---

### Task 5: Add service args generation to gk_install_generator.py

**Files:**
- Modify: `gk_install_builder/generators/gk_install_generator.py`

**Step 1: Add a helper function to build service CLI args**

Add this function before the `generate_gk_install` function (before line 18):

```python
# Mapping from GKInstall ComponentType to launcher settings config key
COMPONENT_SERVICE_CONFIG_MAP = {
    "WDM": "wdm_launcher_settings",
    "FLOW-SERVICE": "flow_service_launcher_settings",
    "LPA-SERVICE": "lpa_service_launcher_settings",
    "STOREHUB-SERVICE": "storehub_service_launcher_settings",
    "RCS-SERVICE": "rcs_service_launcher_settings",
}


def build_service_args(config, platform):
    """
    Build service CLI argument strings for the Launcher invocation.

    Reads per-component service settings from config and generates
    platform-specific argument strings for all Tomcat-based components.

    Args:
        config: Configuration dictionary
        platform: "Windows" or "Linux"

    Returns:
        dict with "ps" and "sh" keys containing the replacement strings
        for @SERVICE_ARGS_PS@ and @SERVICE_ARGS_SH@ tokens
    """
    ps_lines = []
    sh_lines = []

    for component_type, config_key in COMPONENT_SERVICE_CONFIG_MAP.items():
        settings = config.get(config_key, {})
        run_as_service = settings.get("runAsService", "0")

        if run_as_service != "1":
            continue

        app_service_name = settings.get("appServiceName", f"Tomcat-{component_type.lower().split('-')[0]}")
        updater_service_name = settings.get("updaterServiceName", f"Updater-{component_type.lower().split('-')[0]}")
        start_type = settings.get("runAsServiceStartType", "auto")

        # PowerShell: conditional block per component
        ps_lines.append(f'if ($ComponentType -eq \'{component_type}\') {{')
        ps_lines.append(f'    $serviceArgs = @("--runAsService", "1", "--appServiceName", "{app_service_name}", "--updaterServiceName", "{updater_service_name}", "--runAsServiceStartType", "{start_type}")')
        ps_lines.append(f'}}')

        # Bash: conditional block per component (no runAsServiceStartType — Windows only)
        sh_lines.append(f'if [ "$ComponentType" = "{component_type}" ]; then')
        sh_lines.append(f'    service_args="--runAsService 1 --appServiceName {app_service_name} --updaterServiceName {updater_service_name}"')
        sh_lines.append(f'fi')

    return {
        "ps": "\n".join(ps_lines),
        "sh": "\n".join(sh_lines),
    }
```

**Step 2: Call build_service_args and add the token replacements**

In `generate_gk_install`, after the existing replacements are applied (after line ~294, the `@REMOVE_OVERRIDES_AFTER_INSTALL@` replacement), add:

```python
        # Replace service args tokens
        service_args = build_service_args(config, platform)
        if platform == "Windows":
            template = template.replace("@SERVICE_ARGS_PS@", service_args["ps"])
        else:
            template = template.replace("@SERVICE_ARGS_SH@", service_args["sh"])
```

**Step 3: Test generation manually**

Run the application, enable service for WDM in Launcher Settings, generate, and check the output GKInstall.ps1/sh contains the correct service args block.

**Step 4: Commit**

```bash
git add gk_install_builder/generators/gk_install_generator.py
git commit -m "feat: generate service CLI args for Launcher invocation"
```

---

### Task 6: Add unit tests

**Files:**
- Modify or create: `tests/unit/test_service_installation.py`

**Step 1: Create test file**

```python
"""Tests for system service installation feature"""
import pytest

# Import with fallback for both package and direct execution
try:
    from gk_install_builder.generators.gk_install_generator import build_service_args
except ImportError:
    from generators.gk_install_generator import build_service_args


class TestBuildServiceArgs:
    """Tests for build_service_args function"""

    def test_no_service_enabled_returns_empty(self):
        """When no component has runAsService=1, output is empty"""
        config = {
            "wdm_launcher_settings": {"runAsService": "0"},
            "flow_service_launcher_settings": {},
        }
        result = build_service_args(config, "Windows")
        assert result["ps"] == ""
        assert result["sh"] == ""

    def test_wdm_service_enabled_powershell(self):
        """WDM with service enabled generates correct PS block"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            }
        }
        result = build_service_args(config, "Windows")
        assert "if ($ComponentType -eq 'WDM')" in result["ps"]
        assert '"--runAsService", "1"' in result["ps"]
        assert '"--appServiceName", "Tomcat-wdm"' in result["ps"]
        assert '"--updaterServiceName", "Updater-wdm"' in result["ps"]
        assert '"--runAsServiceStartType", "auto"' in result["ps"]

    def test_wdm_service_enabled_bash(self):
        """WDM with service enabled generates correct Bash block (no startType)"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            }
        }
        result = build_service_args(config, "Linux")
        assert 'if [ "$ComponentType" = "WDM" ]' in result["sh"]
        assert "--runAsService 1" in result["sh"]
        assert "--appServiceName Tomcat-wdm" in result["sh"]
        assert "--updaterServiceName Updater-wdm" in result["sh"]
        assert "runAsServiceStartType" not in result["sh"]

    def test_multiple_services_enabled(self):
        """Multiple components with service enabled generates blocks for each"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            },
            "rcs_service_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-rcs",
                "updaterServiceName": "Updater-rcs",
                "runAsServiceStartType": "manual",
            },
        }
        result = build_service_args(config, "Windows")
        assert "WDM" in result["ps"]
        assert "RCS-SERVICE" in result["ps"]
        assert '"--runAsServiceStartType", "manual"' in result["ps"]

    def test_service_disabled_not_included(self):
        """Component with runAsService=0 is not included"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            },
            "flow_service_launcher_settings": {
                "runAsService": "0",
            },
        }
        result = build_service_args(config, "Windows")
        assert "WDM" in result["ps"]
        assert "FLOW-SERVICE" not in result["ps"]

    def test_missing_settings_uses_defaults(self):
        """Missing service name settings fall back to defaults"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
            }
        }
        result = build_service_args(config, "Windows")
        assert "Tomcat-wdm" in result["ps"]
        assert "Updater-wdm" in result["ps"]

    def test_empty_config_returns_empty(self):
        """Empty config returns empty strings"""
        result = build_service_args({}, "Windows")
        assert result["ps"] == ""
        assert result["sh"] == ""
```

**Step 2: Run tests**

```bash
cd D:/Projects/Store-Install-Builder
pytest tests/unit/test_service_installation.py -v
```

Expected: All 7 tests pass.

**Step 3: Run full test suite to verify no regressions**

```bash
pytest tests/ -v
```

Expected: All existing 187+ tests pass.

**Step 4: Commit**

```bash
git add tests/unit/test_service_installation.py
git commit -m "test: add unit tests for service installation feature"
```

---

### Task 7: Final integration test and cleanup

**Step 1: Manual end-to-end test**

1. Run the application: `python -m gk_install_builder.main`
2. Open Launcher Settings, enable service for WDM with default names
3. Generate installation package for Windows
4. Open generated `GKInstall.ps1` and verify:
   - `$serviceArgs = @()` line exists
   - Conditional block for WDM with correct args
   - Launcher invocation uses `$installArgs` combining defaults + service args
5. Generate for Linux and verify `GKInstall.sh` similarly
6. Disable service for WDM, regenerate, verify `$serviceArgs` stays empty and Launcher command is unchanged

**Step 2: Commit any final fixes if needed**

```bash
git add -A
git commit -m "feat: system service installation feature complete"
```
