#!/bin/bash
# ============================================================================
# On-demand hostname detection test
#
# Spins up a Docker container per hostname, mounts the generated install dir,
# and runs: cd /install && ./GKInstall.sh --ComponentType ONEX
#
# Usage:
#   ./scripts/test-hostname.sh                          # All NEXA test cases
#   ./scripts/test-hostname.sh RO93L01-R005             # Single hostname
#   ./scripts/test-hostname.sh RO93L01-R005 1234-101    # Multiple hostnames
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

INSTALL_DIR="$PROJECT_DIR/QA/qa.cloud4retail.co"

if [ ! -f "$INSTALL_DIR/GKInstall.sh" ]; then
  echo "Error: GKInstall.sh not found in $INSTALL_DIR"
  exit 1
fi

echo "Using: $INSTALL_DIR"
echo ""

# Default NEXA test hostnames
HOSTNAMES=("$@")
if [ ${#HOSTNAMES[@]} -eq 0 ]; then
  HOSTNAMES=(
    "RO93L01-R005"
    "RO93L02-R005"
    "BE93L01-1234"
    "DE93L50-STORE42"
    "RO33S01-R005"
    "RO03S01-R005"
    "RO97W01-R005"
    "1234-101"
    "R005-101"
    "localhost"
  )
fi

for hn in "${HOSTNAMES[@]}"; do
  echo "============================================================"
  echo "  HOSTNAME: $hn"
  echo "============================================================"

  docker run --rm --hostname "$hn" \
    -v "$INSTALL_DIR:/install" \
    ubuntu:22.04 \
    bash -c 'cd /install && timeout 15 ./GKInstall.sh --ComponentType ONEX 2>&1 || true' \
    | grep -E '(Hostname|Computer name|environment|Store Number|Workstation ID|StoreNr|WorkstationId|does not match|NO MATCH|NEVER_MATCH|Matched|Extracted|Detection)'

  echo ""
done
