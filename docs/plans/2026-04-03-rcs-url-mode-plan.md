# RCS URL Mode (Hostname vs IP) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add radio buttons to choose between hostname and IP address for the RCS URL in system.properties, with HTTPS disabled when IP is selected.

**Architecture:** New config flag `rcs_url_mode` drives a placeholder `@RCS_URL_MODE@` that conditionally resolves hostname or IP (via default-gateway adapter) at runtime in the store-initialization templates. GUI enforces HTTPS/IP mutual exclusion.

**Tech Stack:** Python/CustomTkinter (GUI), PowerShell/Bash (templates), pytest (tests)

**Design doc:** `docs/plans/2026-04-03-rcs-url-mode-design.md`

---

### Task 1: Add config default

**Files:**
- Modify: `gk_install_builder/config.py:136`

**Step 1: Add the new config key**

In `_get_default_config()`, add after line 136 (`"rcs_skip_url_config": False`):

```python
            "rcs_url_mode": "hostname",  # RCS URL resolution mode: "hostname" or "ip" (IP disables HTTPS)
```

**Step 2: Run existing tests to verify no breakage**

Run: `pytest tests/ -x -q`
Expected: All 187 tests pass

**Step 3: Commit**

```
feat: add rcs_url_mode config default
```

---

### Task 2: Add radio buttons and HTTPS interlock to GUI

**Files:**
- Modify: `gk_install_builder/dialogs/launcher_settings.py:174-218`

**Step 1: Add radio buttons before the HTTPS checkbox**

Replace the RCS-SERVICE block (lines 174-218) with radio buttons + interlinked HTTPS checkbox. The radio buttons go after the separator, before the HTTPS checkbox. Key behavior:
- `rcs_url_mode_var` StringVar, values `"hostname"` / `"ip"`, loaded from config
- When "IP Address" selected: uncheck and disable HTTPS checkbox
- When "Hostname" selected: re-enable HTTPS checkbox
- Store reference to HTTPS checkbox as `self.rcs_https_cb` so the callback can configure it

```python
            # Add RCS URL mode and HTTPS options to the RCS-SERVICE tab
            if component_type == "RCS-SERVICE":
                separator = ctk.CTkFrame(scrollable_settings, height=2, fg_color="gray50")
                separator.grid(row=row, column=0, sticky="ew", padx=5, pady=10)
                row += 1

                # RCS URL Mode radio buttons
                mode_label = ctk.CTkLabel(scrollable_settings, text="RCS URL Mode:", anchor="w")
                mode_label.grid(row=row, column=0, sticky="w", padx=10, pady=(5, 0))
                row += 1

                mode_frame = ctk.CTkFrame(scrollable_settings, fg_color="transparent")
                mode_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)

                self.rcs_url_mode_var = ctk.StringVar(
                    value=self.config_manager.config.get("rcs_url_mode", "hostname")
                )

                hostname_rb = ctk.CTkRadioButton(
                    mode_frame,
                    text="Hostname",
                    variable=self.rcs_url_mode_var,
                    value="hostname",
                    command=self._on_rcs_url_mode_changed
                )
                hostname_rb.pack(side="left", padx=10, pady=5)
                create_tooltip(hostname_rb,
                    "Use the machine's hostname for the RCS service URL.\n"
                    "Example: http://STORE-PC-01:8180/rcs",
                    parent_window=self.window)

                ip_rb = ctk.CTkRadioButton(
                    mode_frame,
                    text="IP Address",
                    variable=self.rcs_url_mode_var,
                    value="ip",
                    command=self._on_rcs_url_mode_changed
                )
                ip_rb.pack(side="left", padx=10, pady=5)
                create_tooltip(ip_rb,
                    "Use the machine's IP address (from the default gateway adapter)\n"
                    "for the RCS service URL. HTTPS is not available in this mode.\n"
                    "Example: http://10.63.2.215:8180/rcs",
                    parent_window=self.window)

                row += 1

                # HTTPS checkbox
                https_frame = ctk.CTkFrame(scrollable_settings, fg_color="transparent")
                https_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)

                self.rcs_use_https_var = ctk.BooleanVar(
                    value=self.config_manager.config.get("rcs_use_https", False)
                )
                self.rcs_https_cb = ctk.CTkCheckBox(
                    https_frame,
                    text="Use HTTPS for RCS URL",
                    variable=self.rcs_use_https_var,
                    onvalue=True, offvalue=False
                )
                self.rcs_https_cb.pack(side="left", padx=10, pady=5)
                create_tooltip(self.rcs_https_cb,
                    "Use HTTPS protocol and HTTPS port for the RCS service URL.\n"
                    "When enabled, the store-initialization script will configure\n"
                    "RCS with https://<hostname>:<httpsPort>/rcs instead of\n"
                    "http://<hostname>:<httpPort>/rcs.\n"
                    "Not available when using IP Address mode.",
                    parent_window=self.window)

                # Apply initial state (disable HTTPS if IP mode)
                self._on_rcs_url_mode_changed()

                # Skip URL checkbox
                skip_url_frame = ctk.CTkFrame(scrollable_settings, fg_color="transparent")
                skip_url_frame.grid(row=row + 1, column=0, sticky="ew", padx=5, pady=5)

                self.rcs_skip_url_var = ctk.BooleanVar(
                    value=self.config_manager.config.get("rcs_skip_url_config", False)
                )
                rcs_skip_url_cb = ctk.CTkCheckBox(
                    skip_url_frame,
                    text="Don't set RCS URL",
                    variable=self.rcs_skip_url_var,
                    onvalue=True, offvalue=False
                )
                rcs_skip_url_cb.pack(side="left", padx=10, pady=5)
                create_tooltip(rcs_skip_url_cb,
                    "Skip setting the RCS URL during store initialization.\n"
                    "When enabled, the store-initialization script will not\n"
                    "make the API call to configure the rcs.url property\n"
                    "in Config-Service.",
                    parent_window=self.window)
```

