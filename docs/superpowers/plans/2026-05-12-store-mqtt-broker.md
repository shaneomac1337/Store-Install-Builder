# Store MQTT Broker Component Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Store MQTT Broker as a fully-wired installable component across config, UI, generators, templates, detection, dialogs, API integration, and tests — cloning the RCS-SERVICE pattern verbatim.

**Architecture:** Mechanical clone of every RCS-SERVICE reference in the codebase, renamed to MQTT-BROKER (key) / Store MQTT Broker (label) / store-mqtt-broker-service (slug) / GKR-Store-MQTT-Broker (system type) / `clientType=store-mqtt-broker` (onboarding) / `MQTT.station` (detection file). One parametrized test case added per existing test file to lock in parity.

**Tech Stack:** Python 3, CustomTkinter (GUI), pytest (tests), Jinja-free `@VARIABLE@` token templates, PowerShell + Bash template targets.

**Spec:** `docs/superpowers/specs/2026-05-12-store-mqtt-broker-design.md`

---

## Glossary of Identifiers

These exact strings appear throughout the plan. Use them verbatim.

| Aspect | Value |
|--------|-------|
| Display label | `Store MQTT Broker` |
| Internal key | `MQTT-BROKER` |
| Onboarding `clientType` | `store-mqtt-broker` |
| System type (cloud) | `GKR-Store-MQTT-Broker` |
| Config key prefix | `mqtt_broker_` |
| File slug | `store-mqtt-broker-service` |
| Station file | `MQTT.station` |
| Tomcat service name | `Tomcat-storemqttbrokerservice` |
| Updater service name | `Updater-storemqttbrokerservice` |
| FP property ID | `StoreMQTTBroker_Version` |
| FPD property ID | `StoreMQTTBroker_Update_Version` |
| Default version | `v1.0.0` |
| Substitution tokens | `@MQTT_BROKER_VERSION@`, `@MQTT_BROKER_SYSTEM_TYPE@`, `@MQTT_BROKER_INSTALL_DIR@` |

---

## Task 1: Config defaults + default_versions.json

**Files:**
- Modify: `gk_install_builder/config.py:121-128` (`installer_overrides_components`), `:147` (after `rcs_version`), `:158` (after `rcs_system_type`)
- Modify: `gk_install_builder/default_versions.json` — add 2 entries after the RCS entries (lines ~290-297)
- Test: `tests/unit/test_config_management.py` (or nearest config test) — add MQTT-BROKER defaults test

- [ ] **Step 1.1: Write failing test**

Add to `tests/unit/test_config_management.py` (or create if absent — verify with `pytest --collect-only tests/unit/test_config_management.py 2>&1 | head`):

```python
def test_mqtt_broker_defaults_present():
    from gk_install_builder.config import ConfigManager
    cm = ConfigManager()
    config = cm._get_default_config()
    assert config["installer_overrides_components"]["MQTT-BROKER"] is True
    assert config["mqtt_broker_version"] == "v1.0.0"
    assert "mqtt_broker_system_type" in config
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
pytest tests/unit/test_config_management.py::test_mqtt_broker_defaults_present -v
```
Expected: FAIL with `KeyError: 'MQTT-BROKER'` or `KeyError: 'mqtt_broker_version'`.

- [ ] **Step 1.3: Edit `gk_install_builder/config.py`**

In `installer_overrides_components` dict (around line 121-128), append after `"RCS-SERVICE": True,`:
```python
                "MQTT-BROKER": True,
```

After `"rcs_version": "v1.0.0",` (around line 147), append:
```python
            "mqtt_broker_version": "v1.0.0",
```

After `"rcs_system_type": "",  # Will be dynamically set based on URL` (around line 158), append:
```python
            "mqtt_broker_system_type": "",  # Will be dynamically set based on URL
```

- [ ] **Step 1.4: Edit `gk_install_builder/default_versions.json`**

After the `RCS_Version` entry (around line 290-297), insert two new entries. Locate alphabetical placement by `propertyId` (after `RCS_Version`, before `Receipt_Image_Extensions`):

```json
    {
        "propertyId": "StoreMQTTBroker_Update_Version",
        "tenantId": "000",
        "scope": "FPD",
        "referenceId": "platform",
        "value": "v1.0.0",
        "description": "Version for Store MQTT Broker Update"
    },
    {
        "propertyId": "StoreMQTTBroker_Version",
        "tenantId": "000",
        "scope": "FPD",
        "referenceId": "platform",
        "value": "v1.0.0",
        "description": "Version of Store MQTT Broker for installation"
    },
```

Make sure commas balance with surrounding entries.

- [ ] **Step 1.5: Run test to verify pass**

```bash
pytest tests/unit/test_config_management.py::test_mqtt_broker_defaults_present -v
```
Expected: PASS.

- [ ] **Step 1.6: Commit**

```bash
git add gk_install_builder/config.py gk_install_builder/default_versions.json tests/unit/test_config_management.py
git commit -m "feat(mqtt-broker): add config defaults + FP/FPD property defaults"
```

---

## Task 2: Detection (station file mapping)

**Files:**
- Modify: `gk_install_builder/detection.py:12-29` (custom_filenames + detection_files dicts)
- Test: `tests/unit/test_generator_core.py` — add MQTT-BROKER detection test case

- [ ] **Step 2.1: Write failing test**

Add to `tests/unit/test_generator_core.py`:

