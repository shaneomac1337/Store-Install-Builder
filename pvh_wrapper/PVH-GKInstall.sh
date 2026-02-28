#!/bin/bash
#
# PVH wrapper for GKInstall.sh - auto-detects store, system type, and workstation from hostname.
#
# Reads the hostname, parses it into store prefix + till number, looks up the FAT system type
# from a mapping file, transforms FAT -> ONEX-CLOUD, and calls GKInstall.sh with the correct
# --SystemNameOverride and --WorkstationNameOverride parameters.
#
# Hostname format: [CC-]{StorePrefix}TILL{TillNumber}[T]
# Examples: DE-A319TILL01, DE-A319TILL01T, A319TILL01
#
# Usage:
#   ./PVH-GKInstall.sh                        # Auto-detect everything
#   ./PVH-GKInstall.sh --ComponentType ONEX-POS --offline
#   ./PVH-GKInstall.sh --dry-run              # Show parsed values without executing
#   ./PVH-GKInstall.sh --hostname-override A319TILL01 --dry-run     # Test with specific hostname

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================
# CONFIGURABLE HOSTNAME PATTERN
# Adjust this regex if the hostname format changes.
# Production format: [CC-]{4-char prefix}TILL{2-digit number}[T]
#   e.g., DE-A319TILL01, DE-A319TILL01T, A319TILL01
# Optional country prefix (CC-) is ignored. Optional trailing T (test env) is ignored.
# Capture groups: (1) country prefix or empty, (2) store prefix (4 chars), (3) till number (2 digits), (4) T or empty
# ============================================================
HOSTNAME_PATTERN='^([A-Za-z]{2}-)?([A-Za-z][A-Za-z0-9]{3})TILL([0-9]{2})(T?)$'

# ============================================================
# DEFAULTS
# ============================================================
MAPPING_FILE="pvh_store_mapping.properties"
COMPONENT_TYPE="ONEX-POS"
DRY_RUN=false
HOSTNAME_OVERRIDE=""
PASSTHROUGH_ARGS=()

# ============================================================
# PARSE WRAPPER ARGUMENTS
# Separate PVH-specific args from GKInstall pass-through args.
# ============================================================
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run|--DryRun)
            DRY_RUN=true
            shift
            ;;
        --mapping-file|--MappingFile)
            MAPPING_FILE="$2"
            shift 2
            ;;
        --hostname-override|--HostnameOverride)
            HOSTNAME_OVERRIDE="$2"
            shift 2
            ;;
        --ComponentType)
            COMPONENT_TYPE="$2"
            PASSTHROUGH_ARGS+=("$1" "$2")
            shift 2
            ;;
        --offline)
            PASSTHROUGH_ARGS+=("$1")
            shift
            ;;
        --storeId|--StoreID|--workstationId|--WorkstationID|--SystemNameOverride|--WorkstationNameOverride)
            # Skip these - the wrapper sets them automatically
            echo "[PVH] WARNING: Ignoring $1 (set automatically by wrapper)" >&2
            shift 2
            ;;
        --UseDefaultVersions|--noOverrides|--skipCheckAlive|--skipStartApplication|--list-environments)
            PASSTHROUGH_ARGS+=("$1")
            shift
            ;;
        --base_url|--VersionSource|--VersionOverride|--versionOverride|--rcsUrl|-e|--env|--environment|--SslPassword)
            PASSTHROUGH_ARGS+=("$1" "$2")
            shift 2
            ;;
        *)
            # Pass through any unknown args to GKInstall
            PASSTHROUGH_ARGS+=("$1")
            shift
            ;;
    esac
done

# ============================================================
# 1. GET HOSTNAME
# ============================================================
if [ -n "$HOSTNAME_OVERRIDE" ]; then
    pvh_hostname="$HOSTNAME_OVERRIDE"
    echo "[PVH] Using hostname override: $pvh_hostname"
else
    pvh_hostname="$(hostname)"
fi

echo ""
echo "========================================"
echo " PVH GKInstall Wrapper"
echo "========================================"
echo "[PVH] Hostname: $pvh_hostname"

