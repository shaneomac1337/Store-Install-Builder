#!/bin/bash

echo "============================================"
echo "Coop Sweden WDM Installation"
echo "============================================"
echo ""
echo "Installing WDM component with:"
echo "- Workstation ID: 200"
echo "- Offline Mode: Enabled"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call main installation script with Coop defaults
"$SCRIPT_DIR/GKInstall.sh" --componentType WDM --workstationId 200 --offline
