# CLI Parameters Feature: Store ID and Workstation ID Override

## Overview

Added CLI parameters to override automatic detection of Store ID and Workstation ID in the installation scripts. This allows for flexible installation scenarios where you want to:
- Hardcode specific values
- Mix automatic detection with manual values
- Bypass detection entirely for automated deployments

## Implementation Summary

### Changes Made

#### 1. PowerShell Template (`GKInstall.ps1.template`)

**New Parameters:**
```powershell
[string]$storeId,         # Optional: Override Store ID detection
[string]$WorkstationId    # Optional: Override Workstation ID detection
```

**Detection Priority (New):**
1. **Priority 0:** CLI parameters (highest)
2. Priority 1: Update mode (read from station.properties)
3. Priority 2: Hostname detection
4. Priority 3: File detection
5. Priority 4: Manual input (lowest)

#### 2. Bash Template (`GKInstall.sh.template`)

**New Parameters:**
```bash
--storeId <value>         # Optional: Override Store ID detection
--workstationId <value>   # Optional: Override Workstation ID detection
```

**Same priority order as PowerShell**

### No Changes Required To:
- ✅ `onboarding.ps1` / `onboarding.sh` (doesn't use these values)
- ✅ `store-initialization.ps1` / `store-initialization.sh` (already accepts these parameters)

---

## Usage Examples

### Example 1: Provide Both Values via CLI

**Windows:**
```powershell
.\GKInstall.ps1 -ComponentType POS -storeId R005 -WorkstationId 02
```

**Linux:**
```bash
./GKInstall.sh --ComponentType POS --storeId R005 --workstationId 02
```

**Result:**
- Skips hostname detection
- Skips file detection
- Skips manual input
- Uses provided values directly

---

### Example 2: Provide Only Workstation ID (Your Use Case)

**Windows:**
```powershell
.\GKInstall.ps1 -ComponentType POS -WorkstationId 02
```

**Linux:**
```bash
./GKInstall.sh --ComponentType POS --workstationId 02
```

**Result:**
- Workstation ID: `02` (from CLI)
- Store ID: Extracted from hostname using regex (e.g., `R005` from `RO03S02-R005.eu.delhaize.com`)
- No manual input needed

**Perfect for your scenario where:**
- Hostname: `RO03S02-R005.eu.delhaize.com`
- Regex extracts: Store ID = `R005`
- CLI provides: Workstation ID = `02`

---

### Example 3: Provide Only Store ID

**Windows:**
```powershell
.\GKInstall.ps1 -ComponentType POS -storeId R005
```

**Linux:**
```bash
./GKInstall.sh --ComponentType POS --storeId R005
```

**Result:**
- Store ID: `R005` (from CLI)
- Workstation ID: Extracted from hostname or file, or prompts if not found

---

### Example 4: Use with Environment Selection

**Windows:**
```powershell
.\GKInstall.ps1 -Env DEV -ComponentType POS -WorkstationId 02
```

**Linux:**
```bash
./GKInstall.sh --env DEV --ComponentType POS --workstationId 02
```

**Result:**
- Environment: `DEV` (from CLI)
- Store ID: Detected from hostname
- Workstation ID: `02` (from CLI)

---

## Detection Flow (New Logic)

```
┌─────────────────────────────────────────┐
│  Check CLI Parameters                   │
│  -storeId and -WorkstationId            │
└────────────┬────────────────────────────┘
             │
             ├─ BOTH provided ─→ Skip ALL detection ─→ Use CLI values
             │
             ├─ ONE provided ─→ Use CLI value + Detect other
             │
             └─ NONE provided ─→ Continue with normal detection
                │
┌───────────────┴──────────────────────────┐
│  Update Mode Check                       │
│  (if installation exists)                │
└────────────┬─────────────────────────────┘
             │
             ├─ YES ─→ Read station.properties ─→ Use existing values
             │
             └─ NO ─→ Continue detection
                │
┌───────────────┴──────────────────────────┐
│  Hostname Detection                      │
│  (only for missing values)               │
└────────────┬─────────────────────────────┘
             │
             ├─ SUCCESS ─→ Use detected values
             │
             └─ FAIL ─→ Continue
                │
┌───────────────┴──────────────────────────┐
│  File Detection                          │
│  (only for missing values)               │
└────────────┬─────────────────────────────┘
             │
             ├─ SUCCESS ─→ Use file values
             │
             └─ FAIL ─→ Continue
                │
┌───────────────┴──────────────────────────┐
│  Manual Input                            │
│  (prompt only for missing values)        │
└──────────────────────────────────────────┘
```

---

## Smart Prompting

The scripts now intelligently prompt only for missing values:

**If Store ID provided via CLI but Workstation ID not detected:**
```
Store Number already provided: R005
Please enter the Workstation ID (numeric): _
```

**If Workstation ID provided via CLI but Store ID not detected:**
```
Please enter the Store Number in one of these formats:
  - 4 digits (e.g., 1234)
  - 1 letter + 3 digits (e.g., R005)
Store Number: _
Workstation ID already provided: 02
```

---

## Benefits

### 1. **Flexibility**
- Choose which values to provide manually
- Mix CLI parameters with automatic detection

### 2. **Automation-Friendly**
- Can script installations with known Workstation IDs
- No interactive prompts needed

### 3. **Debugging**
- Override detection for testing specific scenarios
- Force specific values without changing hostname or files

### 4. **Multi-Tenancy Support**
- Combine with environment selection (`-Env DEV`)
- Perfect for CI/CD pipelines

---

## Integration with Existing Features

### Works With:
✅ Environment detection (`-Env`, `--env`)  
✅ Hostname detection (regex patterns)  
✅ File detection (.station files)  
✅ Update mode (preserves existing installation)  
✅ Offline mode (`--offline`)  
✅ Component type selection (`-ComponentType`, `--ComponentType`)

### Backward Compatible:
✅ Scripts work exactly as before if parameters not provided  
✅ All existing detection mechanisms still function  
✅ No breaking changes to existing workflows

---

## Example Deployment Scenarios

### Scenario 1: Automated Deployment Script

```powershell
# Deploy to multiple workstations
$workstations = @("01", "02", "03", "04", "05")

foreach ($ws in $workstations) {
    Write-Host "Installing on workstation $ws..."
    .\GKInstall.ps1 -ComponentType POS -Env PROD -WorkstationId $ws
}
```

### Scenario 2: Docker/Container Deployment

```bash
#!/bin/bash
# Store ID detected from hostname
# Workstation ID passed as environment variable
./GKInstall.sh --ComponentType POS --workstationId "$WORKSTATION_ID"
```

### Scenario 3: Manual Override for Testing

```powershell
# Test with specific values without changing hostname
.\GKInstall.ps1 -ComponentType POS -storeId TEST001 -WorkstationId 99
```

---

## Command Line Help

### PowerShell
```powershell
Get-Help .\GKInstall.ps1 -Parameter storeId
Get-Help .\GKInstall.ps1 -Parameter WorkstationId
```

### Bash
```bash
./GKInstall.sh --help
# Shows: [--storeId <id>] [--workstationId <id>]
```

---

## Testing Checklist

- [x] CLI parameters accept values
- [x] Hostname detection skipped when both CLI params provided
- [x] Partial CLI params work (one provided, one detected)
- [x] Manual prompt shows "already provided" message
- [x] Works with environment selection
- [x] Works in update mode
- [x] Backward compatible (no params = original behavior)
- [x] Both PowerShell and Bash templates updated
- [x] Values correctly passed to store-initialization script

---

## Notes for Users

1. **Parameter names are case-sensitive in PowerShell:**
   - Use `-WorkstationId` (capital W and I)
   - Use `-storeId` (lowercase s)

2. **Bash parameters use lowercase:**
   - Use `--workstationId`
   - Use `--storeId`

3. **Values are validated:**
   - Workstation ID must be numeric
   - Store ID accepts alphanumeric characters

4. **Priority matters:**
   - CLI parameters override ALL other detection methods
   - Even in update mode, CLI params are respected (though not recommended)

---

## Conclusion

This feature provides maximum flexibility for installation scenarios while maintaining full backward compatibility with existing detection mechanisms. Your specific use case (hardcoded Workstation ID + hostname-detected Store ID) is now fully supported!