```python
def test_mqtt_broker_detection_file_default():
    from gk_install_builder.detection import DetectionManager
    dm = DetectionManager()
    assert dm.detection_config["custom_filenames"]["MQTT-BROKER"] == "MQTT.station"
    assert "MQTT-BROKER" in dm.detection_config["detection_files"]
```

- [ ] **Step 2.2: Run test to verify fail**

```bash
pytest tests/unit/test_generator_core.py::test_mqtt_broker_detection_file_default -v
```
Expected: FAIL with `KeyError`.

- [ ] **Step 2.3: Edit `gk_install_builder/detection.py`**

In `custom_filenames` dict (lines 12-20), after `"RCS-SERVICE": "RCS.station"`, add:
```python
                "MQTT-BROKER": "MQTT.station"
```
(comma before, no comma after if last entry — preserve dict trailing-comma style of file)

In `detection_files` dict (lines 21-29), after `"RCS-SERVICE": ""`, add:
```python
                "MQTT-BROKER": ""
```

- [ ] **Step 2.4: Run test to verify pass**

```bash
pytest tests/unit/test_generator_core.py::test_mqtt_broker_detection_file_default -v
```
Expected: PASS.

- [ ] **Step 2.5: Commit**

```bash
git add gk_install_builder/detection.py tests/unit/test_generator_core.py
git commit -m "feat(mqtt-broker): add MQTT.station detection mapping"
```

---

## Task 3: Test fixtures (4 JSON configs + generator_fixtures.py)

**Files:**
- Modify: `tests/fixtures/configs/minimal_windows.json`
- Modify: `tests/fixtures/configs/minimal_linux.json`
- Modify: `tests/fixtures/configs/full_windows.json`
- Modify: `tests/fixtures/configs/full_linux.json`
- Modify: `tests/fixtures/generator_fixtures.py`
- Modify: `tests/conftest.py` (if it lists components)

- [ ] **Step 3.1: Add MQTT-BROKER to each fixture JSON**

For each of the 4 JSON fixture files, locate any RCS-SERVICE / rcs_* entry and add a parallel MQTT-BROKER / mqtt_broker_* entry beside it. Specifically:

In each JSON file, add to top-level config:
```json
  "mqtt_broker_version": "v1.0.0",
  "mqtt_broker_system_type": "GKR-Store-MQTT-Broker",
```

If the JSON has an `installer_overrides_components` block with RCS-SERVICE, add `"MQTT-BROKER": true` to it.

Use Read then Edit on each file. Verify with:
```bash
grep -c "mqtt_broker" tests/fixtures/configs/*.json
```
Expected: at least 2 lines per file.

- [ ] **Step 3.2: Edit `tests/fixtures/generator_fixtures.py`**

Locate any list/dict referencing RCS-SERVICE. Add `"MQTT-BROKER"` to the same collection. Grep first:
```bash
grep -n "RCS-SERVICE\|rcs_service\|RCS_SERVICE" tests/fixtures/generator_fixtures.py
```
For each match, add a parallel MQTT-BROKER entry.

- [ ] **Step 3.3: Edit `tests/conftest.py` (if needed)**

```bash
grep -n "RCS-SERVICE\|rcs_service" tests/conftest.py
```
If matches exist, add MQTT-BROKER parallels.

- [ ] **Step 3.4: Run full suite to confirm no fixture regressions**

```bash
pytest tests/ -x --tb=short 2>&1 | tail -30
```
Expected: any failures are NEW MQTT-BROKER tests not yet wired (acceptable). Existing tests must still pass.

- [ ] **Step 3.5: Commit**

```bash
git add tests/fixtures/ tests/conftest.py
git commit -m "test(mqtt-broker): add MQTT-BROKER to test fixtures"
```

---

## Task 4: gen_config (launcher template list + structure)

**Files:**
- Modify: `gk_install_builder/gen_config/generator_config.py:18-50` (file lists), `:152-176` (LAUNCHER_TEMPLATE_*), `:205-227` (override XML mappings)

- [ ] **Step 4.1: Write failing test**

Add to `tests/unit/test_generator_file_ops.py`:

```python
def test_mqtt_broker_in_launcher_list():
    from gk_install_builder.gen_config.generator_config import LAUNCHER_TEMPLATES
    assert "launcher.store-mqtt-broker-service.template" in LAUNCHER_TEMPLATES
```

(If the constant name differs, grep `gen_config/generator_config.py` first for the actual exported list name and adjust the test.)

- [ ] **Step 4.2: Run test to verify fail**

```bash
pytest tests/unit/test_generator_file_ops.py::test_mqtt_broker_in_launcher_list -v
```
Expected: FAIL or import error.

- [ ] **Step 4.3: Edit `gk_install_builder/gen_config/generator_config.py`**

Open the file. For every list/dict containing `launcher.rcs-service.template`, add `launcher.store-mqtt-broker-service.template` as a sibling entry.

For every list containing `rcs-service.onboarding.json`, add `store-mqtt-broker-service.onboarding.json`.

For the `LAUNCHER_TEMPLATE_RCS_SERVICE` constant (around lines 152-176), define a new constant `LAUNCHER_TEMPLATE_MQTT_BROKER` with this content:

```python
LAUNCHER_TEMPLATE_MQTT_BROKER = """# Launcher defaults for Store MQTT Broker
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
```

For the override file mapping (around lines 205-227), wherever `installer_overrides.rcs-service.xml` is referenced, add `installer_overrides.mqtt-broker.xml` parallel entry.