**Step 2: Add the callback method**

Add this method to the `LauncherSettingsDialog` class (before `save_settings`):

```python
    def _on_rcs_url_mode_changed(self):
        """Handle RCS URL mode radio button change - disable HTTPS when IP is selected"""
        if self.rcs_url_mode_var.get() == "ip":
            self.rcs_use_https_var.set(False)
            self.rcs_https_cb.configure(state="disabled")
        else:
            self.rcs_https_cb.configure(state="normal")
```

**Step 3: Save the new value in save_settings**

Find the `save_settings` method. It already saves `rcs_use_https` and `rcs_skip_url_config`. Add saving `rcs_url_mode` alongside them:

```python
        self.config_manager.config["rcs_url_mode"] = self.rcs_url_mode_var.get()
```

**Step 4: Run existing tests**

Run: `pytest tests/ -x -q`
Expected: All tests pass

**Step 5: Commit**

```
feat: add RCS URL mode radio buttons with HTTPS interlock
```

---

### Task 3: Add placeholder replacement in generator

**Files:**
- Modify: `gk_install_builder/generators/helper_file_generator.py:104-118`

**Step 1: Add URL mode placeholder and IP-forces-HTTP logic**

Replace lines 104-118 with:

```python
        # Add RCS URL mode
        rcs_url_mode = config.get("rcs_url_mode", "hostname")
        template_content = template_content.replace("@RCS_URL_MODE@", rcs_url_mode)

        # Add RCS protocol and port from launcher settings
        rcs_launcher_settings = config.get("rcs_service_launcher_settings", {})
        rcs_use_https = config.get("rcs_use_https", False)
        # IP mode forces HTTP (no valid certificate for raw IP addresses)
        if rcs_url_mode == "ip":
            rcs_use_https = False
        if rcs_use_https:
            rcs_protocol = "https"
            rcs_port = rcs_launcher_settings.get("applicationServerHttpsPort", "8543")
        else:
            rcs_protocol = "http"
            rcs_port = rcs_launcher_settings.get("applicationServerHttpPort", "8180")
        template_content = template_content.replace("@RCS_PROTOCOL@", rcs_protocol)
        template_content = template_content.replace("@RCS_PORT@", rcs_port)

        # Add RCS skip URL config flag
        rcs_skip_url = config.get("rcs_skip_url_config", False)
        template_content = template_content.replace("@RCS_SKIP_URL_CONFIG@", "true" if rcs_skip_url else "false")
```

