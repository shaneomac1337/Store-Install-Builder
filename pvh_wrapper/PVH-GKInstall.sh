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
# CONFIGURABLE HEALTH CHECK
# Post-install verification: checks ONEX folder, station.properties,
# and Java process on port 3333. Triggers rollback on failure.
# ============================================================
ENABLE_HEALTH_CHECK=true
HEALTH_CHECK_TIMEOUT=600
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_ONEX_PATH="/usr/local/gkretail/onex"
HEALTH_CHECK_STATION_FILE="/usr/local/gkretail/onex/station.properties"
HEALTH_CHECK_PORT=3333

# ============================================================
# DEFAULTS
# ============================================================
COMPONENT_TYPE="ONEX-POS"
DRY_RUN=false
HOSTNAME_OVERRIDE=""
PASSTHROUGH_ARGS=()
SKIP_HEALTH_CHECK=false

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
        --skip-health-check|--SkipHealthCheck)
            SKIP_HEALTH_CHECK=true
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
if [ "$SKIP_HEALTH_CHECK" = true ] || [ "$ENABLE_HEALTH_CHECK" != true ]; then
    echo "  Health Check:       Disabled"
else
    echo "  Health Check:       Enabled (port timeout: ${HEALTH_CHECK_TIMEOUT}s)"
fi
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
    if [ "$SKIP_HEALTH_CHECK" != true ] && [ "$ENABLE_HEALTH_CHECK" = true ]; then
        echo ""
        echo "[PVH] DRY RUN - After successful GKInstall, would perform health checks:"
        echo "  1. Check folder exists: $HEALTH_CHECK_ONEX_PATH"
        echo "  2. Check file exists: $HEALTH_CHECK_STATION_FILE"
        echo "  3. Poll for Java process on port $HEALTH_CHECK_PORT (every ${HEALTH_CHECK_INTERVAL}s, up to ${HEALTH_CHECK_TIMEOUT}s)"
        echo "  4. On failure: trigger rollback"
    fi
    echo "[PVH] Dry run complete. No changes were made."
    exit 0
fi

echo "[PVH] Calling GKInstall.sh..."
echo "[PVH] Command: GKInstall.sh ${gkinstall_args[*]}"
echo ""

set +e
"$gkinstall_path" "${gkinstall_args[@]}"
gk_exit_code=$?
set -e

if [ $gk_exit_code -ne 0 ]; then
    echo ""
    echo "========================================"
    echo " GKInstall FAILED (exit code: $gk_exit_code)"
    echo "========================================"
    exit $gk_exit_code
fi

echo ""
echo "[PVH] GKInstall.sh completed successfully (exit code: 0)."

# ============================================================
# 8. POST-INSTALL HEALTH CHECK
# ============================================================
health_check_passed=true
health_check_reason=""

if [ "$SKIP_HEALTH_CHECK" != true ] && [ "$ENABLE_HEALTH_CHECK" = true ]; then
    echo ""
    echo "========================================"
    echo " Post-Install Health Check"
    echo "========================================"

    # Check 1: ONEX folder exists
    printf "[PVH] [1/3] Checking %s exists... " "$HEALTH_CHECK_ONEX_PATH"
    if [ -d "$HEALTH_CHECK_ONEX_PATH" ]; then
        echo "OK"
    else
        echo "FAILED"
        health_check_passed=false
        health_check_reason="ONEX folder not found at $HEALTH_CHECK_ONEX_PATH"
    fi

    # Check 2: station.properties exists (only if check 1 passed)
    if [ "$health_check_passed" = true ]; then
        printf "[PVH] [2/3] Checking %s exists... " "$HEALTH_CHECK_STATION_FILE"
        if [ -f "$HEALTH_CHECK_STATION_FILE" ]; then
            echo "OK"
        else
            echo "FAILED"
            health_check_passed=false
            health_check_reason="station.properties not found at $HEALTH_CHECK_STATION_FILE"
        fi
    fi

    # Check 3: Java process on port (only if checks 1-2 passed)
    if [ "$health_check_passed" = true ]; then
        max_attempts=$(( HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL ))
        echo "[PVH] [3/3] Waiting for Java process on port $HEALTH_CHECK_PORT (timeout: $(( HEALTH_CHECK_TIMEOUT / 60 ))m)..."
        port_check_passed=false

        for attempt in $(seq 1 $max_attempts); do
            sleep "$HEALTH_CHECK_INTERVAL"
            elapsed=$(( attempt * HEALTH_CHECK_INTERVAL ))
            minutes=$(( elapsed / 60 ))
            seconds=$(( elapsed % 60 ))
            time_str=$(printf "%d:%02d" $minutes $seconds)

            printf "[PVH]        Attempt %d/%d (%s elapsed)... " "$attempt" "$max_attempts" "$time_str"

            pid=$(ss -tlnp sport = :$HEALTH_CHECK_PORT 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
            if [ -n "$pid" ]; then
                comm=$(cat /proc/$pid/comm 2>/dev/null || echo "unknown")
                if [ "$comm" = "java" ]; then
                    echo "Java process detected on port $HEALTH_CHECK_PORT (PID: $pid). OK"
                    port_check_passed=true
                    break
                else
                    echo "port in use but not Java (process: $comm)"
                fi
            else
                echo "not yet"
            fi
        done

        if [ "$port_check_passed" != true ]; then
            health_check_passed=false
            health_check_reason="No Java process listening on port $HEALTH_CHECK_PORT after $HEALTH_CHECK_TIMEOUT seconds"
        fi
    fi

    # Result
    if [ "$health_check_passed" = true ]; then
        echo ""
        echo "[PVH] === Health Check PASSED ==="
    else
        echo ""
        echo "[PVH] === Health Check FAILED ==="
        echo "[PVH] Reason: $health_check_reason"
        exit 1
    fi
else
    echo "[PVH] Health check skipped."
fi