- [ ] **Step 4.4: Run test to verify pass**

```bash
pytest tests/unit/test_generator_file_ops.py::test_mqtt_broker_in_launcher_list -v
```
Expected: PASS.

- [ ] **Step 4.5: Commit**

```bash
git add gk_install_builder/gen_config/generator_config.py tests/unit/test_generator_file_ops.py
git commit -m "feat(mqtt-broker): register launcher + onboarding + override entries"
```

---

## Task 5: generator.py file lists + default template

**Files:**
- Modify: `gk_install_builder/generator.py:466-468` (launcher template list), `:481` (onboarding JSON list), `:537` (onboarding JSON default content), `:1089-1091` (default template creation)

- [ ] **Step 5.1: Write failing test**

Add to `tests/unit/test_generator_integration.py`:

```python
def test_mqtt_broker_launcher_file_generated(tmp_path, full_windows_config):
    from gk_install_builder.generator import ProjectGenerator
    pg = ProjectGenerator(config=full_windows_config, output_dir=str(tmp_path))
    pg.generate()
    launcher_path = tmp_path / "helper" / "launchers" / "launcher.store-mqtt-broker-service.template"
    onboarding_path = tmp_path / "helper" / "onboarding" / "store-mqtt-broker-service.onboarding.json"
    assert launcher_path.exists(), f"Missing {launcher_path}"
    assert onboarding_path.exists(), f"Missing {onboarding_path}"
```

(If the `ProjectGenerator` constructor signature differs, look up actual call site with `grep -n "ProjectGenerator(" tests/unit/test_generator_integration.py` and match it.)

- [ ] **Step 5.2: Run test to verify fail**

```bash
pytest tests/unit/test_generator_integration.py::test_mqtt_broker_launcher_file_generated -v
```
Expected: FAIL — launcher file missing.

- [ ] **Step 5.3: Edit `gk_install_builder/generator.py`**

At lines 466-468 — the launcher template list:
```python
                         "launcher.wdm.template", "launcher.flow-service.template",
                         "launcher.lpa-service.template", "launcher.storehub-service.template",
                         "launcher.rcs-service.template",
                         "launcher.store-mqtt-broker-service.template"]:
```

At line 481 — onboarding JSON list, similarly add `"store-mqtt-broker-service.onboarding.json"`.

At line 537 (onboarding JSON default-content dict), add entry parallel to RCS:
```python
            "store-mqtt-broker-service.onboarding.json": '''{"deviceId":"@USER_ID@","tenant_id":"@TENANT_ID@","clientType":"store-mqtt-broker","timestamp":"{{TIMESTAMP}}"}''',
```

At line 1091 area (`self._create_default_template(...)` calls), add:
```python
        self._create_default_template(launchers_dir, "launcher.store-mqtt-broker-service.template")
```

- [ ] **Step 5.4: Run test to verify pass**

```bash
pytest tests/unit/test_generator_integration.py::test_mqtt_broker_launcher_file_generated -v
```
Expected: PASS.

- [ ] **Step 5.5: Commit**

```bash
git add gk_install_builder/generator.py tests/unit/test_generator_integration.py
git commit -m "feat(mqtt-broker): wire launcher + onboarding file generation"
```

---

## Task 6: launcher_generator.py (settings + default template)

**Files:**
- Modify: `gk_install_builder/generators/launcher_generator.py:108-129` (settings extraction + template_files dict), `:171-329` (`create_default_template` adds MQTT branch)

- [ ] **Step 6.1: Write failing test**

Add to `tests/unit/test_generator_file_ops.py`:

```python
def test_mqtt_broker_launcher_template_content(tmp_path):
    from gk_install_builder.generators.launcher_generator import create_default_template
    create_default_template(str(tmp_path), "launcher.store-mqtt-broker-service.template")
    path = tmp_path / "launcher.store-mqtt-broker-service.template"
    content = path.read_text()
    assert "# Launcher defaults for Store MQTT Broker" in content
    assert "applicationServerHttpPort=8180" in content
    assert "applicationServerHttpsPort=8543" in content
    assert "@BASE64_TOKEN@" in content
```

- [ ] **Step 6.2: Run test to verify fail**

```bash
pytest tests/unit/test_generator_file_ops.py::test_mqtt_broker_launcher_template_content -v
```
Expected: FAIL — file empty or missing.

- [ ] **Step 6.3: Edit `gk_install_builder/generators/launcher_generator.py`**

At line 109, after `rcs_service_settings = config.get("rcs_service_launcher_settings", {})`, add:
```python
    mqtt_broker_settings = config.get("mqtt_broker_launcher_settings", {})
```

At line 119, after `print(f"RCS-SERVICE settings: {rcs_service_settings}")`, add:
```python
    print(f"MQTT-BROKER settings: {mqtt_broker_settings}")
```

In `template_files` dict (around line 129), after `"launcher.rcs-service.template": rcs_service_settings`, add:
```python
        ,
        "launcher.store-mqtt-broker-service.template": mqtt_broker_settings
```
(Replace the trailing comma/brace correctly — the dict ends with `}` on line 130. Insert comma after RCS entry, then new entry, then close `}`.)

In `create_default_template()` function, after the `elif filename == "launcher.rcs-service.template":` block (lines 301-320), add:
```python
    elif filename == "launcher.store-mqtt-broker-service.template":
        template_content = """# Launcher defaults for Store MQTT Broker
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
```

