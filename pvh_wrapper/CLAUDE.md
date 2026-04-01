# PVH Wrapper - Development Context

## What This Is

PVH is migrating from `PVH-OPOS-FAT-*` to `PVH-OPOS-ONEX-CLOUD-*` system types. DSG still serves packages under the old FAT names. These wrapper scripts auto-detect store/workstation from hostname, look up the FAT system type from a mapping file, transform FAT -> ONEX-CLOUD, and call GKInstall with `--SystemNameOverride` and `--WorkstationNameOverride`.

## File Overview

| File | Status | Description |
|------|--------|-------------|
| `PVH-GKInstall.ps1` | Done | PowerShell wrapper |
| `PVH-GKInstall.sh` | Done | Bash wrapper |
| `pvh_store_mapping.properties` | Gitignored | QA mapping (49 stores from `table_result.csv`) |
| `pvh_store_mapping_prod.properties` | Gitignored | Production mapping (415 stores from `prod_csv.csv`) |
| `pvh_store_mapping.properties.example` | Tracked | Template for customers |
| `queries.sql` | Tracked | SQL queries for Store Manager DB (sm_pvhprd / sm_qa2) |
| `README.md` | Done | Usage documentation |
| `prod_csv.csv` | Gitignored | Raw production data (1,112 workstations, 415 stores) |

## Key Design Decisions

### Hostname Parsing
- **Confirmed production format**: `[CC-]{4-char prefix}TILL{2-digit}[T]`
  - `CC-` = optional country code prefix (e.g., `DE-`), ignored
  - Trailing `T` = optional test environment marker, ignored
  - Examples: `DE-A319TILL01`, `DE-A319TILL01T`, `A319TILL01`
- **PS1 regex**: `^(?:[A-Za-z]{2}-)?([A-Za-z][A-Za-z0-9]{3})TILL(\d{2})T?$`
- **SH regex**: `^([A-Za-z]{2}-)?([A-Za-z][A-Za-z0-9]{3})TILL([0-9]{2})(T?)$`
  - Bash ERE doesn't support non-capturing groups, so capture indices are shifted (store=2, till=3)
- All production prefixes are exactly 4 chars (letter + 3 alphanumeric)
- Till numbers always 2 digits (01-15 range observed)

### Workstation Derivation
- **Workstation ID**: `100 + till_number` (TILL01 -> 101)
- **Workstation Name**: `{storePrefix}_OneXPOS{tillNumber}` (A319_OneXPOS1)

### FAT -> ONEX-CLOUD Transformation
- Simple string replacement: `FAT` -> `ONEX-CLOUD` in system type name
- Example: `PVH-OPOS-FAT-EN_GB-TH-FULL` -> `PVH-OPOS-ONEX-CLOUD-EN_GB-TH-FULL`
- All 62 FAT types used in production have verified ONEX-CLOUD counterparts

### Store Mapping
- One mapping per store (store_prefix=FAT_system_type)
- Production has zero mixed types (all workstations in a store use same system type)
- QA has 6 stores with mixed types (minor misconfigs, not a concern)

### Post-Install Health Check
- **Purpose**: Verify ONEX installation is functional even when GKInstall exits 0
- **Configurable**: `$enableHealthCheck` / `ENABLE_HEALTH_CHECK` (default: true)
- **CLI override**: `-SkipHealthCheck` (PS1) / `--skip-health-check` (bash)
- **Checks (sequential, fail-fast)**:
  1. `C:\gkretail\onex` folder exists (immediate)
  2. `C:\gkretail\onex\station.properties` file exists (immediate)
  3. Java process listening on port 3333 (poll every 30s, up to 10min)
- **On failure**: Sets `$gkInstallFailed = $true` and triggers existing rollback logic
- **Paths configurable**: `$healthCheckOnexPath`, `$healthCheckStationFile`, `$healthCheckPort`

## Pending Items (Waiting on Colleague)

### 1. Hostname Format ~~Confirmation~~ CONFIRMED
- **Confirmed**: Production format is `[CC-]{4-char}TILL{2-digit}[T]` e.g., `DE-A319TILL01`
- Country prefix (`DE-`) is ignored, trailing `T` (test env) is ignored
- Regex updated in both scripts to handle all variants

### 2. Workstation Naming Convention
- **Decision: Use hostname format** (`A319TILL01`) — PVH prefers keeping the hostname as the workstation name
- Scripts need updating: change from `{prefix}_OneXPOS{till}` to `{prefix}TILL{till:02d}`
  - PS1:145 -> `$workstationName = "${storePrefix}TILL$('{0:D2}' -f $tillNumber)"`
  - SH:182 -> `workstation_name="${store_prefix}TILL${till_number}"`

### 3. Workstation ID Formula
- Current: `100 + till_number` (TILL01 -> 101)
- Verify this matches PVH's existing convention

## Production Data Analysis Summary

- **415 unique stores** across 62 FAT system types
- **1,112 workstations** total
- **Zero mixed types** per store (safe for per-store mapping)
- **Store prefix patterns**: A+3digits (218), AA+2digits (142), F-prefix (~30), others
- **Countries**: DE_AT, DE_DE, DE_CH, EN_GB, EN_NL, FR_FR, IT_IT, ES_ES, EN_PL, EN_CZ, PT_PT, EN_BE, FR_BE, EN_SE, EN_DK, EN_NO, EN_FI, EN_IE, EN_HR, FR_CH, IT_CH, FR_LU, RU_RU, TR_TR
- **Brands**: TH (Tommy Hilfiger), CK (Calvin Klein)
- **Types**: FULL, OUTLET

## SQL Queries (queries.sql)

1. **Node listing** - Get all POS workstation nodes with system type and parent store
2. **System types** - Get all PVH-OPOS system types defined in Store Manager
3. **Mixed type detection** - Find stores where workstations have different system types

All queries default to `sm_pvhprd` (production) with `sm_qa2` (QA) as commented alternatives.

## Testing

```powershell
# PowerShell dry-run test
.\PVH-GKInstall.ps1 -HostnameOverride "A319TILL01" -WhatIf

# Test with production mapping (copy prod file first)
copy pvh_store_mapping_prod.properties pvh_store_mapping.properties
.\PVH-GKInstall.ps1 -HostnameOverride "A143TILL02" -WhatIf

# Test with health check disabled
.\PVH-GKInstall.ps1 -HostnameOverride "A319TILL01" -SkipHealthCheck -WhatIf
```

```bash
# Bash dry-run test
./PVH-GKInstall.sh --hostname-override "A319TILL01" --dry-run

# Bash with health check disabled
./PVH-GKInstall.sh --hostname-override "A319TILL01" --skip-health-check --dry-run
```

## Git State

- Branch: `feature/pvh-customization`
- Commits:
  - `2de8b37` - Initial wrapper scripts, mapping, README, gitignore
  - `53ec7a7` - Production hostname format update, SQL queries, README/gitignore/.properties.example updates
  - `554a4d6` - Added `--SystemNameOverride` and `--WorkstationNameOverride` to generated install scripts
- Working tree: clean
