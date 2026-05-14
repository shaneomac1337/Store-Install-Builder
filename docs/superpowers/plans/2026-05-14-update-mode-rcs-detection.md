# Update-mode RCS Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When GKInstall runs in update mode and the existing `station.properties` contains `rcs.url=...`, the "Waiting for installer log file..." progress message must show "Downloading installation files from RCS (\<url\>)" instead of "Downloading from \<base_url\> DSG".

**Architecture:** Cosmetic / log-message change only. Add `rcs.url` regex extraction in the existing update-mode `station.properties` parse block (PowerShell line ~1107; Bash line ~1346). Set local var `$stationRcsUrl` / `station_rcs_url`. Add an `elseif` branch to the existing wait-message logic (PS1 ~2655, SH ~3109) that uses this variable when CLI `$rcsUrl` is unset. No other side effects.

**Tech Stack:** PowerShell + Bash templates; Python generator; pytest.

**Spec:** [docs/superpowers/specs/2026-05-14-update-mode-rcs-detection-design.md](../specs/2026-05-14-update-mode-rcs-detection-design.md)

**Branch:** `feature/rcs-afteronboarding` (per user — continues on existing branch)

---

### Task 1: GKInstall.ps1 — extract `rcs.url` from station.properties + add elseif to wait message

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template`
  - Update-mode parse block (~line 1107-1135) — add extraction
  - Wait-message block (~line 2655) — add `elseif` branch
- Test: `tests/unit/test_rcs_afteronboarding.py` (add new class)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_rcs_afteronboarding.py`:

```python
class TestUpdateModeRcsDetectionPs1:
    """GKInstall.ps1 must extract rcs.url from station.properties in update mode
    and show it in the wait message via an elseif branch."""

    def _generate_ps1(self, tmp_path):
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        cfg = create_config(platform="Windows")
        gen = ProjectGenerator()
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate(cfg, output_dir=str(tmp_path))
        ps1_path = os.path.join(str(tmp_path), "GKInstall.ps1")
        with open(ps1_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_ps1_extracts_rcs_url_from_station_properties(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        # Extraction regex present
        assert "'rcs\\.url=([^\\r\\n]+)'" in content or \
               "rcs\\.url=([^\\r\\n]+)" in content, (
            "GKInstall.ps1 must contain rcs.url regex extraction"
        )
        # Variable assigned
        assert '$stationRcsUrl' in content, (
            "GKInstall.ps1 must declare $stationRcsUrl variable"
        )
        # Java-escape unescape (matches configServiceUrl pattern)
        # The extraction line should use the same -replace pattern
        assert "$stationRcsUrl = $matches[1].Trim() -replace '\\\\:', ':' -replace '\\\\=', '='" in content, (
            "GKInstall.ps1 must unescape Java property colons/equals for stationRcsUrl"
        )

    def test_ps1_wait_message_has_station_rcs_elseif(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        # The new elseif branch must reference $stationRcsUrl
        assert 'elseif ($stationRcsUrl)' in content, (
            "GKInstall.ps1 wait-message logic must include elseif ($stationRcsUrl) branch"
        )
        # And use the variable in the RCS message
        assert 'Downloading installation files from RCS ($stationRcsUrl)' in content, (
            "Wait message must show extracted station.properties rcs.url"
        )

    def test_ps1_extraction_before_wait_message(self, tmp_path):
        """station.properties parse block must appear BEFORE wait-message block
        so $stationRcsUrl is in scope."""
        content = self._generate_ps1(tmp_path)
        extract_idx = content.find('$stationRcsUrl = $matches[1].Trim()')
        wait_idx = content.find('elseif ($stationRcsUrl)')
        assert extract_idx >= 0, "Extraction not found"
        assert wait_idx >= 0, "Wait-message elseif not found"
        assert extract_idx < wait_idx, (
            f"Extraction (idx={extract_idx}) must appear BEFORE wait-message elseif (idx={wait_idx})"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestUpdateModeRcsDetectionPs1 -v`
Expected: 3 failures (extraction missing, `$stationRcsUrl` missing, elseif missing).

- [ ] **Step 3: Modify GKInstall.ps1.template — add rcs.url extraction in update-mode parse block**

Locate the existing update-mode parse block. Find the `configServiceUrl` extraction (around line 1124-1135). Insert NEW extraction block immediately AFTER the `configServiceUrl` block, BEFORE the next existing field extraction. The exact insertion point: after the closing `}` of the `if ($stationPropertiesContent -match 'configService\.url=...')` block.

Use `grep -n "Found Config Service URL in station.properties"` to locate.

Insert:

