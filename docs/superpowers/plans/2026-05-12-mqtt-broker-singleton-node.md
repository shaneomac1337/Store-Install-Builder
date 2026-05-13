# MQTT Broker Singleton Node — Implementation Plan

**Date:** 2026-05-12
**Baseline:** 04a6836
**Scope:** Make MQTT-BROKER component a store-level singleton node. No workstationId in node creation, no WSID prompt during install, duplicate detection by systemName.

## Context

MQTT broker is a singleton per store. Product UI POSTs `/api/config/services/rest/infrastructure/v1/structure/nodes` for MQTT with body:
```json
{
  "parentNode": {"tenantId":"001","retailStoreId":"9909","systemName":"GKR-Store"},
  "newNode": {"systemName":"GKR-Store-MQTT-Broker","name":"Store MQTT Broker"},
  "user": "gk01ag"
}
```
No `workstationId` in `newNode`. Existing tool body always includes `workstationId`, which causes 404 / wrong-shape rejection for MQTT.

RCS + every other component stay unchanged. Only MQTT-BROKER diverges.

## Locked Design Decisions

- New template file `create_structure_mqtt-broker.json` (no workstationId placeholder)
- Store-init dispatches template by componentType (existing branch pattern)
- Duplicate detection matches by `systemName == "GKR-Store-MQTT-Broker"` for MQTT (3 sites PS1, 8+ sites SH)
- GKInstall skips WSID prompt for MQTT-BROKER (full drop, no default surrogate)
- `name` field hardcoded `"Store MQTT Broker"` for MQTT (already in `@STATION_NAME@` switch)
- `MQTT.station` env-marker file stays unchanged
- `WorkstationNameOverride` CLI flag effectively no-op for MQTT (no workstation to rename)
- `StructureUniqueNameOverride` CLI flag still applied to MQTT newNode
- `SystemNameOverride` still applies (override `GKR-Store-MQTT-Broker`)
- `parentNode.systemName` hardcoded `"GKR-Store"`
- Onboarding flow stays as-is

## Tasks

### Task 1 — Generate `create_structure_mqtt-broker.json` template
**Files:** `gk_install_builder/generators/helper_file_generator.py`
**Test first:** `tests/unit/test_generator_file_ops.py` — add `test_mqtt_broker_structure_template_no_workstationid`. Assert file written to `helper/structure/create_structure_mqtt-broker.json`, body has `parentNode.systemName="GKR-Store"`, `newNode.systemName="@SYSTEM_TYPE@"`, `newNode.name="@STATION_NAME@"`, `user="@USER_ID@"`, and `newNode` does NOT contain key `workstationId`.
**Implement:** In `create_structure_template()`, after writing `create_structure.json`, write second file `create_structure_mqtt-broker.json` with MQTT-shaped body.
**Commit:** `feat(mqtt-broker): emit singleton create_structure_mqtt-broker.json template`

### Task 2 — `gen_config/generator_config.py` register new helper file
**Files:** `gk_install_builder/gen_config/generator_config.py`
**Test first:** Existing structure-listing test or add assertion that HELPER_STRUCTURE / equivalent includes `structure/create_structure_mqtt-broker.json` (read source of truth from gen_config).
**Implement:** Add entry so the file is recognized as part of generated output.
**Commit:** `feat(mqtt-broker): register create_structure_mqtt-broker.json in HELPER_STRUCTURE`

### Task 3 — Store-init template selection (PS1)
**Files:** `gk_install_builder/templates/store-initialization.ps1.template`
**Test first:** `tests/unit/test_generator_integration.py` — extend MQTT test class: render store-init, grep for `if ($ComponentType -eq 'MQTT-BROKER')` template-path branch loading `create_structure_mqtt-broker.json`.
**Implement:** Replace the static `$createStructureTemplate = Join-Path $basePath "helper\structure\create_structure.json"` with conditional that picks MQTT template for MQTT-BROKER, default otherwise.
**Commit:** `feat(mqtt-broker): PS1 store-init selects MQTT template by componentType`

### Task 4 — Store-init template selection (SH)
**Files:** `gk_install_builder/templates/store-initialization.sh.template`
**Test first:** Same pattern, assert SH template contains `if [ "$COMPONENT_TYPE" = "MQTT-BROKER" ]` template-path branch.
**Implement:** Mirror Task 3 conditional in bash.
**Commit:** `feat(mqtt-broker): SH store-init selects MQTT template by componentType`

