# PVH GKInstall Wrapper

Wrapper scripts that auto-detect store configuration from the hostname and call `GKInstall.ps1`/`GKInstall.sh` with the correct `--SystemNameOverride` and `--WorkstationNameOverride` parameters.

## Background

PVH is migrating from `PVH-OPOS-FAT-*` to `PVH-OPOS-ONEX-CLOUD-*` system types. DSG still serves packages under the old FAT names. These wrapper scripts handle the FAT-to-ONEX-CLOUD transformation automatically.

## Files

| File | Description |
|------|-------------|
| `PVH-GKInstall.ps1` | PowerShell wrapper (Windows) |
| `PVH-GKInstall.sh` | Bash wrapper (Linux) |
| `pvh_store_mapping.properties` | Store-to-system-type mapping (customer data, not tracked in git) |
| `pvh_store_mapping.properties.example` | Template for the mapping file |

## Setup

1. Copy the generated install scripts (`GKInstall.ps1`/`GKInstall.sh` and `helper/` directory) into this `pvh_wrapper/` directory.
2. Copy `pvh_store_mapping.properties.example` to `pvh_store_mapping.properties` and fill in your store data (or use the pre-populated version if available).

## Hostname Format

The wrapper parses the machine hostname to detect store and till information.

```
{StorePrefix}TILL{TillNumber}-{CountrySuffix}
```

| Part | Example | Description |
|------|---------|-------------|
| StorePrefix | `A319` | Store identifier (1 letter + 2-3 alphanumeric chars) |
| TILL | `TILL` | Literal separator |
| TillNumber | `01` | Two-digit till number |
| CountrySuffix | `BE` | Country code (available for future use) |

**Full example**: `A319TILL01-BE`

The hostname regex is configurable at the top of each script if the format differs.

## How It Works

1. **Parse hostname** -> extract store prefix (`A319`), till number (`01`), country (`BE`)
2. **Look up** the store's FAT system type from the mapping file -> `PVH-OPOS-FAT-EN_GB-TH-FULL`
3. **Transform** `FAT` to `ONEX-CLOUD` -> `PVH-OPOS-ONEX-CLOUD-EN_GB-TH-FULL`
4. **Derive workstation**:
   - Workstation ID: `100 + till_number` -> TILL01 = `101`, TILL15 = `115`
   - Workstation Name: `{store}_OneXPOS{till}` -> `A319_OneXPOS1`
5. **Call GKInstall** with `--SystemNameOverride`, `--WorkstationNameOverride`, `--storeId`, `--WorkstationId`

## Usage

### Windows (PowerShell)

```powershell
# Auto-detect everything from hostname
.\PVH-GKInstall.ps1

# With specific component type
.\PVH-GKInstall.ps1 -ComponentType ONEX-POS

# Offline mode
.\PVH-GKInstall.ps1 -offline

# Dry run (shows what would be passed without executing)
.\PVH-GKInstall.ps1 -WhatIf

# Test with a different hostname
.\PVH-GKInstall.ps1 -HostnameOverride "A319TILL01-BE" -WhatIf

# Pass through any GKInstall parameter
.\PVH-GKInstall.ps1 -VersionOverride "v5.27.1" -base_url "prod.pvh.cloud4retail.co"
```

### Linux (Bash)

```bash
# Auto-detect everything from hostname
./PVH-GKInstall.sh

# With specific component type
./PVH-GKInstall.sh --ComponentType ONEX-POS

# Offline mode
./PVH-GKInstall.sh --offline

# Dry run
./PVH-GKInstall.sh --dry-run

# Test with a different hostname
./PVH-GKInstall.sh --hostname-override "A319TILL01-BE" --dry-run

# Pass through any GKInstall parameter
./PVH-GKInstall.sh --VersionOverride "v5.27.1" --base_url "prod.pvh.cloud4retail.co"
```

## Mapping File Format

```properties
# Comments start with #
# Format: STORE_PREFIX=FAT_SYSTEM_TYPE
A319=PVH-OPOS-FAT-EN_GB-TH-FULL
A179=PVH-OPOS-FAT-DE_AT-CK-FULL
```

The wrapper automatically replaces `FAT` with `ONEX-CLOUD` in the system type string.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Hostname doesn't match pattern | Error with expected format examples |
| Mapping file not found | Error with path and setup instructions |
| Store not in mapping | Error listing all available stores |
| GKInstall.ps1/sh not found | Error with placement instructions |

## Customization

The hostname regex is defined at the top of each script:

```powershell
# PowerShell
$hostnamePattern = '^([A-Za-z][A-Za-z0-9]{2,3})TILL(\d{2})-(\w+)$'
```

```bash
# Bash
HOSTNAME_PATTERN='^([A-Za-z][A-Za-z0-9]{2,3})TILL([0-9]{2})-([A-Za-z]+)$'
```

Modify these patterns if the hostname format differs from the expected `{StorePrefix}TILL{TillNumber}-{CountrySuffix}` convention.