**Step 2: Run existing tests**

Run: `pytest tests/ -x -q`
Expected: All tests pass

**Step 3: Commit**

```
feat: add RCS URL mode placeholder replacement in generator
```

---

### Task 4: Update PowerShell store-initialization template

**Files:**
- Modify: `gk_install_builder/templates/store-initialization.ps1.template:538-554`

**Step 1: Replace hostname resolution + URL construction**

Replace lines 538-554 with:

```powershell
                    # Resolve host identifier based on URL mode
                    $rcsUrlMode = "@RCS_URL_MODE@"
                    if ($rcsUrlMode -eq "ip") {
                        # Get IP address from the adapter with default gateway
                        $hostIdentifier = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway }) | 
                            Select-Object -First 1 | 
                            ForEach-Object { $_.IPv4Address.IPAddress }
                        if ([string]::IsNullOrEmpty($hostIdentifier)) {
                            Write-Host "Warning: Could not detect IP address from default gateway adapter, falling back to hostname" -ForegroundColor Yellow
                            $hostIdentifier = $env:COMPUTERNAME
                        } else {
                            Write-Host "Detected IP address from default gateway adapter: $hostIdentifier" -ForegroundColor Green
                        }
                    } else {
                        # Use hostname (default)
                        $hostIdentifier = $env:COMPUTERNAME
                        if ([string]::IsNullOrEmpty($hostIdentifier)) {
                            $hostIdentifier = "localhost"
                        }
                    }

                    # Get version from parameter or fallback to config
                    if (-Not [string]::IsNullOrEmpty($Version)) {
                        $version = $Version
                        Write-Host "Using dynamic version from parameter: $version"
                    } else {
                        $version = "@RCS_VERSION@"
                        Write-Host "Using fallback version from config: $version"
                    }

                    # Build the RCS URL
                    $rcsUrl = "@RCS_PROTOCOL@://${hostIdentifier}:@RCS_PORT@/rcs"
```

**Step 2: Commit**

```
feat: add IP address detection to PowerShell store-initialization template
```

---

### Task 5: Update Bash store-initialization template

**Files:**
- Modify: `gk_install_builder/templates/store-initialization.sh.template:673-687`

**Step 1: Replace hostname resolution + URL construction**

Replace lines 673-687 with:

```bash
        # Resolve host identifier based on URL mode
        rcs_url_mode="@RCS_URL_MODE@"
        if [ "$rcs_url_mode" = "ip" ]; then
          # Get IP address from the adapter with default gateway
          host_identifier=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')
          if [ -z "$host_identifier" ]; then
            # Fallback: first non-loopback IP
            host_identifier=$(hostname -I 2>/dev/null | awk '{print $1}')
          fi
          if [ -z "$host_identifier" ]; then
            echo "Warning: Could not detect IP address from default gateway adapter, falling back to hostname"
            host_identifier=$(hostname 2>/dev/null || echo "localhost")
          else
            echo "Detected IP address from default gateway adapter: $host_identifier"
          fi
        else
          # Use hostname (default)
          host_identifier=$(hostname 2>/dev/null || echo "localhost")
        fi

        # Get version from parameter or fallback to config
        if [ -n "$VERSION" ]; then
          version="$VERSION"
          echo "Using dynamic version from parameter: $version"
        else
          version="@RCS_VERSION@"
          echo "Using fallback version from config: $version"
        fi

        # Build the RCS URL
        rcs_url="@RCS_PROTOCOL@://${host_identifier}:@RCS_PORT@/rcs"
```

**Step 2: Commit**

```
feat: add IP address detection to Bash store-initialization template
```

---

### Task 6: Add tests

**Files:**
- Create: `tests/unit/test_rcs_url_mode.py`

**Step 1: Write tests**