- [ ] **Step 6.4: Run test to verify pass**

```bash
pytest tests/unit/test_generator_file_ops.py::test_mqtt_broker_launcher_template_content -v
```
Expected: PASS.

- [ ] **Step 6.5: Commit**

```bash
git add gk_install_builder/generators/launcher_generator.py tests/unit/test_generator_file_ops.py
git commit -m "feat(mqtt-broker): launcher template settings + default content"
```

---

## Task 7: gk_install_generator.py (COMPONENT_SERVICE_CONFIG_MAP + tokens + station mapping)

**Files:**
- Modify: `gk_install_builder/generators/gk_install_generator.py:19-25` (COMPONENT_SERVICE_CONFIG_MAP), `:150-322` (substitution tokens), `:612-660`, `:847-899` (detection file mapping inserts)

- [ ] **Step 7.1: Write failing test**

Add to `tests/unit/test_generator_core.py`:

```python
def test_mqtt_broker_in_component_service_config_map():
    from gk_install_builder.generators.gk_install_generator import COMPONENT_SERVICE_CONFIG_MAP
    assert COMPONENT_SERVICE_CONFIG_MAP["MQTT-BROKER"] == "mqtt_broker_launcher_settings"

def test_mqtt_broker_station_file_in_generated_ps1(tmp_path, full_windows_config):
    from gk_install_builder.generator import ProjectGenerator
    pg = ProjectGenerator(config=full_windows_config, output_dir=str(tmp_path))
    pg.generate()
    ps1 = (tmp_path / "GKInstall.ps1").read_text()
    assert "'MQTT-BROKER'" in ps1
    assert "MQTT.station" in ps1
```

- [ ] **Step 7.2: Run tests to verify fail**

```bash
pytest tests/unit/test_generator_core.py::test_mqtt_broker_in_component_service_config_map tests/unit/test_generator_core.py::test_mqtt_broker_station_file_in_generated_ps1 -v
```
Expected: FAIL (key missing / station string missing).

- [ ] **Step 7.3: Edit `gk_install_builder/generators/gk_install_generator.py`**

At line 24-25, in `COMPONENT_SERVICE_CONFIG_MAP`:
```python
COMPONENT_SERVICE_CONFIG_MAP = {
    "WDM": "wdm_launcher_settings",
    "FLOW-SERVICE": "flow_service_launcher_settings",
    "LPA-SERVICE": "lpa_service_launcher_settings",
    "STOREHUB-SERVICE": "storehub_service_launcher_settings",
    "RCS-SERVICE": "rcs_service_launcher_settings",
    "MQTT-BROKER": "mqtt_broker_launcher_settings",
}
```

At lines 614-620 (and again at the parallel sh block around 847-855) — detection filename resolution. After `rcs_filename = detection_manager.get_custom_filename("RCS-SERVICE") if file_detection_enabled else "NEVER_MATCH.station"`, add:
```python
            mqtt_filename = detection_manager.get_custom_filename("MQTT-BROKER") if file_detection_enabled else "NEVER_MATCH.station"
```

Repeat for the bash detection block.

Find all substitution sections that include `rcs_filename` (e.g., `template = template.replace("@RCS_STATION_FILE@", rcs_filename)`). For each, add a parallel line for MQTT:
```python
            template = template.replace("@MQTT_BROKER_STATION_FILE@", mqtt_filename)
```

Also add MQTT-BROKER version/system-type token replacements wherever RCS_VERSION/RCS_SYSTEM_TYPE are replaced. Search:
```bash
grep -n "RCS_VERSION\|RCS_SYSTEM_TYPE\|rcs_version\|rcs_system_type" gk_install_builder/generators/gk_install_generator.py
```
For each match, add a parallel MQTT_BROKER line:
```python
            template = template.replace("@MQTT_BROKER_VERSION@", config.get("mqtt_broker_version", "v1.0.0"))
            template = template.replace("@MQTT_BROKER_SYSTEM_TYPE@", config.get("mqtt_broker_system_type", "GKR-Store-MQTT-Broker"))
```

- [ ] **Step 7.4: Run tests to verify pass**

```bash
pytest tests/unit/test_generator_core.py -k mqtt_broker -v
```
Expected: PASS.

- [ ] **Step 7.5: Commit**

```bash
git add gk_install_builder/generators/gk_install_generator.py tests/unit/test_generator_core.py
git commit -m "feat(mqtt-broker): COMPONENT_SERVICE_CONFIG_MAP + token + station mapping"
```

---

## Task 8: helper_file_generator.py (onboarding JSON + init config)

**Files:**
- Modify: `gk_install_builder/generators/helper_file_generator.py:41,73-74,97,295-378,491-504`

- [ ] **Step 8.1: Write failing test**

Add to `tests/unit/test_generator_file_ops.py`:

```python
def test_mqtt_broker_onboarding_json_content(tmp_path, full_windows_config):
    from gk_install_builder.generator import ProjectGenerator
    pg = ProjectGenerator(config=full_windows_config, output_dir=str(tmp_path))
    pg.generate()
    import json
    p = tmp_path / "helper" / "onboarding" / "store-mqtt-broker-service.onboarding.json"
    data = json.loads(p.read_text())
    assert data.get("clientType") == "store-mqtt-broker"
```

- [ ] **Step 8.2: Run test to verify fail**

```bash
pytest tests/unit/test_generator_file_ops.py::test_mqtt_broker_onboarding_json_content -v
```
Expected: FAIL — file missing or clientType wrong.

