# Store MQTT Broker Component — Design Spec

**Date**: 2026-05-12
**Status**: Approved (brainstorming)
**Approach**: Clone RCS-SERVICE component pattern verbatim, rename to MQTT-BROKER

---

## 1. Goal

Add a new installable component "Store MQTT Broker" to GK Install Builder so generated installation packages can deploy a Tomcat+Java-based MQTT broker on retail store machines (Windows + Linux), with full parity to existing RCS-SERVICE wiring: detection, onboarding, launcher template, API integration, and tests.

## 2. Identifiers & Naming

| Aspect | Value |
|--------|-------|
| Display label (UI) | Store MQTT Broker |
| Internal component key | `MQTT-BROKER` |
| Onboarding `clientType` | `store-mqtt-broker` |
| Cloud system type | `GKR-Store-MQTT-Broker` |
| Config key prefix | `mqtt_broker_*` (`mqtt_broker_version`, `mqtt_broker_system_type`, `mqtt_broker_launcher_settings`) |
| File slug (launcher, onboarding JSON) | `store-mqtt-broker-service` |
| Install directory name | `store-mqtt-broker-service` (under `C:\gkretail\` / `/usr/local/gkretail/`) |
| Station file | `MQTT.station` |
| Tomcat service name (Windows) | `Tomcat-storemqttbrokerservice` |
| Updater service name (Windows) | `Updater-storemqttbrokerservice` |
| FP property ID | `StoreMQTTBroker_Version` |
| FPD property ID | `StoreMQTTBroker_Update_Version` |
| Config-Service `systemName` | `GKR-Store-MQTT-Broker` (POST body) |
| Default version | `v1.0.0` |
| Platforms supported | Windows + Linux |

## 3. File Touchpoints

### 3.1 Config & defaults

- `gk_install_builder/config.py` — add `"MQTT-BROKER": True` to component-enabled defaults dict; add `mqtt_broker_version`, `mqtt_broker_system_type` to default config schema.
- `gk_install_builder/default_versions.json` — add `StoreMQTTBroker_Version` + `StoreMQTTBroker_Update_Version` baseline entries with default `v1.0.0`.
- `gk_install_builder/gen_config/generator_config.py` — add `launcher.store-mqtt-broker-service.template` to launcher list, `store-mqtt-broker-service.onboarding.json` to onboarding list, structure entries paralleling RCS-SERVICE.

### 3.2 UI

- `gk_install_builder/main.py` — Store MQTT Broker section row (system type entry field), component checkbox in install selection, label strings.
- `gk_install_builder/features/auto_fill.py` — when user enters base URL, auto-populate `mqtt_broker_system_type` with `GKR-Store-MQTT-Broker`.
- `gk_install_builder/features/version_manager.py` — version row UI + FP property mapping for Store MQTT Broker.

### 3.3 Generators

- `gk_install_builder/generator.py` — append `launcher.store-mqtt-broker-service.template` and `store-mqtt-broker-service.onboarding.json` to file lists (lines around 466-468, 481, 537, 1089-1091).
- `gk_install_builder/generators/gk_install_generator.py` — extend `COMPONENT_SERVICE_CONFIG_MAP`, add detection file mapping (`MQTT-BROKER` → `MQTT.station`), add substitution tokens `@MQTT_BROKER_VERSION@`, `@MQTT_BROKER_SYSTEM_TYPE@`, `@MQTT_BROKER_INSTALL_DIR@`.
- `gk_install_builder/generators/helper_file_generator.py` — onboarding JSON generation branch + init config generation for MQTT-BROKER.
- `gk_install_builder/generators/launcher_generator.py` — read `mqtt_broker_launcher_settings` from config, add `"launcher.store-mqtt-broker-service.template"` to `template_files` dict, add MQTT default template in `create_default_template()`.
- `gk_install_builder/generators/onboarding_generator.py` — dispatch branch for MQTT-BROKER onboarding step.

### 3.4 Templates

- `gk_install_builder/templates/GKInstall.ps1.template` — add `'MQTT-BROKER' { "MQTT.station" }` to switch (line ~340-346), add MQTT-BROKER branches to component dispatch, version handling, launcher invocation.
- `gk_install_builder/templates/GKInstall.sh.template` — bash equivalent (case at line ~593-599, plus component dispatch branches).
- `gk_install_builder/templates/onboarding.ps1.template` — add `store-mqtt-broker-service.onboarding.json` to onboarding JSON list.
- `gk_install_builder/templates/onboarding.sh.template` — same as above for bash.
- `gk_install_builder/templates/store-initialization.ps1.template` — MQTT-BROKER branch parallel to RCS-SERVICE.
- `gk_install_builder/templates/store-initialization.sh.template` — bash equivalent.

### 3.5 Detection & dialogs

- `gk_install_builder/detection.py` — add `"MQTT-BROKER": "MQTT.station"` to `STATION_FILES` dict; add to component lists.
- `gk_install_builder/dialogs/detection_settings.py` — add Store MQTT Broker to component validation list.
- `gk_install_builder/dialogs/launcher_settings.py` — add Store MQTT Broker tab with same fields as RCS.
- `gk_install_builder/dialogs/offline_package.py` — component checkbox + download dispatch for MQTT-BROKER.
- `gk_install_builder/dialogs/about.py` — append Store MQTT Broker to component list.

### 3.6 Integration

- `gk_install_builder/integrations/api_client.py`:
  - Add `"MQTT-BROKER": self.config_manager.config.get("mqtt_broker_system_type", "GKR-Store-MQTT-Broker")` to `system_types` dict at line ~592-600 (auto-flows through Config-Service POST loop).
  - Add `StoreMQTTBroker_Version` to FP property dispatch.
  - Add `StoreMQTTBroker_Update_Version` to FPD property dispatch.

### 3.7 Tests

- `tests/conftest.py`, `tests/fixtures/generator_fixtures.py` — fixture data MQTT-BROKER entry.
- `tests/fixtures/configs/{minimal,full}_{windows,linux}.json` — `mqtt_broker_*` keys.
- `tests/unit/test_auto_fill.py`, `test_fp_fpd_coverage.py`, `test_generator_core.py`, `test_generator_file_ops.py`, `test_generator_integration.py`, `test_installer_overrides.py`, `test_service_installation.py`, `test_version_management.py` — one parametrized case per file mirroring RCS-SERVICE assertions.

## 4. Templates & Placeholders

### 4.1 New `@VARIABLE@` tokens

- `@MQTT_BROKER_VERSION@` — version string (e.g., `v1.0.0`)
- `@MQTT_BROKER_SYSTEM_TYPE@` — `GKR-Store-MQTT-Broker`
- `@MQTT_BROKER_INSTALL_DIR@` — absolute install path

### 4.2 Launcher template

File: `helper/launchers/launcher.store-mqtt-broker-service.template` — verbatim RCS clone, only header comment changes:

```
# Launcher defaults for Store MQTT Broker
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
```

Managed Tomcat ports: 8180 (HTTP) / 8543 (HTTPS). MQTT broker ports 1883 / 8883 are broker-internal defaults, not managed by installer.

### 4.3 Onboarding JSON

File: `helper/onboarding/store-mqtt-broker-service.onboarding.json` — RCS structural clone with `clientType=store-mqtt-broker`:

```json
{
  "tenantId": "@TENANT_ID@",
  "clientType": "store-mqtt-broker",
  "storeId": "@STORE_ID@",
  "workstationId": "@WORKSTATION_ID@",
  "username": "launchpad",
  "deviceId": "@DEVICE_ID@"
}
```

Exact field list mirrored from existing `rcs-service.onboarding.json` (no auth — RCS has no BA credentials, MQTT same).

## 5. Data Flow

### 5.1 Generation (user clicks "Generate")

1. `main.py` reads MQTT-BROKER checkbox + version from UI.
2. `config.py` persists `mqtt_broker_*` values (1s debounce auto-save).
3. `generator.py` orchestrates:
   - `gk_install_generator.py` replaces `@MQTT_BROKER_*@` tokens in GKInstall scripts.
   - `launcher_generator.py` writes `launcher.store-mqtt-broker-service.template` with user-overridden ports if any.
   - `helper_file_generator.py` writes `store-mqtt-broker-service.onboarding.json` + init configs.
   - `onboarding_generator.py` adds MQTT to onboarding script dispatch list.

### 5.2 Runtime (generated GKInstall executes on store machine)

1. Detection priority unchanged (5-tier system). At priority 3, GKInstall reads `MQTT.station` only when invoked with `componentType=MQTT-BROKER` (see Section 6 — detection is component-type-scoped, not global).
2. Component dispatch loop encounters MQTT-BROKER.
3. Version resolved via `@MQTT_BROKER_VERSION@` baked in.
4. Launcher invoked with `launcher.store-mqtt-broker-service.template` properties.
5. Onboarding posts `store-mqtt-broker-service.onboarding.json` (`clientType=store-mqtt-broker`) → cloud returns token → cached for installer.
6. Installer fetches Tomcat + Java + broker package → deploys to `<base>/store-mqtt-broker-service` → registers Windows service `Tomcat-storemqttbrokerservice` / `Updater-storemqttbrokerservice` (or systemd unit on Linux).

### 5.3 API integration

- **FP/FPD** (`api_client.py`): query `StoreMQTTBroker_Version` (FP scope) → fallback `StoreMQTTBroker_Update_Version` (FPD scope) per existing PRIA-1740 dispatch fix.
- **Config-Service** (`api_client.py:614-617`):
  - POST `https://{base_url}/api/config/services/rest/infrastructure/v1/versions/search` (new API)
  - POST `https://{base_url}/config-service/services/rest/infrastructure/v1/versions/search` (legacy API)
  - Body: `{"systemName": "GKR-Store-MQTT-Broker"}`
  - Response: `versionNameList` → sorted via `version_sorting.sort_versions()` → latest picked.

No new external systems. Broker registration uses existing Launchpad/onboarding endpoint same as RCS. No new KeePass entry. No new auth flow.

## 6. Error Handling & Edge Cases

### 6.1 Version resolution fallback chain

1. FP scope (`StoreMQTTBroker_Version`) — primary.
2. FPD scope (`StoreMQTTBroker_Update_Version`) — fallback if FP empty/404.
3. Config-Service `versionNameList` — alternate path when user picks Config-Service source.
4. `default_versions.json` value (`v1.0.0`) — final fallback.
5. Manual UI override — always wins if user typed value.

### 6.2 Generation-time errors

- Missing `mqtt_broker_system_type` in config → use default `GKR-Store-MQTT-Broker`, log warning.
- Missing launcher template file → `create_default_template()` writes baked-in default (existing pattern, `launcher_generator.py:171`).
- Onboarding JSON write failure → bubble exception same as RCS branches today.

### 6.3 Runtime (generated script) errors

- `MQTT.station` missing + no hostname match + no CLI param → falls through to manual input prompt (existing priority-4 behavior).
- Onboarding token fetch fails → installer aborts using same error path RCS uses.
- Tomcat service registration fails on Windows → existing `runAsService` error reporting applies.

### 6.4 API testing dialog errors

- 401 → token refresh, retry once (existing `DSGRestBrowser` pattern).
- 404 on FP → fallback to FPD scope (existing PRIA-1740 fix).
- Empty `versionNameList` → mark component as "No versions found", continue other components.

### 6.5 Detection edge cases (component coexistence)

Detection is component-type-scoped, not global:

- `GKInstall.ps1.template:340-346` — switch/case maps `componentType` → exact filename.
- `GKInstall.sh.template:593-599` — bash case equivalent.
- Running with `componentType=RCS-SERVICE` reads only `RCS.station`.
- Running with `componentType=MQTT-BROKER` reads only `MQTT.station`.

Both `.station` files can coexist on the same machine. Each install invocation filters by component type. New MQTT branch joins the existing switch — same isolation pattern. No new conflict logic needed.

### 6.6 No new error categories

Every failure mode maps to an existing handler from RCS-SERVICE.

## 7. Testing Strategy

### 7.1 Unit tests — one parametrized MQTT-BROKER case per file

| Test file | Assertion |
|-----------|-----------|
| `tests/unit/test_auto_fill.py` | `GKR-Store-MQTT-Broker` auto-populated from base URL |
| `tests/unit/test_fp_fpd_coverage.py` | `StoreMQTTBroker_Version` (FP) + `StoreMQTTBroker_Update_Version` (FPD) dispatched |
| `tests/unit/test_generator_core.py` | MQTT-BROKER → `MQTT.station` detection mapping in generated PS1+SH |
| `tests/unit/test_generator_file_ops.py` | `launcher.store-mqtt-broker-service.template` + `store-mqtt-broker-service.onboarding.json` written |
| `tests/unit/test_generator_integration.py` | Full-stack: enable MQTT-BROKER → output contains all expected files + tokens |
| `tests/unit/test_installer_overrides.py` | Override XML emitted for MQTT-BROKER |
| `tests/unit/test_service_installation.py` | `Tomcat-storemqttbrokerservice` / `Updater-storemqttbrokerservice` service names |
| `tests/unit/test_version_management.py` | Version override flow for `mqtt_broker_version` |

### 7.2 Fixtures updated

- `tests/fixtures/generator_fixtures.py` — MQTT-BROKER entry in component dict.
- `tests/conftest.py` — fixture config keys.
- `tests/fixtures/configs/{minimal,full}_{windows,linux}.json` — 4 files, `mqtt_broker_*` keys.

### 7.3 Manual smoke test (post-implementation)

1. Run app, enable Store MQTT Broker checkbox, generate package.
2. Inspect output dir: `GKInstall.ps1`/`.sh` contains MQTT-BROKER branch, `launcher.store-mqtt-broker-service.template` exists, `store-mqtt-broker-service.onboarding.json` exists.
3. Grep generated `GKInstall.ps1` for `'MQTT-BROKER' { "MQTT.station" }`.
4. Test API dialog: Config-Service lookup returns versions for `GKR-Store-MQTT-Broker`.

### 7.4 Success criteria

- All 187+ existing tests still pass.
- New MQTT-BROKER test cases pass.
- Manual smoke test produces functionally-complete output package.

## 8. Out of Scope

- Refactoring RCS/Flow/MQTT into shared `tomcat-service` base class (approach C from brainstorm).
- Changing MQTT-internal ports 1883/8883 (broker config concern, not installer concern).
- Adding KeePass credentials (MQTT, like RCS, has no auth).
- Adding new external APIs beyond existing Launchpad/Config-Service.