```powershell
        # Extract the RCS URL (for update-mode wait message; cosmetic only)
        if ($stationPropertiesContent -match 'rcs\.url=([^\r\n]+)') {
            $stationRcsUrl = $matches[1].Trim() -replace '\\:', ':' -replace '\\=', '='
            Write-Host "Found RCS URL in station.properties: $stationRcsUrl"
        }
```

The variable `$stationPropertiesContent` was loaded at line ~1109. `$stationRcsUrl` defaults to `$null`/unset when this block doesn't run (fresh install) or when the regex doesn't match (no rcs.url in file).

- [ ] **Step 4: Modify GKInstall.ps1.template — add elseif branch to wait-message logic**

Locate the wait-message block. Find with: `grep -n "Downloading installation files from RCS" gk_install_builder/templates/GKInstall.ps1.template`. Should find the block around line 2655.

Replace the existing block:

```powershell
        $waitMessage = if (-not $offline.IsPresent) {
            if ($rcsUrl -and $rcsUrl -ne "autodetect") {
                "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from RCS ($rcsUrl)"
            } else {
                "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from $base_url DSG"
            }
        } else {
            "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed)"
        }
```

With:

```powershell
        $waitMessage = if (-not $offline.IsPresent) {
            if ($rcsUrl -and $rcsUrl -ne "autodetect") {
                "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from RCS ($rcsUrl)"
            } elseif ($stationRcsUrl) {
                "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from RCS ($stationRcsUrl)"
            } else {
                "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from $base_url DSG"
            }
        } else {
            "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed)"
        }
```

Only one line changed: a new `elseif ($stationRcsUrl)` branch inserted before the `else` (DSG) branch.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestUpdateModeRcsDetectionPs1 -v`
Expected: 3 passes.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short -q`
Expected: All previously passing tests still pass (416 + 3 new = 419 passing; 1 pre-existing pytest-mock error unrelated).

- [ ] **Step 7: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template tests/unit/test_rcs_afteronboarding.py
git commit -m "feat(rcs): GKInstall.ps1 detect rcs.url in station.properties for update-mode wait message"
```

---

### Task 2: GKInstall.sh — extract `rcs.url` from station.properties + add elif to wait message

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.sh.template`
  - Update-mode parse block (~line 1346-1395) — add extraction
  - Wait-message block (~line 3109) — add `elif` branch
- Test: `tests/unit/test_rcs_afteronboarding.py` (add new class)

**Bash extraction pattern note:** GKInstall.sh uses individual `grep` calls per key (NOT a pre-loaded variable like the PowerShell version). The existing pattern for `configService.url` is:

```bash
config_service_url_line=$(grep "configService.url=" "$station_properties_path")
if [ -n "$config_service_url_line" ]; then
  config_service_url=$(echo "$config_service_url_line" | cut -d'=' -f2-)
  config_service_url=$(echo "$config_service_url" | sed 's/\\:/:/g')
  echo "Found Config Service URL in station.properties: $config_service_url"
fi
```