- [ ] **Step 8.3: Edit `gk_install_builder/generators/helper_file_generator.py`**

```bash
grep -n "rcs-service.onboarding\|RCS-SERVICE\|rcs_service" gk_install_builder/generators/helper_file_generator.py
```

For every RCS reference, add a parallel MQTT-BROKER reference:
- Onboarding filename: `"store-mqtt-broker-service.onboarding.json"`
- Onboarding JSON content for RCS uses `clientType` (or equivalent); use `"clientType": "store-mqtt-broker"` for MQTT
- Init helper directory entries (parallel to whatever RCS uses, e.g., `helper/init/store-mqtt-broker-service/`)
- Any dict mapping `RCS-SERVICE → onboarding-json-filename`: add `MQTT-BROKER → store-mqtt-broker-service.onboarding.json`

If RCS-SERVICE has a hardcoded JSON content block (lines 295-378 region), clone it and substitute the `clientType` value.

- [ ] **Step 8.4: Run test to verify pass**

```bash
pytest tests/unit/test_generator_file_ops.py::test_mqtt_broker_onboarding_json_content -v
```
Expected: PASS.

- [ ] **Step 8.5: Commit**

```bash
git add gk_install_builder/generators/helper_file_generator.py tests/unit/test_generator_file_ops.py
git commit -m "feat(mqtt-broker): onboarding JSON + init helper generation"
```

---

## Task 9: onboarding_generator.py (dispatch branch)

**Files:**
- Modify: `gk_install_builder/generators/onboarding_generator.py` — every RCS-SERVICE branch gets MQTT-BROKER sibling

- [ ] **Step 9.1: Locate RCS references**

```bash
grep -n "RCS-SERVICE\|rcs_service\|rcs-service" gk_install_builder/generators/onboarding_generator.py
```

- [ ] **Step 9.2: Add MQTT-BROKER parallels**

For each RCS dispatch branch (if/elif on componentType, list entries, string substitutions), add an equivalent MQTT-BROKER branch immediately after the RCS one. Use `clientType=store-mqtt-broker`, file slug `store-mqtt-broker-service`.

- [ ] **Step 9.3: Smoke test via integration**

```bash
pytest tests/unit/test_generator_integration.py -v 2>&1 | tail -20
```
Expected: no new failures attributable to onboarding generator (existing MQTT integration test from Task 5 still passes).

- [ ] **Step 9.4: Commit**

```bash
git add gk_install_builder/generators/onboarding_generator.py
git commit -m "feat(mqtt-broker): onboarding generator dispatch branch"
```

---

## Task 10: Templates — GKInstall.ps1 + GKInstall.sh

**Files:**
- Modify: `gk_install_builder/templates/GKInstall.ps1.template:340-346,3,201,345,515-525,756-762,785,860-868,1041,1053,1400,1430,1444,1509,1589,1981-1996,2290-2291,2371`
- Modify: `gk_install_builder/templates/GKInstall.sh.template:593-599,130,150,598,869-879,1090,1151,1293-1295,1771-1772,1814,1844,1912,1997,2410-2423,2704-2705,2757,2808`

- [ ] **Step 10.1: Write failing test**

Add to `tests/unit/test_service_installation.py`:

```python
def test_mqtt_broker_service_names_in_generated_ps1(tmp_path, full_windows_config):
    cfg = dict(full_windows_config)
    cfg["mqtt_broker_launcher_settings"] = {
        "runAsService": "1",
        "appServiceName": "Tomcat-storemqttbrokerservice",
        "updaterServiceName": "Updater-storemqttbrokerservice",
        "runAsServiceStartType": "auto",
    }
    from gk_install_builder.generator import ProjectGenerator
    pg = ProjectGenerator(config=cfg, output_dir=str(tmp_path))
    pg.generate()
    ps1 = (tmp_path / "GKInstall.ps1").read_text()
    assert "Tomcat-storemqttbrokerservice" in ps1
    assert "Updater-storemqttbrokerservice" in ps1
```

- [ ] **Step 10.2: Run test to verify fail**

```bash
pytest tests/unit/test_service_installation.py::test_mqtt_broker_service_names_in_generated_ps1 -v
```
Expected: FAIL — service names absent.

- [ ] **Step 10.3: Edit `GKInstall.ps1.template`**

Locate every line containing `RCS-SERVICE` or `'RCS-SERVICE'`. For each, add a parallel `MQTT-BROKER` branch immediately after. Examples:

Switch (line 340-346):
```powershell
        'STOREHUB-SERVICE' { "SH.station" }
        'RCS-SERVICE' { "RCS.station" }
        'MQTT-BROKER' { "MQTT.station" }
```

Component dispatch / version branch:
```powershell
        'RCS-SERVICE' {
            # existing RCS logic
        }
        'MQTT-BROKER' {
            # mirror the RCS block, swap RCS_VERSION → MQTT_BROKER_VERSION, etc.
        }
```

Repeat for every RCS branch. Use `grep -n "RCS-SERVICE" gk_install_builder/templates/GKInstall.ps1.template` to enumerate. For each line, manually copy the surrounding block, paste below, swap identifiers.

- [ ] **Step 10.4: Edit `GKInstall.sh.template`**

Same procedure for bash. The bash switch (line 593-599):
```bash
    'STOREHUB-SERVICE') station_filename="SH.station" ;;
    'RCS-SERVICE') station_filename="RCS.station" ;;
    'MQTT-BROKER') station_filename="MQTT.station" ;;
```

