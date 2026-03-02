# Design: --StructureUniqueNameOverride CLI Parameter

## Purpose

Add a `--StructureUniqueNameOverride` CLI parameter that, when passed, injects `"structureUniqueName"` into the `newNode` object of the `create_structure.json` payload before POSTing to `/structure/nodes`. When not passed, behavior is unchanged.

## Pattern

Follows the exact same pattern as `--SystemNameOverride` and `--WorkstationNameOverride`:

1. **GKInstall script** accepts the CLI param and passes it through to store-initialization
2. **store-initialization script** receives the param and conditionally injects it into the JSON payload
3. **No changes to create_structure.json template** - injection happens at runtime only when param is present

## Flow

```
User passes --StructureUniqueNameOverride "MY_VALUE"
  -> GKInstall.ps1/sh stores it
  -> Passes to store-initialization via args
  -> store-initialization injects into create_structure.json before POST
  -> POST /structure/nodes includes structureUniqueName in newNode
```

## JSON Result

**Without override** (unchanged):
```json
{
  "newNode": {
    "systemName": "@SYSTEM_TYPE@",
    "workstationId": "@WORKSTATION_ID@",
    "name": "@STATION_NAME@"
  }
}
```

**With override**:
```json
{
  "newNode": {
    "systemName": "@SYSTEM_TYPE@",
    "workstationId": "@WORKSTATION_ID@",
    "name": "@STATION_NAME@",
    "structureUniqueName": "THE_OVERRIDE_VALUE"
  }
}
```

## Files to Modify

| File | Change |
|------|--------|
| `GKInstall.ps1.template` | Add `[string]$StructureUniqueNameOverride` param + pass to store-init args |
| `GKInstall.sh.template` | Add `cli_structure_unique_name_override` variable + case parsing + pass-through |
| `store-initialization.ps1.template` | Add `[string]$StructureUniqueNameOverride` param, inject into JSON before POST |
| `store-initialization.sh.template` | Add param parsing, inject into JSON before POST |
| `gk_install_generator.py` | Verify no code injection needed (param is template-native) |
| `tests/` | Add test coverage for new parameter |

## Injection Approach

### PowerShell (store-initialization)
After template replacements and before the POST call, if `$StructureUniqueNameOverride` is non-empty, use `ConvertFrom-Json` / `ConvertTo-Json` to add the field to `newNode`.

### Bash (store-initialization)
After sed replacements and before the POST call, if `$STRUCTURE_UNIQUE_NAME_OVERRIDE` is non-empty, use `jq` (with sed fallback) to inject the field into `newNode`.
