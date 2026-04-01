#!/bin/bash
#
# PVH wrapper for GKInstall.sh - auto-detects store ID and workstation ID from hostname.
#
# Reads the hostname, parses it into store prefix + till number, derives storeId and workstationId,
# and calls GKInstall.sh with --storeId, --workstationId, and -y parameters.
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
# CONFIGURABLE ENVIRONMENT
# Change this value when creating copies for other environments.
# Example: "PVHTST2" for test, "PVHPRD" for production
# ============================================================
PVH_ENVIRONMENT="PVHTST2"

# ============================================================
# DEFAULTS
# ============================================================
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
        --storeId|--StoreID|--workstationId|--WorkstationID)
            # Skip these - the wrapper sets them automatically
            echo "[PVH] WARNING: Ignoring $1 (set automatically by wrapper)" >&2
            shift 2
            ;;
        -y|--yes)
            # Skip - the wrapper always passes -y
            echo "[PVH] WARNING: Ignoring $1 (set automatically by wrapper)" >&2
            shift
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
# 3. DERIVE WORKSTATION ID
# ============================================================
workstation_id=$((100 + till_number_int))                      # TILL01 -> 101

# ============================================================
# 4. DISPLAY SUMMARY
# ============================================================
echo ""
echo "----------------------------------------"
echo " Resolved Values:"
echo "----------------------------------------"
echo "  Store ID:           $store_prefix"
echo "  Till Number:        $till_number_int"
echo "  Workstation ID:     $workstation_id"
echo "  Auto-Confirm:       Yes (-y)"
echo "  Component Type:     $COMPONENT_TYPE"
echo "  Environment:        $PVH_ENVIRONMENT"
echo "----------------------------------------"
echo ""

# ============================================================
# 5. BUILD GKINSTALL ARGUMENTS
# ============================================================
gkinstall_args=(
    --storeId "$store_prefix"
    --workstationId "$workstation_id"
    --env "$PVH_ENVIRONMENT"
    -y
)

# Append all pass-through arguments
gkinstall_args+=("${PASSTHROUGH_ARGS[@]}")

# ============================================================
# 6. EXECUTE GKINSTALL
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