Walk every other RCS-SERVICE occurrence and add MQTT-BROKER sibling block.

- [ ] **Step 10.5: Run test to verify pass**

```bash
pytest tests/unit/test_service_installation.py::test_mqtt_broker_service_names_in_generated_ps1 -v
pytest tests/unit/test_generator_core.py::test_mqtt_broker_station_file_in_generated_ps1 -v
```
Expected: PASS.

- [ ] **Step 10.6: Commit**

```bash
git add gk_install_builder/templates/GKInstall.ps1.template gk_install_builder/templates/GKInstall.sh.template tests/unit/test_service_installation.py
git commit -m "feat(mqtt-broker): add MQTT-BROKER branches to GKInstall templates"
```

---

## Task 11: Templates — onboarding + store-initialization

**Files:**
- Modify: `gk_install_builder/templates/onboarding.ps1.template`
- Modify: `gk_install_builder/templates/onboarding.sh.template`
- Modify: `gk_install_builder/templates/store-initialization.ps1.template:103,403-406`
- Modify: `gk_install_builder/templates/store-initialization.sh.template`

- [ ] **Step 11.1: Locate every RCS reference**

```bash
grep -n "RCS-SERVICE\|rcs-service\|RCS_SERVICE" gk_install_builder/templates/onboarding.ps1.template gk_install_builder/templates/onboarding.sh.template gk_install_builder/templates/store-initialization.ps1.template gk_install_builder/templates/store-initialization.sh.template
```

- [ ] **Step 11.2: Add parallel MQTT-BROKER branches**

For each occurrence:
- Onboarding JSON list: add `"store-mqtt-broker-service.onboarding.json"` after `"rcs-service.onboarding.json"`
- componentType dispatch: add `'MQTT-BROKER'` branch after `'RCS-SERVICE'` branch
- Store init config writes: clone RCS block, swap identifiers (no MQTT-specific URL mode like `rcs_use_https` is needed — MQTT has no equivalent for now)

Important: store-initialization for RCS includes URL-mode logic (`rcs_use_https`, `rcs_skip_url_config`, `rcs_url_mode`). MQTT does NOT have these — skip the URL-config block for MQTT, only add the JSON config-write part.

- [ ] **Step 11.3: Smoke verify**

```bash
pytest tests/unit/ -k mqtt_broker -v 2>&1 | tail -20
```
Expected: existing MQTT tests still pass.

- [ ] **Step 11.4: Commit**

```bash
git add gk_install_builder/templates/onboarding.ps1.template gk_install_builder/templates/onboarding.sh.template gk_install_builder/templates/store-initialization.ps1.template gk_install_builder/templates/store-initialization.sh.template
git commit -m "feat(mqtt-broker): onboarding + store-init template branches"
```

---

## Task 12: main.py + features (auto_fill, version_manager)

**Files:**
- Modify: `gk_install_builder/main.py:607,620,1419,1426,1461,1468,1534,1546`
- Modify: `gk_install_builder/features/auto_fill.py:78,89,145-147`
- Modify: `gk_install_builder/features/version_manager.py:26,168-177,218,309`

- [ ] **Step 12.1: Write failing test for auto_fill**

Add to `tests/unit/test_auto_fill.py`:

```python
def test_mqtt_broker_system_type_auto_filled():
    from gk_install_builder.features.auto_fill import auto_fill_from_base_url
    config = {}
    auto_fill_from_base_url("test.cse.cloud4retail.co", config)
    assert config["mqtt_broker_system_type"] == "GKR-Store-MQTT-Broker"
```

(If the actual `auto_fill_from_base_url` signature differs, inspect `tests/unit/test_auto_fill.py` for an existing RCS test and copy its structure.)

- [ ] **Step 12.2: Run test to verify fail**

```bash
pytest tests/unit/test_auto_fill.py::test_mqtt_broker_system_type_auto_filled -v
```
Expected: FAIL.

- [ ] **Step 12.3: Edit `gk_install_builder/features/auto_fill.py`**

For every RCS reference (`rcs_system_type`, `GKR-Resource-Cache-Service`), add MQTT-BROKER parallel:
```python
config["mqtt_broker_system_type"] = "GKR-Store-MQTT-Broker"
```

- [ ] **Step 12.4: Edit `gk_install_builder/features/version_manager.py`**

For every RCS version-row reference (line 26 enum/list, lines 168-177 mapping, line 218, line 309), add MQTT-BROKER:
- Component list: include `"MQTT-BROKER"` with display label `"Store MQTT Broker"`
- Property-ID mapping: `"MQTT-BROKER": ("StoreMQTTBroker_Version", "StoreMQTTBroker_Update_Version")`
- Config key: `mqtt_broker_version`

- [ ] **Step 12.5: Edit `gk_install_builder/main.py`**

At line 607 area (system type entry labels) add Store MQTT Broker section row. At line 620 area, add system type field. At lines 1419-1468 (component detection defaults), include `"MQTT-BROKER"` in lists. At line 1534/1546 (component checkbox display name), add `("MQTT-BROKER", "Store MQTT Broker")` entry.

Use grep to enumerate:
```bash
grep -n "RCS-SERVICE\|rcs_service\|rcs_system_type\|RCS Service" gk_install_builder/main.py
```
For each match, add a parallel MQTT-BROKER line.

- [ ] **Step 12.6: Run tests to verify pass**

