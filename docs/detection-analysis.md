# Detection Mechanism Analysis: Store, Environment, and WSID

## Overview

This document provides a thorough analysis of how the Store Install Builder detects Store IDs, Environment configurations, and Workstation IDs (WSID) in both the tool (Python) and the generated scripts (PowerShell/Bash).

---

## 1. Detection Manager (`detection.py`)

### Purpose
The `DetectionManager` class manages all detection settings and generates detection code for scripts.

### Key Components

#### A. File-Based Detection
**Configuration:**
```python
"file_detection_enabled": True,
"use_base_directory": True,
"base_directory": "",  # Defaults to C:\gkretail\stations (Windows) or /usr/local/gkretail/stations (Linux)
"custom_filenames": {
    "POS": "POS.station",
    "WDM": "WDM.station",
    "FLOW-SERVICE": "FLOW-SERVICE.station",
    "LPA-SERVICE": "LPA.station",
    "STOREHUB-SERVICE": "SH.station"
}
```

**How It Works:**
1. Looks for `.station` files in a base directory
2. Each component type has its own station file
3. Files contain `StoreID=` and `WorkstationID=` entries
4. Used as fallback when hostname detection fails

**Detection Priority:**
- File detection is Priority 2 (after hostname detection)
- Only runs if hostname detection fails
- Validates that WorkstationID is numeric

---

#### B. Hostname Detection

**Configuration:**
```python
"hostname_detection": {
    "windows_regex": r"([^-]+)-([0-9]+)$",
    "linux_regex": r"([^-]+)-([0-9]+)$",
    "test_hostname": "STORE-1234-101",
    "detect_environment": False,
    "env_group": 1,      # Which regex group contains environment
    "store_group": 2,    # Which regex group contains store ID
    "workstation_group": 3  # Which regex group contains workstation ID
}
```

**Two Detection Modes:**

1. **2-Group Pattern (Default):**
   - Format: `STORE-101` or `R005-101`
   - Group 1: Store ID
   - Group 2: Workstation ID
   - Example regex: `([^-]+)-([0-9]+)$`

2. **3-Group Pattern (With Environment):**
   - Format: `DEV-STORE-101` or `P-R005-101`
   - Group 1: Environment (e.g., DEV, P, Q)
   - Group 2: Store ID
   - Group 3: Workstation ID
   - Example regex: `([^-]+)-([^-]+)-([0-9]+)$`

**Validation Rules:**
- Store ID: Alphanumeric with dots, dashes, underscores: `^[A-Za-z0-9_\\-.]+$`
- Workstation ID: Must be numeric: `^[0-9]+$`

**Special Handling:**
- If Store ID contains a dash (e.g., `STORE-1674-101`), extracts the last 4 digits
- Example: `STORE-1674` → extracts `1674` as store number

---

## 2. Environment Detection (Multi-Tenancy)

### Environment Manager (`environment_manager.py`)

**Purpose:** Manages multiple environment configurations (DEV, QA, PROD, etc.) with different credentials and settings.

**Environment Structure:**
```json
{
  "alias": "DEV",
  "name": "Development Environment",
  "base_url": "dev.example.cloud4retail.co",
  "use_default_tenant": false,
  "tenant_id": "001",
  "launchpad_oauth2": "password123",
  "eh_launchpad_username": "1001",
  "eh_launchpad_password": "gkgkgk123!"
}
```

### Detection Priorities in Scripts

#### Priority 1: CLI Parameter
```powershell
# Windows
.\GKInstall.ps1 -Env DEV

# Linux
./GKInstall.sh --env DEV
```

#### Priority 2: Hostname Detection (if enabled)
- Extracts environment from hostname using 3-group regex
- Example: `DEV-R005-101` → environment = `DEV`
- **Strict validation:** Environment MUST exist in `environments.json` or script exits with error
- This prevents misconfigurations

**Code Example (PowerShell):**
```powershell
if ($hostname -match '([^-]+)-([^-]+)-([0-9]+)$') {
    $hostnameEnv = $matches[1]  # Extract environment from group 1
    $selectedEnv = $environments | Where-Object { $_.alias -eq $hostnameEnv } | Select-Object -First 1
    if ($selectedEnv) {
        # Apply environment config
    } else {
        Write-Host "ERROR: Environment '$hostnameEnv' detected but not configured!"
        exit 1
    }
}
```

