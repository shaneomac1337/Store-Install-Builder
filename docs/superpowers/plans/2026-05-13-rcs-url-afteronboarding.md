# RCS URL afterOnboardingProperties Injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `--rcsUrl` is set, inject `afterOnboardingProperties: [{key: "rcs.url", value: <resolved>}]` into every non-RCS component's onboarding token request body.

**Architecture:** Resolve `rcsUrl` (autodetect or literal) BEFORE `onboarding.ps1`/`.sh` runs. Pass the resolved value as a new param. Onboarding scripts inject the field in-memory and POST. Disk JSON templates untouched. Existing `installationtoken.txt` append behavior preserved.

**Tech Stack:** PowerShell + Bash templates; Python generator; pytest.

**Spec:** [docs/superpowers/specs/2026-05-13-rcs-url-afteronboarding-design.md](../specs/2026-05-13-rcs-url-afteronboarding-design.md)

---

### Task 1: Onboarding.ps1 — accept `-rcsUrl` param and inject for non-RCS components

**Files:**
- Modify: `gk_install_builder/templates/onboarding.ps1.template` (param block at top, body assembly near line 166)
- Test: `tests/unit/test_rcs_afteronboarding.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_rcs_afteronboarding.py`:

```python
"""
Tests for afterOnboardingProperties injection in onboarding scripts.
"""
import os
import pytest
from gk_install_builder.generators.onboarding_generator import generate_onboarding_script
from tests.fixtures.generator_fixtures import create_config


def _setup_templates(tmp_path, platform="Windows"):
    """Copy the real onboarding templates into a temp dir for testing."""
    import shutil
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    src = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "gk_install_builder", "templates"
    )
    for fname in ("onboarding.ps1.template", "onboarding.sh.template"):
        shutil.copy(os.path.join(src, fname), templates_dir / fname)
    return str(templates_dir), str(output_dir)


def _read(output_dir, filename):
    with open(os.path.join(output_dir, filename), "r", encoding="utf-8") as f:
        return f.read()


class TestOnboardingPs1RcsUrlInjection:
    """Onboarding.ps1 must accept -rcsUrl and inject afterOnboardingProperties."""

    def test_ps1_has_rcsurl_param(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Windows")
        cfg = create_config(platform="Windows")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.ps1")
        assert '[string]$rcsUrl' in content, (
            "onboarding.ps1 must declare -rcsUrl parameter"
        )

    def test_ps1_injects_afteronboarding_for_non_rcs(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Windows")
        cfg = create_config(platform="Windows")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.ps1")
        assert 'afterOnboardingProperties' in content, (
            "onboarding.ps1 must inject afterOnboardingProperties when rcsUrl set"
        )
        assert 'RCS-SERVICE' in content and '-ne "RCS-SERVICE"' in content, (
            "Injection must be gated by ComponentType -ne RCS-SERVICE"
        )
        assert 'rcs.url' in content, (
            "Injection must reference rcs.url key"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestOnboardingPs1RcsUrlInjection -v`
Expected: 2 failures with assertion errors about missing `$rcsUrl` and `afterOnboardingProperties`.

- [ ] **Step 3: Modify onboarding.ps1.template — add param**

Edit `gk_install_builder/templates/onboarding.ps1.template`. Locate the `param(` block at the top (around line 1-9). Add `$rcsUrl` parameter:

```powershell
param(
    [string]$ComponentType = "POS",
    [string]$base_url = "test.cse.cloud4retail.co",
    [string]$tenant_id = "001",
    [string]$rcsUrl = ""
)
```

If the existing param block has different names/defaults, preserve them exactly and append `[string]$rcsUrl = ""` as the new last parameter.

- [ ] **Step 4: Modify onboarding.ps1.template — inject afterOnboardingProperties**

In `gk_install_builder/templates/onboarding.ps1.template`, locate the block (around line 165-168) that reads the JSON body:

```powershell
    # Read JSON from selected file
    $jsonPath = Join-Path $onboardingPath $jsonFile
    try {
        $body = Get-Content -Path $jsonPath -Raw
    }
```

Add the injection block immediately AFTER the `try { $body = Get-Content ... }` catch block. New code:

```powershell
    # Inject afterOnboardingProperties for non-RCS components when rcsUrl is provided
    if ($rcsUrl -and $ComponentType -ne "RCS-SERVICE") {
        try {
            $bodyObj = $body | ConvertFrom-Json
            $afterProps = @(@{ key = "rcs.url"; value = $rcsUrl })
            $bodyObj | Add-Member -NotePropertyName afterOnboardingProperties -NotePropertyValue $afterProps
            $body = $bodyObj | ConvertTo-Json -Depth 10
            Write-Host "Injected afterOnboardingProperties rcs.url=$rcsUrl into $ComponentType onboarding body"
        } catch {
            Write-Host "Warning: Failed to inject afterOnboardingProperties: $_"
            Write-Host "Continuing with original body"
        }
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestOnboardingPs1RcsUrlInjection -v`
Expected: 2 passes.

- [ ] **Step 6: Run full test suite to verify no regression**

Run: `pytest tests/ -v --tb=short`
Expected: All previously-passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add gk_install_builder/templates/onboarding.ps1.template tests/unit/test_rcs_afteronboarding.py
git commit -m "feat(rcs): onboarding.ps1 inject afterOnboardingProperties when rcsUrl set"
```

---

### Task 2: Onboarding.sh — accept `--rcsUrl` arg and inject for non-RCS components

**Files:**
- Modify: `gk_install_builder/templates/onboarding.sh.template` (arg parser at line 10-30, body assembly near line 242)
- Test: `tests/unit/test_rcs_afteronboarding.py` (add class)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_rcs_afteronboarding.py`:

```python
class TestOnboardingShRcsUrlInjection:
    """Onboarding.sh must accept --rcsUrl and inject afterOnboardingProperties."""

    def test_sh_has_rcsurl_arg(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        assert '--rcsUrl' in content, (
            "onboarding.sh must accept --rcsUrl argument"
        )
        assert 'rcs_url=' in content, (
            "onboarding.sh must initialise rcs_url variable"
        )

    def test_sh_injects_afteronboarding_for_non_rcs(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        assert 'afterOnboardingProperties' in content, (
            "onboarding.sh must inject afterOnboardingProperties"
        )
        assert 'RCS-SERVICE' in content and '!= "RCS-SERVICE"' in content, (
            "Injection must be gated by COMPONENT_TYPE != RCS-SERVICE"
        )
        # Both jq path and sed fallback present
        assert 'jq' in content and 'sed' in content, (
            "Both jq and sed fallback paths must be present"
        )

    def test_sh_sed_fallback_anchored_to_last_line(self, tmp_path):
        """Sed fallback must use $ line-address to avoid matching nested braces."""
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        assert "sed '$ s/}/" in content or 'sed "$ s/}/' in content, (
            "Sed fallback must be anchored to last line ($ address)"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestOnboardingShRcsUrlInjection -v`
Expected: 3 failures.

- [ ] **Step 3: Modify onboarding.sh.template — add arg + variable init**

Edit `gk_install_builder/templates/onboarding.sh.template`. Add `rcs_url=""` after line 7 (where `username="launchpad"` is set):

```bash
COMPONENT_TYPE="POS"
base_url="test.cse.cloud4retail.co"
tenant_id="001"
username="launchpad"
rcs_url=""
```

Add the `--rcsUrl` case to the argument parser (around line 23, before the `*)` catch-all):

```bash
    --rcsUrl)
      rcs_url="$2"
      shift 2
      ;;
```

Update the usage line in the `*)` catch-all to include `--rcsUrl`:

```bash
      echo "Usage: $0 [--ComponentType <POS|WDM|...>] [--base_url <url>] [--tenant_id <tenant_id>] [--rcsUrl <url>]"
```

- [ ] **Step 4: Modify onboarding.sh.template — inject afterOnboardingProperties**

Locate the body read (around line 242):

```bash
body=$(cat "$json_path")
```

Insert immediately after:

```bash
# Inject afterOnboardingProperties for non-RCS components when rcs_url is provided
if [ -n "$rcs_url" ] && [ "$COMPONENT_TYPE" != "RCS-SERVICE" ]; then
  if command -v jq >/dev/null 2>&1; then
    new_body=$(echo "$body" | jq --arg url "$rcs_url" \
      '. + {afterOnboardingProperties: [{key: "rcs.url", value: $url}]}' 2>/dev/null)
    if [ -n "$new_body" ]; then
      body="$new_body"
      echo "Injected afterOnboardingProperties rcs.url=$rcs_url (via jq)"
    else
      echo "Warning: jq failed; using original body for $COMPONENT_TYPE"
    fi
  else
    # Sed fallback anchored to last line only (avoids nested braces)
    new_body=$(echo "$body" | sed '$ s/}/,"afterOnboardingProperties":[{"key":"rcs.url","value":"'"$rcs_url"'"}]}/')
    body="$new_body"
    echo "Injected afterOnboardingProperties rcs.url=$rcs_url (via sed fallback)"
  fi
fi
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestOnboardingShRcsUrlInjection -v`
Expected: 3 passes.

- [ ] **Step 6: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add gk_install_builder/templates/onboarding.sh.template tests/unit/test_rcs_afteronboarding.py
git commit -m "feat(rcs): onboarding.sh inject afterOnboardingProperties when rcsUrl set"
```

---

### Task 3: GKInstall.ps1 — pre-acquire OAuth + relocate autodetect before onboarding call

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template`
  - Insert new block before line 1997 (the `.\onboarding.ps1` call)
  - Delete old autodetect block at lines 2144-2221
  - Update onboarding.ps1 invocation to pass `-rcsUrl $rcsUrl`