```bash
pytest tests/unit/test_auto_fill.py::test_mqtt_broker_system_type_auto_filled tests/unit/test_version_management.py -k mqtt_broker -v
```
Expected: PASS.

- [ ] **Step 12.7: Commit**

```bash
git add gk_install_builder/main.py gk_install_builder/features/auto_fill.py gk_install_builder/features/version_manager.py tests/unit/test_auto_fill.py
git commit -m "feat(mqtt-broker): UI section + auto-fill + version manager"
```

---

## Task 13: Dialogs (detection_settings, launcher_settings, offline_package, about)

**Files:**
- Modify: `gk_install_builder/dialogs/detection_settings.py:493`
- Modify: `gk_install_builder/dialogs/launcher_settings.py:57,98,124,154,158-161,418`
- Modify: `gk_install_builder/dialogs/offline_package.py:242,262,386-403,1675,1708-1709`
- Modify: `gk_install_builder/dialogs/about.py:215`

- [ ] **Step 13.1: Enumerate references**

```bash
grep -n "RCS-SERVICE\|rcs_service\|RCS Service" gk_install_builder/dialogs/detection_settings.py gk_install_builder/dialogs/launcher_settings.py gk_install_builder/dialogs/offline_package.py gk_install_builder/dialogs/about.py
```

- [ ] **Step 13.2: Add MQTT-BROKER parallels in detection_settings.py**

At line 493 (component list/dict), add `"MQTT-BROKER"` and / or `("MQTT-BROKER", "Store MQTT Broker")`. Mirror RCS entry structure.

- [ ] **Step 13.3: Add MQTT-BROKER tab in launcher_settings.py**

For every RCS reference, add MQTT-BROKER sibling. Specifically:
- Tab definition (line 57 area)
- Settings extraction (line 98, 124)
- Save logic (line 154, 158-161)
- Display label (line 418): `"Store MQTT Broker"`

- [ ] **Step 13.4: Add MQTT-BROKER to offline_package.py**

Lines 242, 262, 386-403 — component checkbox, download dispatch. Add MQTT-BROKER entries paralleling RCS. Line 1675, 1708-1709 — additional check/dispatch.

- [ ] **Step 13.5: Append to about.py component list**

Line 215 area — append `"Store MQTT Broker"` to the displayed components list.

- [ ] **Step 13.6: Smoke test**

```bash
pytest tests/ -x --tb=short 2>&1 | tail -30
```
Expected: existing tests pass, MQTT tests pass.

- [ ] **Step 13.7: Commit**

```bash
git add gk_install_builder/dialogs/
git commit -m "feat(mqtt-broker): dialog component-list updates"
```

---

## Task 14: api_client.py (FP/FPD + Config-Service)

**Files:**
- Modify: `gk_install_builder/integrations/api_client.py:177-185` (versions init), `:287-296` (FP property dispatch), `:373-376` (FPD dispatch), `:592-600` (system_types dict), `:598` (Config-Service)

- [ ] **Step 14.1: Write failing test**

Add to `tests/unit/test_fp_fpd_coverage.py`:

```python
def test_mqtt_broker_in_versions_init():
    import inspect
    from gk_install_builder.integrations import api_client
    source = inspect.getsource(api_client)
    assert '"MQTT-BROKER": {"value": None, "source": None}' in source

def test_mqtt_broker_property_ids_dispatched():
    import inspect
    from gk_install_builder.integrations import api_client
    source = inspect.getsource(api_client)
    assert "StoreMQTTBroker_Version" in source
    assert "StoreMQTTBroker_Update_Version" in source

def test_mqtt_broker_in_config_service_system_types():
    import inspect
    from gk_install_builder.integrations import api_client
    source = inspect.getsource(api_client)
    assert '"MQTT-BROKER": self.config_manager.config.get("mqtt_broker_system_type"' in source
```

- [ ] **Step 14.2: Run tests to verify fail**

```bash
pytest tests/unit/test_fp_fpd_coverage.py -k mqtt_broker -v
```
Expected: FAIL.

- [ ] **Step 14.3: Edit `gk_install_builder/integrations/api_client.py`**

At line 184, in `versions` init dict, after `"RCS-SERVICE": {"value": None, "source": None}`, add:
```python
                "RCS-SERVICE": {"value": None, "source": None},
                "MQTT-BROKER": {"value": None, "source": None}
```
(Add comma after RCS entry.)

At line 293-296, after the RCS FP elif:
```python
                            # MQTT Broker: try Version first, fallback to Update_Version
                            elif prop_id in ["StoreMQTTBroker_Version", "StoreMQTTBroker_Update_Version"] and value:
                                if versions["MQTT-BROKER"]["value"] is None or prop_id == "StoreMQTTBroker_Version":
                                    versions["MQTT-BROKER"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched MQTT Broker ({prop_id}): {value}")
```

In the FPD branch (~line 373-376 area), add the same elif for FPD scope (use the actual FPD pattern in the file — look for the existing RCS FPD branch and clone). The FPD assignment uses `"FPD (Default)"` as source per existing convention.

At line 599, in `system_types` dict, after `"RCS-SERVICE": self.config_manager.config.get("rcs_system_type", "GKR-Resource-Cache-Service")`, add:
```python
                "RCS-SERVICE": self.config_manager.config.get("rcs_system_type", "GKR-Resource-Cache-Service"),
                "MQTT-BROKER": self.config_manager.config.get("mqtt_broker_system_type", "GKR-Store-MQTT-Broker")
```

