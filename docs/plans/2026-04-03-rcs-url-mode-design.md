# RCS URL Mode: Hostname vs IP Address

**Date**: 2026-04-03
**Status**: Approved

## Problem

RCS installation currently always uses the machine's hostname for the `rcs.url` property in `system.properties`. A colleague needs the option to use the machine's IP address instead, resolved at runtime via the default-gateway network adapter.

## Constraints

- HTTPS must be disabled (greyed out) when IP mode is selected -- no valid certificate for raw IPs
- IP resolution must use the adapter with the default gateway (handles multiple adapters, VPN, Docker, etc.)
- Hostname remains the default
- Only affects RCS-SERVICE component -- no other components touch `rcs.url`

## Design

### Config (`config.py`)
- New default key: `"rcs_url_mode": "hostname"` (values: `"hostname"` or `"ip"`)

### GUI (`launcher_settings.py`)
- Two radio buttons ("Hostname" / "IP Address") in the RCS-SERVICE tab, placed above the existing HTTPS checkbox
- When "IP Address" selected: force-uncheck and disable (grey out) the HTTPS checkbox
- When "Hostname" selected: re-enable the HTTPS checkbox
- Value saved/loaded via `config_manager`

### Generator (`helper_file_generator.py`)
- Read `rcs_url_mode` from config
- Replace new placeholder `@RCS_URL_MODE@` in store-initialization templates
- When mode is `"ip"`, force protocol to `http` regardless of HTTPS checkbox state

### Templates (`store-initialization.ps1.template` / `.sh.template`)
- Conditional in the RCS URL construction block:
  - If `@RCS_URL_MODE@` == `"ip"`: resolve IP via default gateway adapter
  - Else: use hostname as today (`$env:COMPUTERNAME` / `hostname`)
- PowerShell IP detection: `(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway }).IPv4Address.IPAddress | Select-Object -First 1`
- Bash IP detection: `ip route get 1.1.1.1 | awk '{print $7; exit}'` with fallback to `hostname -I | awk '{print $1}'`

### Tests
- Update existing RCS tests to cover the new `@RCS_URL_MODE@` placeholder
- Test that IP mode forces HTTP protocol

## Files Changed

1. `gk_install_builder/config.py` -- new default key
2. `gk_install_builder/dialogs/launcher_settings.py` -- radio buttons + HTTPS interlock
3. `gk_install_builder/generators/helper_file_generator.py` -- new placeholder replacement + IP mode forces HTTP
4. `gk_install_builder/templates/store-initialization.ps1.template` -- IP resolution conditional
5. `gk_install_builder/templates/store-initialization.sh.template` -- IP resolution conditional
6. Tests -- cover new placeholder and IP/HTTP enforcement