```python
"""Tests for RCS URL mode (hostname vs IP) feature"""

import pytest
from tests.fixtures.generator_fixtures import create_config


class TestRcsUrlModeConfig:
    """Test config defaults for rcs_url_mode"""

    def test_default_config_has_rcs_url_mode(self):
        """rcs_url_mode should default to 'hostname'"""
        from gk_install_builder.config import ConfigManager
        cm = ConfigManager.__new__(ConfigManager)
        defaults = cm._get_default_config()
        assert defaults["rcs_url_mode"] == "hostname"


class TestRcsUrlModeGenerator:
    """Test helper_file_generator handles rcs_url_mode correctly"""

    def test_hostname_mode_placeholder(self, tmp_path):
        """@RCS_URL_MODE@ should be replaced with 'hostname'"""
        from gk_install_builder.generators.helper_file_generator import process_store_initialization
        template = tmp_path / "store-initialization.ps1.template"
        template.write_text("mode=@RCS_URL_MODE@ proto=@RCS_PROTOCOL@ port=@RCS_PORT@ skip=@RCS_SKIP_URL_CONFIG@ ver=@VERSION@")
        config = create_config(rcs_url_mode="hostname", rcs_use_https=False)
        result = process_store_initialization(str(template), config)
        assert "mode=hostname" in result

    def test_ip_mode_placeholder(self, tmp_path):
        """@RCS_URL_MODE@ should be replaced with 'ip'"""
        from gk_install_builder.generators.helper_file_generator import process_store_initialization
        template = tmp_path / "store-initialization.ps1.template"
        template.write_text("mode=@RCS_URL_MODE@ proto=@RCS_PROTOCOL@ port=@RCS_PORT@ skip=@RCS_SKIP_URL_CONFIG@ ver=@VERSION@")
        config = create_config(rcs_url_mode="ip", rcs_use_https=False)
        result = process_store_initialization(str(template), config)
        assert "mode=ip" in result

    def test_ip_mode_forces_http(self, tmp_path):
        """When rcs_url_mode is 'ip', protocol must be HTTP even if rcs_use_https is True"""
        from gk_install_builder.generators.helper_file_generator import process_store_initialization
        template = tmp_path / "store-initialization.ps1.template"
        template.write_text("proto=@RCS_PROTOCOL@ port=@RCS_PORT@ mode=@RCS_URL_MODE@ skip=@RCS_SKIP_URL_CONFIG@ ver=@VERSION@")
        config = create_config(rcs_url_mode="ip", rcs_use_https=True)
        result = process_store_initialization(str(template), config)
        assert "proto=http" in result
        assert "port=8180" in result

    def test_hostname_mode_allows_https(self, tmp_path):
        """When rcs_url_mode is 'hostname', HTTPS should work normally"""
        from gk_install_builder.generators.helper_file_generator import process_store_initialization
        template = tmp_path / "store-initialization.ps1.template"
        template.write_text("proto=@RCS_PROTOCOL@ port=@RCS_PORT@ mode=@RCS_URL_MODE@ skip=@RCS_SKIP_URL_CONFIG@ ver=@VERSION@")
        config = create_config(rcs_url_mode="hostname", rcs_use_https=True)
        result = process_store_initialization(str(template), config)
        assert "proto=https" in result
        assert "port=8543" in result
```

**Step 2: Run the new tests**

Run: `pytest tests/unit/test_rcs_url_mode.py -v`
Expected: Tests may need adjustment based on the actual `process_store_initialization` function signature. Adapt imports and function calls to match the actual API.

**Step 3: Run all tests**

Run: `pytest tests/ -x -q`
Expected: All tests pass (187 + new tests)

**Step 4: Commit**

```
test: add tests for RCS URL mode feature
```

---

### Task 7: Final verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 2: Quick manual smoke test**

Run: `python -m gk_install_builder.main`
- Open Launcher Settings dialog
- Go to RCS-SERVICE tab
- Verify radio buttons appear (Hostname selected by default)
- Select "IP Address" -> HTTPS checkbox should grey out and uncheck
- Select "Hostname" -> HTTPS checkbox should re-enable
- Save and reopen -> selection should persist

**Step 3: Commit all (if any fixups needed)**

```
feat: RCS URL mode - hostname vs IP address selection
```