- [ ] **Step 14.4: Run tests to verify pass**

```bash
pytest tests/unit/test_fp_fpd_coverage.py -k mqtt_broker -v
```
Expected: PASS.

- [ ] **Step 14.5: Commit**

```bash
git add gk_install_builder/integrations/api_client.py tests/unit/test_fp_fpd_coverage.py
git commit -m "feat(mqtt-broker): FP/FPD + Config-Service API dispatch"
```

---

## Task 15: Installer overrides test parity

**Files:**
- Verify: `tests/unit/test_installer_overrides.py`

- [ ] **Step 15.1: Add MQTT-BROKER override test**

Add:
```python
def test_mqtt_broker_override_xml_generated(tmp_path, full_windows_config):
    from gk_install_builder.generator import ProjectGenerator
    pg = ProjectGenerator(config=full_windows_config, output_dir=str(tmp_path))
    pg.generate()
    override = tmp_path / "helper" / "structure" / "installer_overrides.mqtt-broker.xml"
    # Or wherever override XMLs land — check existing RCS override location
    # If override file naming uses different scheme, adjust path
    assert override.exists() or any("mqtt-broker" in p.name.lower() for p in (tmp_path / "helper" / "structure").rglob("*.xml"))
```

- [ ] **Step 15.2: Run + iterate**

```bash
pytest tests/unit/test_installer_overrides.py -k mqtt_broker -v
```

If fails because Task 4 didn't add the XML filename to `gen_config/generator_config.py:205-227` override map, go back and add `installer_overrides.mqtt-broker.xml` there. Re-run.

- [ ] **Step 15.3: Commit**

```bash
git add gk_install_builder/gen_config/generator_config.py tests/unit/test_installer_overrides.py
git commit -m "feat(mqtt-broker): installer override XML wiring"
```

---

## Task 16: Full regression + manual smoke test

- [ ] **Step 16.1: Full test suite**

```bash
pytest tests/ -v 2>&1 | tail -50
```
Expected: All 187+ existing tests pass, plus new MQTT-BROKER cases pass. If any RCS-SERVICE test now fails, a clone-step swapped an identifier incorrectly — fix before proceeding.

- [ ] **Step 16.2: Manual smoke test**

Run the app and generate a package:
```bash
python -m gk_install_builder.main
```

In the UI:
1. Enter base URL `test.cse.cloud4retail.co`
2. Verify "Store MQTT Broker" section appears in Project Configuration
3. Verify `mqtt_broker_system_type` auto-fills to `GKR-Store-MQTT-Broker`
4. Verify Store MQTT Broker checkbox in component selection
5. Click Generate
6. Inspect output directory:
   ```bash
   grep -l "MQTT-BROKER" <output_dir>/GKInstall.ps1 <output_dir>/GKInstall.sh
   ls <output_dir>/helper/launchers/launcher.store-mqtt-broker-service.template
   ls <output_dir>/helper/onboarding/store-mqtt-broker-service.onboarding.json
   ```
7. Verify generated `GKInstall.ps1` contains:
   ```
   'MQTT-BROKER' { "MQTT.station" }
   ```
8. Verify onboarding JSON contains `"clientType": "store-mqtt-broker"`.

- [ ] **Step 16.3: API dialog smoke test**

In the running app, open "Test API" dialog (Config-Service test). Verify:
- "MQTT-BROKER" row appears in results
- POST body includes `"systemName": "GKR-Store-MQTT-Broker"`
- Response (if reachable) shows version list or "No versions found"

- [ ] **Step 16.4: Final commit (if any cleanup needed)**

If smoke test surfaces any small fixes, address them and commit:
```bash
git add -p
git commit -m "fix(mqtt-broker): smoke-test corrections"
```

---

## Self-Review Notes

**Spec coverage check:**
- §2 Identifiers — Glossary at plan top covers every identifier; Tasks 1, 2, 5-14 use them.
- §3.1 Config/defaults — Task 1.
- §3.2 UI — Task 12.
- §3.3 Generators — Tasks 5, 6, 7, 8, 9.
- §3.4 Templates — Tasks 10, 11.
- §3.5 Detection/dialogs — Tasks 2, 13.
- §3.6 Integration (api_client) — Task 14.
- §3.7 Tests — Tasks 1.1, 2.1, 3, 5.1, 6.1, 7.1, 8.1, 10.1, 12.1, 14.1, 15.1.
- §4 Templates & placeholders — Tasks 6, 10.
- §5 Data flow — implicit across Tasks 5-12.
- §6 Error handling — RCS clone preserves all existing handlers; no new task needed.
- §7 Testing strategy — Tasks 1-15 each contain TDD cycle; Task 16 is full regression + smoke.

**Placeholder scan:** all code blocks contain concrete code. Grep statements provided where line-exact location may have shifted due to upstream edits.

**Type consistency:** `mqtt_broker_*` config keys consistent. `MQTT-BROKER` internal key consistent. `store-mqtt-broker-service` slug consistent. `clientType=store-mqtt-broker` (no `-service` suffix in onboarding clientType per user spec).

**Known soft spots:**
- Tasks 10/11 use grep-driven enumeration because the templates contain dozens of RCS references at line numbers that may have shifted; the worker must use grep output as the authoritative location list, not the line numbers cited in this plan.
- Test fixture line numbers (Task 3) are unknown; worker must locate RCS entries via grep first.