Match this style for `rcs.url`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_rcs_afteronboarding.py`:

```python
class TestUpdateModeRcsDetectionSh:
    """GKInstall.sh must extract rcs.url from station.properties in update mode
    and show it in the wait message via an elif branch."""

    def _generate_sh(self, tmp_path):
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        cfg = create_config(platform="Linux")
        gen = ProjectGenerator()
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate(cfg, output_dir=str(tmp_path))
        sh_path = os.path.join(str(tmp_path), "GKInstall.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_sh_extracts_rcs_url_from_station_properties(self, tmp_path):
        content = self._generate_sh(tmp_path)
        # grep call on rcs.url present
        assert 'grep "rcs.url=" "$station_properties_path"' in content or \
               'grep \'rcs.url=\' "$station_properties_path"' in content or \
               'grep "^rcs\\.url=" "$station_properties_path"' in content, (
            "GKInstall.sh must grep for rcs.url in station.properties"
        )
        # Variable name
        assert 'station_rcs_url=' in content, (
            "GKInstall.sh must assign station_rcs_url variable"
        )
        # Java unescape (matches configService.url style)
        assert "sed 's/\\\\:/:/g'" in content or "sed 's/\\\\:/:/g;s/\\\\=/=/g'" in content, (
            "GKInstall.sh must unescape \\: -> : (Java property style)"
        )

    def test_sh_wait_message_has_station_rcs_elif(self, tmp_path):
        content = self._generate_sh(tmp_path)
        assert 'elif [ -n "$station_rcs_url" ]' in content, (
            "Wait-message logic must include elif [ -n \"$station_rcs_url\" ] branch"
        )
        assert 'Downloading installation files from RCS ($station_rcs_url)' in content, (
            "Wait message must show extracted station.properties rcs.url"
        )

    def test_sh_extraction_before_wait_message(self, tmp_path):
        content = self._generate_sh(tmp_path)
        extract_idx = content.find('station_rcs_url=')
        wait_idx = content.find('elif [ -n "$station_rcs_url" ]')
        assert extract_idx >= 0 and wait_idx >= 0
        assert extract_idx < wait_idx, (
            f"Extraction (idx={extract_idx}) must appear BEFORE wait-message elif (idx={wait_idx})"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestUpdateModeRcsDetectionSh -v`
Expected: 3 failures.

- [ ] **Step 3: Modify GKInstall.sh.template — add rcs.url extraction in update-mode parse block**

Locate the existing update-mode parse block (around line 1346). Find the `configService.url` extraction (around line 1366-1383). Insert NEW extraction immediately AFTER the closing `fi` of the `if [ -n "$config_service_url_line" ]; then ... fi` block, BEFORE the next `# Extract the tenant ID` block.

Use `grep -n "Found Config Service URL in station.properties" gk_install_builder/templates/GKInstall.sh.template` to locate.

Insert:

```bash
    # Extract the RCS URL (for update-mode wait message; cosmetic only)
    rcs_url_line=$(grep "^rcs\.url=" "$station_properties_path")
    if [ -n "$rcs_url_line" ]; then
      station_rcs_url=$(echo "$rcs_url_line" | cut -d'=' -f2-)
      # Unescape Java property colons/equals: https\://host\:7443/rcs -> https://host:7443/rcs
      station_rcs_url=$(echo "$station_rcs_url" | sed 's/\\:/:/g;s/\\=/=/g' | tr -d '\r')
      echo "Found RCS URL in station.properties: $station_rcs_url"
    fi
```

- [ ] **Step 4: Modify GKInstall.sh.template — add elif branch to wait-message logic**

Find the wait-message block: `grep -n "Downloading installation files from RCS" gk_install_builder/templates/GKInstall.sh.template`. Should be around line 3110.

Replace the existing block:

```bash
    if [ "$offline_mode" = false ]; then
      if [ -n "$rcs_url" ] && [ "$rcs_url" != "autodetect" ]; then
        echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from RCS ($rcs_url)"
      else
        echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from $base_url DSG"
      fi
    else
      echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed)"
    fi
```

With:

```bash
    if [ "$offline_mode" = false ]; then
      if [ -n "$rcs_url" ] && [ "$rcs_url" != "autodetect" ]; then
        echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from RCS ($rcs_url)"
      elif [ -n "$station_rcs_url" ]; then
        echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from RCS ($station_rcs_url)"
      else
        echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from $base_url DSG"
      fi
    else
      echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed)"
    fi
```

One new `elif` branch inserted before the `else` (DSG) branch.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_rcs_afteronboarding.py::TestUpdateModeRcsDetectionSh -v`
Expected: 3 passes.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ --tb=short -q`
Expected: All previously passing tests still pass (419 + 3 new = 422 passing; 1 pre-existing pytest-mock error unrelated).

- [ ] **Step 7: Commit**

```bash
git add gk_install_builder/templates/GKInstall.sh.template tests/unit/test_rcs_afteronboarding.py
git commit -m "feat(rcs): GKInstall.sh detect rcs.url in station.properties for update-mode wait message"
```

---

## Verification (final pass)

- [ ] Run `pytest tests/ -v` — every test passes (419 prior + 6 new = ~422 passing)
- [ ] Manually inspect generated `GKInstall.ps1`:
  - Update-mode parse block (around line 1107-1135) contains `if ($stationPropertiesContent -match 'rcs\.url=...')` extraction block
  - Wait-message block contains `elseif ($stationRcsUrl)` branch ordered between CLI-rcsUrl branch and DSG fallback
- [ ] Manually inspect generated `GKInstall.sh`:
  - Update-mode parse block contains `rcs_url_line=$(grep ...)` extraction with `sed 's/\\:/:/g'` unescape
  - Wait-message block contains `elif [ -n "$station_rcs_url" ]` branch
- [ ] Confirm no behavioral change when:
  - Fresh install (no update mode) → station_rcs_url unset → DSG fallback hit
  - Update mode + station.properties has rcs.url + CLI --rcsUrl also set → CLI wins (precedence #1)
  - Update mode + station.properties lacks rcs.url → station_rcs_url unset → DSG fallback hit

---

## Out of scope

- No change to `installationtoken.txt` `rcs.url=` append logic
- No auto-set of `$rcsUrl` / `$rcs_url` script variable from station.properties
- No change to onboarding flow or `afterOnboardingProperties` injection
- No change to autodetect behavior on fresh install
- No new CLI parameters
- No change to `helper/onboarding/*.onboarding.json` files
