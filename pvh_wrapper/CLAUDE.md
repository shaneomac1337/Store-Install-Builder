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
- **Current regex**: `^([A-Za-z][A-Za-z0-9]{3})TILL(\d{2})$`
- Based on production data analysis of 1,112 workstations
- All production prefixes are exactly 4 chars (letter + 3 alphanumeric)
- Till numbers always 2 digits (01-15 range observed)
- Regex is configurable at top of each script (line 56 in PS1, line 28 in SH)

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

## Pending Items (Waiting on Colleague)

### 1. Hostname Format Confirmation
- Current assumption based on prod DB data: `{4-char}TILL{2-digit}` e.g., `A319TILL01`
- Need colleague with machine access to confirm actual COMPUTERNAME / hostname
- If format differs, update regex in PS1 line 56 and SH line 28

### 2. Workstation Naming Convention
- Current: `A319_OneXPOS1` (matches typical GK convention)
- PVH may prefer keeping `A319TILL01` as the workstation name
- If so, change one line in each script:
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
```

```bash
# Bash dry-run test
./PVH-GKInstall.sh --hostname-override "A319TILL01" --dry-run
```

## Git State

- Branch: `feature/pvh-customization`
- Initial commit: `2de8b37` (wrapper scripts, mapping, README, gitignore)
- Uncommitted changes: hostname regex update (removed country suffix), queries.sql, README update, .gitignore update, .properties.example update
- These uncommitted changes should be committed once hostname format is confirmed