- Test: `tests/unit/test_rcs_afteronboarding.py` (add class)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_rcs_afteronboarding.py`:

```python
class TestGKInstallPs1RcsUrlPreOnboarding:
    """GKInstall.ps1 must resolve rcsUrl BEFORE onboarding.ps1 is invoked."""

    def _generate_ps1(self, tmp_path):
        """Generate GKInstall.ps1 via the real generator and return its content."""
        from gk_install_builder.generator import ProjectGenerator
        from unittest.mock import Mock
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        cfg = create_config(platform="Windows")
        gen = ProjectGenerator(cfg, output_dir=str(tmp_path))
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate()
        ps1_path = os.path.join(str(tmp_path), "GKInstall.ps1")
        with open(ps1_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_onboarding_call_passes_rcsurl(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        # The .\onboarding.ps1 invocation must include -rcsUrl $rcsUrl
        assert '.\\onboarding.ps1' in content
        assert '-rcsUrl $rcsUrl' in content, (
            "GKInstall.ps1 must pass -rcsUrl when calling onboarding.ps1"
        )

    def test_autodetect_runs_before_onboarding_call(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        autodetect_marker = "Autodetecting RCS URL from config-service"
        onboarding_marker = ".\\onboarding.ps1"
        a_idx = content.find(autodetect_marker)
        o_idx = content.find(onboarding_marker)
        assert a_idx >= 0, "Autodetect block not found"
        assert o_idx >= 0, "Onboarding invocation not found"
        assert a_idx < o_idx, (
            f"Autodetect block (idx={a_idx}) must appear BEFORE onboarding call (idx={o_idx})"
        )

    def test_autodetect_block_not_duplicated(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        marker = "Autodetecting RCS URL from config-service"
        assert content.count(marker) == 1, (
            f"Autodetect block must appear exactly once, found {content.count(marker)}"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestGKInstallPs1RcsUrlPreOnboarding -v`
Expected: failures — `-rcsUrl $rcsUrl` missing from call, autodetect block appears AFTER onboarding (idx ordering wrong).

- [ ] **Step 3: Modify GKInstall.ps1.template — update onboarding.ps1 invocation**

Locate the existing invocation at approximately line 1997:

```powershell
        .\onboarding.ps1 -ComponentType $ComponentType -base_url $base_url -tenant_id $tenantId
```

Replace with:

```powershell
        .\onboarding.ps1 -ComponentType $ComponentType -base_url $base_url -tenant_id $tenantId -rcsUrl $rcsUrl
```

- [ ] **Step 4: Modify GKInstall.ps1.template — insert pre-onboarding resolve block**

Locate the line above the onboarding call. Find the block `if (-not $isUpdate) {` (the wrapper around the onboarding invocation). Insert the resolve block AS THE FIRST CHILD of that `if (-not $isUpdate)` block (above the `.\onboarding.ps1` line):

```powershell
        # ---- Pre-acquire OAuth + resolve RCS URL (for afterOnboardingProperties injection) ----
        if ($rcsUrl) {
            try {
                $tokensPath = Join-Path $PSScriptRoot "helper\tokens"
                $basicAuthPath = Join-Path $tokensPath "basic_auth_password.txt"
                $formPasswordPath = Join-Path $tokensPath "form_password.txt"
                $formUsernamePath = Join-Path $tokensPath "form_username.txt"

                if ((Test-Path $basicAuthPath) -and (Test-Path $formPasswordPath) -and (Test-Path $formUsernamePath)) {
                    $basicAuthPassword = (Get-Content $basicAuthPath -Raw).Trim()
                    $formPassword = (Get-Content $formPasswordPath -Raw).Trim()
                    $formUsername = (Get-Content $formUsernamePath -Raw).Trim()

                    $base64Auth = [Convert]::ToBase64String(
                        [Text.Encoding]::ASCII.GetBytes("${username}:${basicAuthPassword}")
                    )
                    $oauthBody = @{
                        username   = $formUsername
                        password   = $formPassword
                        grant_type = "password"
                    }
                    $formData = ($oauthBody.GetEnumerator() | ForEach-Object {
                        "$([System.Net.WebUtility]::UrlEncode($_.Key))=$([System.Net.WebUtility]::UrlEncode($_.Value))"
                    }) -join '&'
                    $tokenUrl = "https://$base_url/auth-service/tenants/${tenantId}/oauth/token"
                    $oauthResponse = Invoke-RestMethod -Uri $tokenUrl -Method Post `
                        -Headers @{Authorization = "Basic $base64Auth"} `
                        -Body $formData -ContentType "application/x-www-form-urlencoded"
                    Set-Content -Path (Join-Path $tokensPath "access_token.txt") `
                        -Value $oauthResponse.access_token -NoNewline
                    Write-Host "Pre-acquired OAuth token for RCS URL resolution"
                }
            } catch {
                Write-Host "Warning: Pre-OAuth acquisition failed: $_"
            }

            if ($rcsUrl -eq "autodetect") {
                # ---- Autodetect block (moved from later in script) ----
                Write-Host "Autodetecting RCS URL from config-service..." -ForegroundColor Cyan
                $rcsUrl = ""
                try {
                    $tokenFile = Join-Path $PSScriptRoot "helper\tokens\access_token.txt"
                    if (Test-Path $tokenFile) {
                        $bearerToken = (Get-Content $tokenFile -Raw).Trim()
                        $rcsHeaders = @{
                            "authorization" = "Bearer $bearerToken"
                            "Content-Type"  = "application/json"
                        }
                        $childNodesUrl = "https://$server/api/config/services/rest/infrastructure/v1/structure/child-nodes/search"
                        $childNodesBody = @{
                            station = @{
                                systemName    = "GKR-Store"
                                tenantId      = $tenantId
                                retailStoreId = $storeNumber
                            }
                        } | ConvertTo-Json -Compress
                        Write-Host "Fetching store child nodes for store $storeNumber..."
                        $childNodesResponse = Invoke-RestMethod -Uri $childNodesUrl -Method Post `
                            -Headers $rcsHeaders -Body $childNodesBody -TimeoutSec 30
                        $rcsNode = $childNodesResponse.childNodeList |
                            Where-Object { $_.systemName -like "*Resource-Cache-Service*" } |
                            Select-Object -First 1
                        if ($rcsNode) {
                            Write-Host "Found RCS node: $($rcsNode.systemName) (version: $($rcsNode.activeVersion))"
                            $paramUrl = "https://$server/api/config/services/rest/config-management/v1/parameter-contents/plain/search"
                            $paramBody = @{
                                levelDescriptor  = @{ structureUniqueName = $rcsNode.structureUniqueName }
                                systemDescriptor = @{
                                    systemName        = $rcsNode.systemName
                                    systemVersionList = @(@{ name = $rcsNode.activeVersion })
                                }
                                parameterList    = @(@{ name = "system.properties" })
                            } | ConvertTo-Json -Depth 4 -Compress
                            Write-Host "Fetching RCS system.properties..."
                            $paramResponse = Invoke-RestMethod -Uri $paramUrl -Method Post `
                                -Headers $rcsHeaders -Body $paramBody `
                                -ContentType "application/json" -TimeoutSec 30
                            $propsParam = $paramResponse.parameterList |
                                Where-Object { $_.name -eq "system.properties" } |
                                Select-Object -First 1
                            if ($propsParam -and $propsParam.content) {
                                $propsContent = [System.Text.Encoding]::UTF8.GetString(
                                    [Convert]::FromBase64String($propsParam.content)
                                )
                                $rcsUrlMatch = [regex]::Match($propsContent, 'rcs\.url\s*=\s*(.+)')
                                if ($rcsUrlMatch.Success) {
                                    $rcsUrl = $rcsUrlMatch.Groups[1].Value.Trim() -replace '\\:', ':' -replace '\\=', '='
                                    Write-Host "Autodetected RCS URL: $rcsUrl" -ForegroundColor Green
                                } else {
                                    Write-Host "Warning: system.properties found but no rcs.url entry" -ForegroundColor Yellow
                                }
                            } else {
                                Write-Host "Warning: No system.properties content returned for RCS node" -ForegroundColor Yellow
                            }
                        } else {
                            Write-Host "Warning: No Resource-Cache-Service node found for store $storeNumber" -ForegroundColor Yellow
                        }
                    } else {
                        Write-Host "Warning: No access token available for RCS URL autodetect" -ForegroundColor Yellow
                    }
                } catch {
                    Write-Host "Warning: Failed to autodetect RCS URL: $_" -ForegroundColor Yellow
                }

                if ([string]::IsNullOrEmpty($rcsUrl)) {
                    Write-Host "RCS URL autodetection failed. Continue without rcs.url in installation token?" -ForegroundColor Yellow
                    $continue = Read-Host "Press Y to continue, any other key to abort"
                    if ($continue -ne "Y" -and $continue -ne "y") {
                        Write-Host "Aborted by user."
                        Stop-TranscriptSafely
                        exit 1
                    }
                }
            }
        }
        # ---- End pre-onboarding RCS URL resolution ----
```

- [ ] **Step 5: Delete the old autodetect block**

Locate the block currently at lines 2144-2221 starting with `# Resolve RCS URL if autodetect requested` and ending with the closing `}` of the `if ($rcsUrl -eq "autodetect")` block (the line above `# Append RCS URL to installation token if provided`). **Delete this entire block** since the logic moved up.

Keep the section that follows starting with `# Append RCS URL to installation token if provided` (the existing `if ($rcsUrl -and $rcsUrl -ne "autodetect")` append at lines 2223-2226) — that stays.

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestGKInstallPs1RcsUrlPreOnboarding -v`
Expected: 3 passes.

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template tests/unit/test_rcs_afteronboarding.py
git commit -m "feat(rcs): GKInstall.ps1 resolve rcsUrl before onboarding; pass -rcsUrl"
```

---

### Task 4: GKInstall.sh — pre-acquire OAuth + relocate autodetect before onboarding call

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.sh.template`
  - Insert new block before line 2428 (the `./onboarding.sh` call)
  - Delete old autodetect block at lines 2536-2620
  - Update onboarding.sh invocation to pass `--rcsUrl "$rcs_url"`
- Test: `tests/unit/test_rcs_afteronboarding.py` (add class)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_rcs_afteronboarding.py`:

```python
class TestGKInstallShRcsUrlPreOnboarding:
    """GKInstall.sh must resolve rcs_url BEFORE onboarding.sh is invoked."""

    def _generate_sh(self, tmp_path):
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        cfg = create_config(platform="Linux")
        gen = ProjectGenerator(cfg, output_dir=str(tmp_path))
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate()
        sh_path = os.path.join(str(tmp_path), "GKInstall.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_onboarding_call_passes_rcsurl(self, tmp_path):
        content = self._generate_sh(tmp_path)
        assert './onboarding.sh' in content
        assert '--rcsUrl "$rcs_url"' in content, (
            "GKInstall.sh must pass --rcsUrl when calling onboarding.sh"
        )

    def test_autodetect_runs_before_onboarding_call(self, tmp_path):
        content = self._generate_sh(tmp_path)
        autodetect_marker = "Autodetecting RCS URL from config-service"
        onboarding_marker = "./onboarding.sh"
        a_idx = content.find(autodetect_marker)
        o_idx = content.find(onboarding_marker)
        assert a_idx >= 0 and o_idx >= 0
        assert a_idx < o_idx, (
            f"Autodetect block (idx={a_idx}) must appear BEFORE onboarding call (idx={o_idx})"
        )

    def test_autodetect_block_not_duplicated(self, tmp_path):
        content = self._generate_sh(tmp_path)
        marker = "Autodetecting RCS URL from config-service"
        assert content.count(marker) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestGKInstallShRcsUrlPreOnboarding -v`
Expected: 3 failures.

- [ ] **Step 3: Modify GKInstall.sh.template — update onboarding.sh invocation**

Locate the existing invocation at approximately line 2428:

```bash
    if ! ./onboarding.sh --ComponentType "$COMPONENT_TYPE" --base_url "$base_url" --tenant_id "$tenant_id"; then
```

Replace with:

```bash
    if ! ./onboarding.sh --ComponentType "$COMPONENT_TYPE" --base_url "$base_url" --tenant_id "$tenant_id" --rcsUrl "$rcs_url"; then
```

- [ ] **Step 4: Modify GKInstall.sh.template — insert pre-onboarding resolve block**

Locate the `if [ "$isUpdate" = false ]; then` wrapper around the onboarding call (around line 2426). Insert the resolve block as the FIRST statement inside that block:

```bash
    # ---- Pre-acquire OAuth + resolve RCS URL (for afterOnboardingProperties injection) ----
    if [ -n "$rcs_url" ]; then
      tokens_path="$script_dir/helper/tokens"
      basic_auth_file="$tokens_path/basic_auth_password.txt"
      form_password_file="$tokens_path/form_password.txt"
      form_username_file="$tokens_path/form_username.txt"

      if [ -f "$basic_auth_file" ] && [ -f "$form_password_file" ] && [ -f "$form_username_file" ]; then
        basic_auth_password=$(cat "$basic_auth_file")
        form_password=$(cat "$form_password_file")
        form_username=$(cat "$form_username_file")
        auth_string=$(echo -n "$username:$basic_auth_password" | base64 | tr -d '\n')

        urlencode_pre() {
          local string="$1"
          local length="${#string}"
          local encoded=""
          local i char
          for (( i = 0; i < length; i++ )); do
            char="${string:i:1}"
            case "$char" in
              [a-zA-Z0-9.~_-]) encoded="$encoded$char" ;;
              *) encoded="$encoded$(printf '%%%02X' "'$char")" ;;
            esac
          done
          echo "$encoded"
        }

        username_enc=$(urlencode_pre "$form_username")
        password_enc=$(urlencode_pre "$form_password")
        token_url="https://$base_url/auth-service/tenants/$tenant_id/oauth/token"
        oauth_response=$(curl -s -X POST "$token_url" \
          -H "Authorization: Basic $auth_string" \
          -H "Content-Type: application/x-www-form-urlencoded" \
          --data "username=$username_enc&password=$password_enc&grant_type=password")
        if command -v jq >/dev/null 2>&1; then
          access_token_pre=$(echo "$oauth_response" | jq -r '.access_token // empty')
        else
          access_token_pre=$(echo "$oauth_response" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//;s/"$//')
        fi
        if [ -n "$access_token_pre" ]; then
          echo -n "$access_token_pre" > "$tokens_path/access_token.txt"
          echo "Pre-acquired OAuth token for RCS URL resolution"
        else
          echo "Warning: Pre-OAuth acquisition returned no token"
        fi
      fi

      if [ "$rcs_url" = "autodetect" ]; then
        # ---- Autodetect block (moved from later in script) ----
        echo "Autodetecting RCS URL from config-service..."
        rcs_url=""
        token_file="$script_dir/helper/tokens/access_token.txt"
        if [ -f "$token_file" ]; then
          bearer_token=$(cat "$token_file" | tr -d '\n\r')
          child_nodes_url="https://$server/api/config/services/rest/infrastructure/v1/structure/child-nodes/search"
          child_nodes_body=$(printf '{"station":{"systemName":"GKR-Store","tenantId":"%s","retailStoreId":"%s"}}' "$tenant_id" "$storeNumber")
          echo "Fetching store child nodes for store $storeNumber..."
          child_nodes_response=$(curl -s -X POST "$child_nodes_url" \
            -H "authorization: Bearer $bearer_token" \
            -H "Content-Type: application/json" \
            -d "$child_nodes_body")

          if command -v jq >/dev/null 2>&1; then
            rcs_struct=$(echo "$child_nodes_response" | jq -r '.childNodeList[]? | select(.systemName | test("Resource-Cache-Service")) | .structureUniqueName' | head -n 1)
            rcs_system=$(echo "$child_nodes_response" | jq -r '.childNodeList[]? | select(.systemName | test("Resource-Cache-Service")) | .systemName' | head -n 1)
            rcs_version=$(echo "$child_nodes_response" | jq -r '.childNodeList[]? | select(.systemName | test("Resource-Cache-Service")) | .activeVersion' | head -n 1)
          else
            # Minimal grep fallback (template shape stable)
            rcs_struct=$(echo "$child_nodes_response" | grep -o '"structureUniqueName":"[^"]*"' | head -n 1 | sed 's/"structureUniqueName":"//;s/"$//')
            rcs_system=$(echo "$child_nodes_response" | grep -o '"systemName":"[^"]*Resource-Cache-Service[^"]*"' | head -n 1 | sed 's/"systemName":"//;s/"$//')
            rcs_version=$(echo "$child_nodes_response" | grep -o '"activeVersion":"[^"]*"' | head -n 1 | sed 's/"activeVersion":"//;s/"$//')
          fi

          if [ -n "$rcs_system" ]; then
            echo "Found RCS node: $rcs_system (version: $rcs_version)"
            param_url="https://$server/api/config/services/rest/config-management/v1/parameter-contents/plain/search"
            param_body=$(printf '{"levelDescriptor":{"structureUniqueName":"%s"},"systemDescriptor":{"systemName":"%s","systemVersionList":[{"name":"%s"}]},"parameterList":[{"name":"system.properties"}]}' "$rcs_struct" "$rcs_system" "$rcs_version")
            echo "Fetching RCS system.properties..."
            param_response=$(curl -s -X POST "$param_url" \
              -H "authorization: Bearer $bearer_token" \
              -H "Content-Type: application/json" \
              -d "$param_body")
            if command -v jq >/dev/null 2>&1; then
              props_b64=$(echo "$param_response" | jq -r '.parameterList[]? | select(.name == "system.properties") | .content' | head -n 1)
            else
              props_b64=$(echo "$param_response" | grep -o '"content":"[^"]*"' | head -n 1 | sed 's/"content":"//;s/"$//')
            fi
            if [ -n "$props_b64" ]; then
              props_content=$(echo "$props_b64" | base64 -d 2>/dev/null)
              rcs_url=$(echo "$props_content" | grep '^rcs\.url=' | sed 's/^rcs\.url=//;s/\\:/:/g;s/\\=/=/g' | tr -d '\r')
              if [ -n "$rcs_url" ]; then
                echo "Autodetected RCS URL: $rcs_url"
              else
                echo "Warning: system.properties found but no rcs.url entry"
              fi
            else
              echo "Warning: No system.properties content returned for RCS node"
            fi
          else
            echo "Warning: No Resource-Cache-Service node found for store $storeNumber"
          fi
        else
          echo "Warning: No access token available for RCS URL autodetect"
        fi

        if [ -z "$rcs_url" ]; then
          echo "RCS URL autodetection failed. Continue without rcs.url in installation token?"
          read -p "Press Y to continue, any other key to abort: " continue_choice
          if [ "$continue_choice" != "Y" ] && [ "$continue_choice" != "y" ]; then
            echo "Aborted by user."
            exit 1
          fi
        fi
      fi
    fi
    # ---- End pre-onboarding RCS URL resolution ----
```

- [ ] **Step 5: Delete the old autodetect block**

Locate the block starting at approximately line 2536 (`# Resolve RCS URL if autodetect requested`) through line 2619 (just before `# Append RCS URL to installation token if provided`). **Delete this entire block.**

Keep the `# Append RCS URL...` block (lines 2621-2624) — unchanged.

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestGKInstallShRcsUrlPreOnboarding -v`
Expected: 3 passes.

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add gk_install_builder/templates/GKInstall.sh.template tests/unit/test_rcs_afteronboarding.py
git commit -m "feat(rcs): GKInstall.sh resolve rcs_url before onboarding; pass --rcsUrl"
```

---

### Task 5: End-to-end smoke test — verify rcsUrl flag flows from CLI to onboarding body

**Files:**
- Test: `tests/unit/test_rcs_afteronboarding.py` (add class)

- [ ] **Step 1: Write the smoke test**

Append to `tests/unit/test_rcs_afteronboarding.py`:

```python
class TestRcsUrlEndToEndFlow:
    """Verify the full rcsUrl flow end-to-end across generated scripts."""

    def test_ps1_full_flow_consistent(self, tmp_path):
        """When rcsUrl is set, the generated PS1 chain wires it correctly."""
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        cfg = create_config(platform="Windows")
        gen = ProjectGenerator(cfg, output_dir=str(tmp_path))
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate()

        gk_path = os.path.join(str(tmp_path), "GKInstall.ps1")
        ob_path = os.path.join(str(tmp_path), "onboarding.ps1")
        with open(gk_path, "r", encoding="utf-8") as f:
            gk = f.read()
        with open(ob_path, "r", encoding="utf-8") as f:
            ob = f.read()

        # GKInstall passes rcsUrl
        assert '-rcsUrl $rcsUrl' in gk
        # Autodetect lives in GKInstall before onboarding call
        assert gk.find("Autodetecting RCS URL") < gk.find(".\\onboarding.ps1")
        # Onboarding accepts param + injects
        assert '[string]$rcsUrl' in ob
        assert 'afterOnboardingProperties' in ob
        assert '-ne "RCS-SERVICE"' in ob
        # Legacy installationtoken.txt append still present
        assert 'rcs.url=$rcsUrl' in gk or '`nrcs.url=$rcsUrl' in gk

    def test_sh_full_flow_consistent(self, tmp_path):
        """When rcs_url is set, the generated SH chain wires it correctly."""
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        cfg = create_config(platform="Linux")
        gen = ProjectGenerator(cfg, output_dir=str(tmp_path))
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate()

        gk_path = os.path.join(str(tmp_path), "GKInstall.sh")
        ob_path = os.path.join(str(tmp_path), "onboarding.sh")
        with open(gk_path, "r", encoding="utf-8") as f:
            gk = f.read()
        with open(ob_path, "r", encoding="utf-8") as f:
            ob = f.read()

        assert '--rcsUrl "$rcs_url"' in gk
        assert gk.find("Autodetecting RCS URL") < gk.find("./onboarding.sh")
        assert '--rcsUrl' in ob
        assert 'afterOnboardingProperties' in ob
        assert '!= "RCS-SERVICE"' in ob
        # Legacy installationtoken.txt append still present
        assert 'rcs.url=$rcs_url' in gk
```

- [ ] **Step 2: Run the smoke test**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestRcsUrlEndToEndFlow -v`
Expected: 2 passes (since prior tasks already implemented all the requirements).

- [ ] **Step 3: Run the full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All 187 + new tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_rcs_afteronboarding.py
git commit -m "test(rcs): end-to-end flow assertions for rcsUrl across PS1 and SH"
```

---

## Verification (final pass before PR)

- [ ] Run `pytest tests/ -v` — every test passes (187 previously + new tests)
- [ ] Manually generate a Windows + Linux project with `--rcsUrl autodetect` and inspect:
  - `GKInstall.ps1` and `GKInstall.sh` — autodetect block appears before onboarding call, no duplicate, onboarding invocation passes `-rcsUrl`/`--rcsUrl`
  - `onboarding.ps1` and `onboarding.sh` — accept the new param, inject `afterOnboardingProperties` for non-RCS components, skip for RCS-SERVICE
  - `installationtoken.txt` legacy append behavior preserved (`rcs.url=...` line still added)
- [ ] Confirm sed fallback path in `onboarding.sh` is anchored to `$ s/}/...}/` (last line only)
- [ ] Confirm no `helper/onboarding/*.onboarding.json` files were modified — disk templates pristine

---

## Out of scope

- No new CLI parameters beyond reusing `--rcsUrl`
- No change to `helper/onboarding/*.onboarding.json` files on disk
- No change to the autodetect API endpoint or its response parsing
- No new fixtures or version-management features