### Task 5 — PS1 dup-check: match by systemName for MQTT
**Files:** `gk_install_builder/templates/store-initialization.ps1.template`
**Test first:** Test renders template, asserts dup-check loops at lines ~183/217/362 each contain MQTT-BROKER branch matching `item.systemName -eq $currentSystemName` instead of `item.workstationId`.
**Implement:** Add componentType-conditional in each of the 3 `foreach ($item in ... .childNodeList)` blocks.
**Commit:** `feat(mqtt-broker): PS1 dup-check by systemName for singleton`

### Task 6 — SH dup-check: match by systemName for MQTT
**Files:** `gk_install_builder/templates/store-initialization.sh.template`
**Test first:** Test renders SH template, asserts each `jq -r ".childNodeList[] | select(.workstationId == \"$WORKSTATION_ID\")"` and each `grep` fallback path has MQTT-BROKER branch using `systemName` filter.
**Implement:** Mirror PS1 changes. Roughly 8 sites — every jq + grep fallback pair (lines ~219-220, 240-241, 286, 289, 294, 297, 474-475, 491-492 per current source).
**Commit:** `feat(mqtt-broker): SH dup-check by systemName for singleton`

### Task 7 — GKInstall PS1: skip WSID prompt for MQTT
**Files:** `gk_install_builder/templates/GKInstall.ps1.template`
**Test first:** Test renders PS1, asserts that when ComponentType=MQTT-BROKER, WSID interactive prompt is bypassed; that store-init dispatch still occurs; and that `$WorkstationId` value (empty or unset) does not break downstream operations.
**Audit BEFORE implementing:**
- Grep every `$WorkstationId` / `$WorkstationID` usage in PS1
- Confirm service name path (`Tomcat-storemqttbrokerservice`) doesn't depend on WSID
- Confirm install dir for MQTT doesn't depend on WSID
- Confirm station file write path doesn't depend on WSID for MQTT
**Implement:** Add early-return in WSID detection ladder for MQTT-BROKER. WSID stays empty.
**Commit:** `feat(mqtt-broker): GKInstall PS1 skips WSID detection for singleton`

### Task 8 — GKInstall SH: skip WSID prompt for MQTT
**Files:** `gk_install_builder/templates/GKInstall.sh.template`
**Test first:** Same as Task 7 but for SH.
**Implement:** Mirror Task 7 bash side.
**Commit:** `feat(mqtt-broker): GKInstall SH skips WSID detection for singleton`

### Task 9 — `@WORKSTATION_ID@` substitution safety in MQTT template
**Files:** Store-init templates (PS1 + SH)
**Test first:** Render PS1 + SH, assert that the line `$processedContent -replace '@WORKSTATION_ID@', $WorkstationId` (and SH `sed` equivalent) is either:
  - skipped for MQTT-BROKER, OR
  - safe to run because MQTT template contains no `@WORKSTATION_ID@` placeholder
**Implement:** Either guard substitution with componentType branch, or rely on no-op (since MQTT template has no placeholder). Prefer no-op approach — less template surface area.
**Commit:** `test(mqtt-broker): verify @WORKSTATION_ID@ substitution safe for MQTT template`

### Task 10 — Cross-platform smoke + regression check
**Files:** Tests only
**Test first:** Run full suite. Confirm 387/387 still pass (or 387+ new with new tests).
**Implement:** N/A. If any non-MQTT test regresses, fix root cause before commit.
**Commit:** `test(mqtt-broker): final regression check after singleton migration`

### Task 11 — Manual integration test (user-side)
**Not committed.** User runs tool against `stage.cloud4retail.co`, selects MQTT-BROKER, runs install. Verify:
- No WSID prompt
- Node POST body matches Product curl shape (no workstationId)
- Re-install: dup-check finds existing MQTT node by systemName, skips POST
- Existing RCS install unchanged (no regression)

## Out of Scope
- Multi-broker / HA MQTT support
- API 409 retry logic
- StoreHub / Flow / LPA / Other singleton-vs-workstation classification

## Risks
- **R1:** Missing a SH match site → silent dup-detection failure → duplicate node POST per re-install. Mitigation: grep-driven test asserts ALL match sites have branch.
- **R2:** WSID drop in GKInstall breaks install path / service install dir for MQTT. Mitigation: audit before Task 7 implement.
- **R3:** SystemNameOverride for MQTT — if user passes `XYZ-Store-MQTT-Broker`, dup-check `$currentSystemName` resolves to that, still works. Verify via test.

## Sequencing Notes
- Tasks 1–2 independent (template + registration)
- Tasks 3–4 depend on Task 1 (template must exist)
- Tasks 5–6 independent of template tasks (logic-only)
- Tasks 7–8 independent of other tasks
- Task 9 quality gate after 1–8
- Task 10 final regression after all merged
