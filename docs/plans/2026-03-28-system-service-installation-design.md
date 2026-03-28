# System Service Installation Feature Design

**Date:** 2026-03-28
**Branch:** `feature/system-services`

## Summary

Add support for installing Tomcat-based components as Windows/Linux system services via the Launcher's existing CLI parameters. Service configuration is per-component, managed in the Launcher Settings dialog, and passed as CLI arguments to `Launcher.exe`/`Launcher.run` at invocation time.

## Scope

### In Scope
- Tomcat-based components: WDM, Flow-Service, LPA-Service, StoreHub-Service, RCS-Service
- Per-component toggle to enable/disable service installation
- Configurable service names (app + updater) with sensible defaults
- Windows-only start type selection (auto/manual)
- Admin/root requirement warning in the UI
- CLI arg injection into GKInstall templates

### Out of Scope
- POS / OneX-POS (not Tomcat-based, no service parameter support in their launchers)
- Changes to lib-installer-core (`defaultsAvailableProperties.list` remains unchanged)
- Changes to `launcher.properties` files (service args are CLI-only)

## Approach: CLI Arguments

The Launcher's `parameterList-service.xml` defines `runAsService`, `appServiceName`, `updaterServiceName`, and `runAsServiceStartType` as InstallBuilder CLI parameters. The custom `--defaultsFile` mechanism does not read these (they are not in `defaultsAvailableProperties.list`), so they must be passed as CLI arguments.

When service is **disabled** (default): the Launcher invocation is unchanged from today.
When service is **enabled**: CLI args are appended to the Launcher command.

## Data Flow

```
Launcher Settings Dialog (per-component)
  -> config["wdm_launcher_settings"]["runAsService"] = "1"
  -> config["wdm_launcher_settings"]["appServiceName"] = "Tomcat-wdm"
  -> config["wdm_launcher_settings"]["updaterServiceName"] = "Updater-wdm"
  -> config["wdm_launcher_settings"]["runAsServiceStartType"] = "auto"

gk_install_generator.py (at generation time)
  -> reads service settings from config for the selected component
  -> builds CLI arg string
  -> replaces @SERVICE_ARGS_PS@ / @SERVICE_ARGS_SH@ tokens in templates

GKInstall.ps1 / GKInstall.sh (at runtime on target machine)
  -> Launcher.exe --defaultsFile launcher.properties --mode unattended
     --runAsService 1 --appServiceName Tomcat-wdm
     --updaterServiceName Updater-wdm --runAsServiceStartType auto
```

## Template Changes

### GKInstall.ps1.template (new install path, ~line 2429)

```powershell
# Service args (injected by generator, empty when service disabled)
$serviceArgs = @()
@SERVICE_ARGS_PS@
$launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList (@("--defaultsFile", "launcher.properties", "--mode", "unattended") + $serviceArgs) -PassThru
```

When enabled, `@SERVICE_ARGS_PS@` is replaced with:
```powershell
$serviceArgs = @("--runAsService", "1", "--appServiceName", "Tomcat-wdm", "--updaterServiceName", "Updater-wdm", "--runAsServiceStartType", "auto")
```

### GKInstall.sh.template (new install path, ~line 2890)

```bash
# Service args (injected by generator, empty when service disabled)
service_args=""
@SERVICE_ARGS_SH@
./Launcher.run --defaultsFile launcher.properties --mode unattended $service_args &
```

When enabled, `@SERVICE_ARGS_SH@` is replaced with:
```bash
service_args="--runAsService 1 --appServiceName Tomcat-wdm --updaterServiceName Updater-wdm"
```

Note: `--runAsServiceStartType` is Windows-only per `parameterList-service.xml` (guarded by `<platformTest><type>windows</type></platformTest>`).

## UI Changes (Launcher Settings Dialog)

For each Tomcat-based component tab (WDM, Flow-Service, LPA-Service, StoreHub-Service, RCS-Service), add a "Service Installation" section at the top:

- **Checkbox:** "Install as System Service" (default: unchecked)
- **Warning label:** "Requires running GKInstall as Administrator (Windows) or root (Linux)"
- **Entry:** Application Service Name (default: `Tomcat-{shortName}`)
- **Entry:** Updater Service Name (default: `Updater-{shortName}`)
- **Dropdown:** Start Type — `auto` / `manual` (default: `auto`, Windows only label)

Service name fields and start type dropdown are shown/enabled only when the checkbox is checked.

## Default Values

| Parameter | Default |
|-----------|---------|
| `runAsService` | `0` (disabled) |
| `appServiceName` | `Tomcat-{shortName}` (e.g., Tomcat-wdm) |
| `updaterServiceName` | `Updater-{shortName}` (e.g., Updater-wdm) |
| `runAsServiceStartType` | `auto` |

Short names: wdm, flow, lpa, sh, rcs

## Files Modified

| File | Change |
|------|--------|
| `dialogs/launcher_settings.py` | Add service section to Tomcat component tabs |
| `templates/GKInstall.ps1.template` | Add `@SERVICE_ARGS_PS@` token at Launcher invocation |
| `templates/GKInstall.sh.template` | Add `@SERVICE_ARGS_SH@` token at Launcher invocation |
| `generators/gk_install_generator.py` | Read service config, build CLI args, replace tokens |

## Files NOT Modified

- `config.py` — service settings stored in existing `{component}_launcher_settings` dict
- `launcher_generator.py` — service args are CLI-only, not in launcher.properties
- `helper/launchers/*.template` — no changes to properties file templates
- lib-installer-core — no changes

## Constraints

- Requires admin/root on the target machine for service registration
- Launcher silently skips service registration without admin (existing behavior)
- `runAsServiceStartType` only applies on Windows
- Update mode (`isUpdate=true`) does not use `--defaultsFile`, so service args are only relevant for new installations