#### Priority 3: File Detection
- Checks `.station` files for `Environment=` entry
- Fallback if hostname doesn't match pattern

#### Priority 4: Interactive Prompt
- Lists all available environments
- User selects from menu

---

## 3. Detection in Generated Scripts

### A. Update Mode Detection

**Purpose:** Detect if installation already exists

**Method:**
1. Checks if installation directory exists
2. Looks for `station.properties` file
3. Checks log files for recent activity (within 48 hours)

**Behavior in Update Mode:**
```powershell
# Windows - Update Mode
if ($isUpdate) {
    # Extract from existing station.properties
    $stationPropertiesPath = Join-Path $install_dir "station.properties"
    # Parse: station.storeId=R005
    # Parse: station.workstationId=101
    
    # Skip environment selection - use existing config
    # Skip hostname/file detection
}
```

**Why?** Updates must preserve exact configuration from original installation.

---

### B. New Installation Detection Flow

```
┌─────────────────────────────────────────┐
│  1. Check if Update Mode                │
│     (installation exists?)              │
└────────────┬────────────────────────────┘
             │
             ├─ YES ─→ Read station.properties ─→ Use existing values
             │
             └─ NO
                │
┌───────────────┴──────────────────────────┐
│  2. Try Hostname Detection               │
│     - Get COMPUTERNAME (Windows) or      │
│       hostname (Linux)                   │
│     - Apply regex pattern                │
│     - Extract groups based on config     │
│     - Validate format                    │
└────────────┬─────────────────────────────┘
             │
             ├─ SUCCESS ─→ Use detected values
             │
             └─ FAIL
                │
┌───────────────┴──────────────────────────┐
│  3. Try File Detection                   │
│     - Check .station file                │
│     - Parse StoreID= and WorkstationID=  │
│     - Validate values                    │
└────────────┬─────────────────────────────┘
             │
             ├─ SUCCESS ─→ Use file values
             │
             └─ FAIL
                │
┌───────────────┴──────────────────────────┐
│  4. Manual Input (Interactive Prompt)    │
│     - Ask user for Store Number          │
│     - Ask user for Workstation ID        │
│     - Validate input                     │
└──────────────────────────────────────────┘
```

---

### C. Code Generation (`generator.py`)

**Dynamic Code Injection:**

The generator replaces placeholders in templates with actual detection code:

1. **`# HOSTNAME_STORE_WORKSTATION_DETECTION_PLACEHOLDER`**
   - Replaced with hostname regex matching code
   - Uses configured regex pattern
   - Uses configured group mappings

2. **`# HOSTNAME_ENV_DETECTION_PLACEHOLDER`**
   - Only inserted if environment detection is enabled
   - Extracts environment from hostname
   - Validates against environments.json

3. **File Detection Code**
   - Inserted via `_generate_powershell_detection()` or `_generate_bash_detection()`
   - Uses configured file paths

**Example Generation (PowerShell):**
```python
# In generator.py
if hostname_env_detection:
    store_workstation_code = rf'''if ($hs -match '{hostname_regex}') {{
        # 3-group pattern: Environment ({env_group}), Store ID ({store_group}), Workstation ID ({ws_group})
        $storeId = $matches[{store_group}]
        $workstationId = $matches[{ws_group}]
        # ... validation
    }}'''
    template = template.replace("# HOSTNAME_STORE_WORKSTATION_DETECTION_PLACEHOLDER", store_workstation_code)
```

---

## 4. Practical Examples

### Example 1: Simple Store Detection

**Hostname:** `R005-101`

**Configuration:**
```json
{
  "hostname_detection": {
    "windows_regex": "([^-]+)-([0-9]+)$",
    "detect_environment": false,
    "store_group": 1,
    "workstation_group": 2
  }
}
```

**Result:**
- Store ID: `R005`
- Workstation ID: `101`
- No environment extracted

---

### Example 2: Multi-Environment Detection

**Hostname:** `DEV-R005-101`