# ============================================================
# 2. PARSE HOSTNAME
# ============================================================
if [[ "$pvh_hostname" =~ $HOSTNAME_PATTERN ]]; then
    store_prefix="${BASH_REMATCH[2]}"
    till_number="${BASH_REMATCH[3]}"
    # Strip leading zeros for arithmetic
    till_number_int=$((10#$till_number))
else
    echo ""
    echo "[PVH] ERROR: Hostname '$pvh_hostname' does not match expected pattern." >&2
    echo "[PVH] Expected format: [CC-]{StorePrefix}TILL{TillNumber}[T]" >&2
    echo "[PVH] Examples: DE-A319TILL01, DE-A319TILL01T, A319TILL01" >&2
    echo "[PVH] Pattern: $HOSTNAME_PATTERN" >&2
    echo "" >&2
    echo "[PVH] To test with a different hostname, use: --hostname-override 'DE-A319TILL01'" >&2
    exit 1
fi

echo "[PVH] Parsed -> Store: $store_prefix | Till: $till_number_int"

# ============================================================
# 3. READ MAPPING FILE
# ============================================================
mapping_path="$SCRIPT_DIR/$MAPPING_FILE"

if [ ! -f "$mapping_path" ]; then
    echo "" >&2
    echo "[PVH] ERROR: Mapping file not found: $mapping_path" >&2
    echo "[PVH] Create the file with store-to-system-type mappings." >&2
    echo "[PVH] Format: STORE_PREFIX=PVH-OPOS-FAT-LOCALE-BRAND-TYPE" >&2
    echo "[PVH] Example: A319=PVH-OPOS-FAT-EN_GB-TH-FULL" >&2
    echo "" >&2
    echo "[PVH] See pvh_store_mapping.properties.example for a template." >&2
    exit 1
fi

declare -A mapping
store_count=0
while IFS= read -r line || [ -n "$line" ]; do
    # Trim whitespace
    line="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    # Skip empty lines and comments
    if [ -z "$line" ] || [[ "$line" == \#* ]]; then
        continue
    fi
    key="${line%%=*}"
    value="${line#*=}"
    key="$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    value="$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    mapping["$key"]="$value"
    ((store_count++))
done < "$mapping_path"

echo "[PVH] Loaded $store_count store mappings from $MAPPING_FILE"

# ============================================================
# 4. LOOKUP STORE + TRANSFORM FAT -> ONEX-CLOUD
# ============================================================
fat_system_name="${mapping[$store_prefix]:-}"

if [ -z "$fat_system_name" ]; then
    echo "" >&2
    echo "[PVH] ERROR: Store '$store_prefix' not found in mapping file." >&2
    echo "[PVH] Available stores:" >&2
    for key in $(echo "${!mapping[@]}" | tr ' ' '\n' | sort); do
        echo "  $key  =  ${mapping[$key]}" >&2
    done
    echo "" >&2
    echo "[PVH] Add the store to $mapping_path and try again." >&2
    exit 1
fi

onex_system_name="${fat_system_name//FAT/ONEX-CLOUD}"

# ============================================================
# 5. DERIVE WORKSTATION ID AND NAME
# ============================================================
workstation_id=$((100 + till_number_int))                      # TILL01 -> 101
workstation_name="${store_prefix}TILL$(printf '%02d' "$till_number_int")"  # A319TILL01

# ============================================================
# 6. DISPLAY SUMMARY
# ============================================================
echo ""
echo "----------------------------------------"
echo " Resolved Values:"
echo "----------------------------------------"
echo "  Store ID:           $store_prefix"
echo "  Till Number:        $till_number_int"
echo "  FAT System Name:    $fat_system_name"
echo "  ONEX System Name:   $onex_system_name"
echo "  Workstation ID:     $workstation_id"
echo "  Workstation Name:   $workstation_name"
echo "  Component Type:     $COMPONENT_TYPE"
echo "----------------------------------------"
echo ""

# ============================================================
# 7. BUILD GKINSTALL ARGUMENTS
# ============================================================
gkinstall_args=(
    --storeId "$store_prefix"
    --workstationId "$workstation_id"
    --SystemNameOverride "$onex_system_name"
    --WorkstationNameOverride "$workstation_name"
)

# Append all pass-through arguments
gkinstall_args+=("${PASSTHROUGH_ARGS[@]}")

# ============================================================
# 8. EXECUTE GKINSTALL
# ============================================================
gkinstall_path="$SCRIPT_DIR/GKInstall.sh"

if [ ! -f "$gkinstall_path" ]; then
    echo "[PVH] ERROR: GKInstall.sh not found at: $gkinstall_path" >&2
    echo "[PVH] Place GKInstall.sh in the same directory as this wrapper." >&2
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    echo "[PVH] DRY RUN - Would execute:"
    echo "  $gkinstall_path ${gkinstall_args[*]}"
    echo ""
    echo "[PVH] Dry run complete. No changes were made."
    exit 0
fi

echo "[PVH] Calling GKInstall.sh..."
echo "[PVH] Command: GKInstall.sh ${gkinstall_args[*]}"
echo ""

exec "$gkinstall_path" "${gkinstall_args[@]}"