**Configuration:**
```json
{
  "hostname_detection": {
    "windows_regex": "([^-]+)-([^-]+)-([0-9]+)$",
    "detect_environment": true,
    "env_group": 1,
    "store_group": 2,
    "workstation_group": 3
  },
  "environments": [
    {
      "alias": "DEV",
      "name": "Development",
      "base_url": "dev.example.com",
      "tenant_id": "001"
    }
  ]
}
```

**Result:**
- Environment: `DEV` (matched from environments)
- Store ID: `R005`
- Workstation ID: `101`
- Uses DEV's base_url and credentials

---

### Example 3: Complex Store Format

**Hostname:** `STORE-1674-101`

**Detection Logic:**
1. Matches regex: `([^-]+)-([0-9]+)$`
2. Extracts: Store = `STORE-1674`, Workstation = `101`
3. **Additional processing:** Finds last 4 digits in Store ID
4. Final Store Number: `1674`

---

## 5. File Detection Format

**Station File Location:**
- Windows: `C:\gkretail\stations\POS.station`
- Linux: `/usr/local/gkretail/stations/POS.station`

**File Format:**
```ini
StoreID=R005
WorkstationID=101
Environment=DEV  # Optional, for environment detection
```

**PowerShell Parsing:**
```powershell
$fileContent = Get-Content -Path $stationFilePath -Raw
$lines = $fileContent -split "`r?`n"
foreach ($line in $lines) {
    if ($line -match "StoreID=(.+)") {
        $storeNumber = $matches[1].Trim()
    }
    if ($line -match "WorkstationID=(.+)") {
        $workstationId = $matches[1].Trim()
    }
}
```

---

## 6. Key Configuration Methods

### DetectionManager Methods

| Method | Purpose |
|--------|---------|
| `set_hostname_regex(regex, platform)` | Set hostname detection pattern |
| `enable_hostname_environment_detection(enabled)` | Enable 3-group detection |
| `set_group_mapping(group_name, group_number)` | Configure which regex group is which |
| `test_hostname_regex(hostname, platform)` | Test regex against sample hostname |
| `generate_detection_code(component_type, script_type)` | Generate detection code for scripts |
| `get_file_path(component_type)` | Get station file path |

---

## 7. Best Practices

1. **Testing Regex Patterns:**
   - Use the "Test Regex" feature in the GUI
   - Test with multiple hostname formats
   - Validate group mappings

2. **Multi-Tenancy:**
   - Use 3-group regex with environment detection
   - Define all environments in `environments.json`
   - Use consistent environment aliases (DEV, QA, PROD)

3. **Station Files:**
   - Place in standardized location
   - Use consistent format
   - Keep files readable (plain text)

4. **Update Safety:**
   - Update mode always reads from `station.properties`
   - Never prompts for manual input during updates
   - Preserves exact configuration

---

## 8. Common Patterns

### Pattern: Basic Store-Workstation
```regex
([^-]+)-([0-9]+)$
```
Matches: `R005-101`, `1234-201`, `STORE-301`

### Pattern: Environment-Store-Workstation
```regex
([^-]+)-([^-]+)-([0-9]+)$
```
Matches: `DEV-R005-101`, `P-1234-201`, `QA-STORE-301`

### Pattern: Complex Store Format
```regex
(.+)-([0-9]{4})-([0-9]+)$
```
Matches: `PREFIX-1234-101`, `COMPLEX-5678-201`

---

## 9. Error Handling

### Script Errors

1. **Update Mode - Missing station.properties:**
   ```
   Error: No station.properties found
   Update not possible. Exiting.
   ```

2. **Environment Not Found:**
   ```
   ERROR: Environment 'DEV' detected from hostname but not configured!
   Please add environment 'DEV' to your configuration.
   ```

3. **Invalid Workstation ID:**
   ```
   Invalid input. Please enter a numeric Workstation ID.
   ```

---

## Summary

The detection system uses a **hierarchical fallback approach**:

1. **Update Mode:** Always use existing `station.properties`
2. **New Installation:**
   - Try hostname detection (fastest, automatic)
   - Fall back to file detection (requires pre-configured files)
   - Fall back to manual input (interactive, always works)

**Environment detection** is independent and runs with its own priority:
1. CLI parameter (`-Env DEV`)
2. Hostname extraction (3-group regex)
3. File detection (`.station` file)
4. Interactive menu

This provides **maximum flexibility** while maintaining **safety and validation** throughout the process.
