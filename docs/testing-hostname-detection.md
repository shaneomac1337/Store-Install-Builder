# Testing Hostname Detection

This guide explains how to test hostname detection in generated GKInstall scripts without permanently changing your machine's hostname.

## Overview

The GKInstall scripts support automatic detection of Store ID and Workstation ID from the hostname. You can test different hostname patterns by temporarily overriding the hostname environment variable during script execution.

## Windows Testing (PowerShell)

### Basic Command

Temporarily override the hostname for a single script execution:

```powershell
$env:COMPUTERNAME = "YOUR-TEST-HOSTNAME"; .\GKInstall.ps1
```

This sets the `COMPUTERNAME` environment variable **only for that command** and doesn't affect your actual system hostname.

### Example Test Cases

#### 2-Group Pattern (Store-Workstation)

Pattern: `^([0-9]{4})-([0-9]{3})$`

```powershell
# Test with store 1234, workstation 101
$env:COMPUTERNAME = "1234-101"; .\GKInstall.ps1

# Test with store 9999, workstation 200
$env:COMPUTERNAME = "9999-200"; .\GKInstall.ps1
```

#### 3-Group Pattern (Environment-Store-Workstation)

Pattern: `^([A-Z])(\d{4})-(\d{2,3})$`

```powershell
# Test DEV environment
$env:COMPUTERNAME = "D9999-150"; .\GKInstall.ps1

# Test PROD environment
$env:COMPUTERNAME = "P9999-150"; .\GKInstall.ps1

# Test QA environment
$env:COMPUTERNAME = "Q1234-101"; .\GKInstall.ps1

# Test with 2-digit workstation ID
$env:COMPUTERNAME = "D9999-01"; .\GKInstall.ps1

# Test with 3-digit workstation ID
$env:COMPUTERNAME = "D9999-999"; .\GKInstall.ps1
```

#### Alternative 3-Group Pattern (Environment-Store-Workstation with Dash)

Pattern: `^([A-Z]+)-([0-9]{4})-([0-9]{3})$`

```powershell
# Test DEV environment
$env:COMPUTERNAME = "DEV-1234-101"; .\GKInstall.ps1

# Test PROD environment
$env:COMPUTERNAME = "PROD-5678-200"; .\GKInstall.ps1

# Test QA environment
$env:COMPUTERNAME = "QA-9999-150"; .\GKInstall.ps1
```

### Multiple Test Scenarios

Run multiple tests in sequence:

```powershell
# Test different patterns
$env:COMPUTERNAME = "D1234-101"; .\GKInstall.ps1
$env:COMPUTERNAME = "P5678-200"; .\GKInstall.ps1
$env:COMPUTERNAME = "Q9999-999"; .\GKInstall.ps1
```

### Running with Additional Parameters

Combine hostname override with CLI parameters:

```powershell
# Override hostname but also provide explicit IDs (CLI takes priority)
$env:COMPUTERNAME = "D9999-150"; .\GKInstall.ps1 -storeId 1234 -workstationId 101
```

**Note**: CLI parameters (`-storeId`, `-workstationId`) have **Priority 0** and will override hostname detection.

## Linux Testing (Bash)

### Basic Command

Temporarily override the hostname for a single script execution:

```bash
HOSTNAME="YOUR-TEST-HOSTNAME" ./GKInstall.sh
```

Or using `hostname` command override:

```bash
hostname() { echo "YOUR-TEST-HOSTNAME"; }; export -f hostname; ./GKInstall.sh
```

**Recommended approach** (sets environment variable):

```bash
HOSTNAME="YOUR-TEST-HOSTNAME" ./GKInstall.sh
```

### Example Test Cases

#### 2-Group Pattern (Store-Workstation)

Pattern: `^([0-9]{4})-([0-9]{3})$`

```bash
# Test with store 1234, workstation 101
HOSTNAME="1234-101" ./GKInstall.sh

# Test with store 9999, workstation 200
HOSTNAME="9999-200" ./GKInstall.sh
```

#### 3-Group Pattern (Environment-Store-Workstation)

Pattern: `^([A-Z])(\d{4})-(\d{2,3})$`

```bash
# Test DEV environment
HOSTNAME="D9999-150" ./GKInstall.sh

# Test PROD environment
HOSTNAME="P9999-150" ./GKInstall.sh

# Test QA environment
HOSTNAME="Q1234-101" ./GKInstall.sh

# Test with 2-digit workstation ID
HOSTNAME="D9999-01" ./GKInstall.sh

# Test with 3-digit workstation ID
HOSTNAME="D9999-999" ./GKInstall.sh
```

#### Alternative 3-Group Pattern (Environment-Store-Workstation with Dash)

Pattern: `^([A-Z]+)-([0-9]{4})-([0-9]{3})$`

```bash
# Test DEV environment
HOSTNAME="DEV-1234-101" ./GKInstall.sh

# Test PROD environment
HOSTNAME="PROD-5678-200" ./GKInstall.sh

# Test QA environment
HOSTNAME="QA-9999-150" ./GKInstall.sh
```

### Multiple Test Scenarios

Run multiple tests in sequence:

```bash
# Test different patterns
HOSTNAME="D1234-101" ./GKInstall.sh
HOSTNAME="P5678-200" ./GKInstall.sh
HOSTNAME="Q9999-999" ./GKInstall.sh
```

### Running with Additional Parameters

Combine hostname override with CLI parameters:

```bash
# Override hostname but also provide explicit IDs (CLI takes priority)
HOSTNAME="D9999-150" ./GKInstall.sh --storeId 1234 --workstationId 101
```

**Note**: CLI parameters (`--storeId`, `--workstationId`) have **Priority 0** and will override hostname detection.

## Configuring Hostname Patterns in GK Install Builder

### Accessing Detection Settings

1. Open **GK Install Builder**
2. Click the **Detection Settings** button (or menu option)
3. Navigate to the **Hostname Detection** tab

### 2-Group Pattern Configuration

For patterns like `1234-101` (Store-Workstation):

**Regex Pattern** (Windows & Linux):
```regex
^([0-9]{4})-([0-9]{3})$
```

**Settings**:
- ⬜ **Environment detection** (unchecked for 2-group)
- **Group Mappings**:
  - Store: Group **1**
  - Workstation: Group **2**
- **Test Hostname**: `1234-101`

### 3-Group Pattern Configuration

For patterns like `D9999-150` (Environment-Store-Workstation):

**Regex Pattern** (Windows & Linux):
```regex
^([A-Z])(\d{4})-(\d{2,3})$
```

**Settings**:
- ✅ **Environment detection** (checked for 3-group)
- **Group Mappings**:
  - Environment: Group **1**
  - Store: Group **2**
  - Workstation: Group **3**
- **Test Hostname**: `D9999-150`

### Alternative 3-Group Pattern (with Dash)

For patterns like `DEV-1234-101`:

**Regex Pattern** (Windows & Linux):
```regex
^([A-Z]+)-([0-9]{4})-([0-9]{3})$
```

**Settings**:
- ✅ **Environment detection** (checked)
- **Group Mappings**:
  - Environment: Group **1**
  - Store: Group **2**
  - Workstation: Group **3**
- **Test Hostname**: `DEV-1234-101`

## Detection Priority System

The generated scripts implement a multi-tier detection system:

1. **Priority 0**: CLI parameters (`--storeId`, `--workstationId`) - **HIGHEST**
2. **Priority 1**: Update mode (read from existing `station.properties`)
3. **Priority 2**: Hostname detection (regex patterns)
4. **Priority 3**: File detection (`.station` files)
5. **Priority 4**: Manual input (user prompts) - **LOWEST**

### Priority Testing Examples

#### Test Priority 0 (CLI Override)

Even with a valid hostname, CLI parameters take precedence:

```powershell
# Windows - CLI overrides hostname detection
$env:COMPUTERNAME = "D9999-150"; .\GKInstall.ps1 -storeId 1234 -workstationId 999
# Result: Uses Store 1234, Workstation 999 (from CLI, not hostname)
```

```bash
# Linux - CLI overrides hostname detection
HOSTNAME="D9999-150" ./GKInstall.sh --storeId 1234 --workstationId 999
# Result: Uses Store 1234, Workstation 999 (from CLI, not hostname)
```

#### Test Priority 2 (Hostname Detection)

With no CLI parameters and no existing installation:

```powershell
# Windows - Uses hostname detection
$env:COMPUTERNAME = "D9999-150"; .\GKInstall.ps1
# Result: Uses Store 9999, Workstation 150, Environment D (from hostname)
```

```bash
# Linux - Uses hostname detection
HOSTNAME="D9999-150" ./GKInstall.sh
# Result: Uses Store 9999, Workstation 150, Environment D (from hostname)
```

#### Test Priority 1 (Update Mode)

When updating an existing installation, values are read from `station.properties` (Priority 1), overriding hostname detection (Priority 2):

```powershell
# Windows - Existing installation detected
$env:COMPUTERNAME = "D9999-150"; .\GKInstall.ps1
# If station.properties exists with Store 5555, it will use 5555 (not 9999 from hostname)
```

## Regex Pattern Reference

### Common Patterns

| Pattern Type | Example | Regex | Groups |
|--------------|---------|-------|--------|
| 2-Group (numeric) | `1234-101` | `^([0-9]{4})-([0-9]{3})$` | Store, WS |
| 2-Group (alphanumeric) | `STORE-101` | `^([A-Za-z0-9]+)-([0-9]{2,3})$` | Store, WS |
| 3-Group (single char env) | `D9999-150` | `^([A-Z])(\d{4})-(\d{2,3})$` | Env, Store, WS |
| 3-Group (multi char env) | `DEV-1234-101` | `^([A-Z]+)-([0-9]{4})-([0-9]{3})$` | Env, Store, WS |
| 3-Group (flexible) | `QA-STORE-999` | `^([A-Z]+)-([A-Z0-9]+)-([0-9]{2,3})$` | Env, Store, WS |

### Regex Components

- `^` - Start of string
- `$` - End of string
- `[0-9]` - Any digit
- `[A-Z]` - Any uppercase letter
- `[A-Za-z0-9]` - Any alphanumeric character
- `\d` - Any digit (equivalent to `[0-9]`)
- `{4}` - Exactly 4 occurrences
- `{2,3}` - Between 2 and 3 occurrences
- `+` - One or more occurrences
- `()` - Capture group

## Troubleshooting

### Script Not Detecting Hostname

1. **Verify the regex pattern** in Detection Settings
2. **Test the pattern** using the built-in tester in the GUI
3. **Check script output** for detection messages
4. **Verify group mappings** are correct (especially for 3-group patterns)

### CLI Parameters Not Working

Windows:
```powershell
# Correct (use dash prefix)
.\GKInstall.ps1 -storeId 1234 -workstationId 101

# Incorrect (don't use equals sign)
.\GKInstall.ps1 -storeId=1234 -workstationId=101
```

Linux:
```bash
# Correct (use double dash and equals)
./GKInstall.sh --storeId=1234 --workstationId=101

# Also correct (space separator)
./GKInstall.sh --storeId 1234 --workstationId 101

# Case-insensitive (also works)
./GKInstall.sh --storeid=1234 --workstationid=101
```

### Environment Variable Not Taking Effect

Make sure to use the correct syntax:

```powershell
# Windows - Set variable in same command
$env:COMPUTERNAME = "D9999-150"; .\GKInstall.ps1
```

```bash
# Linux - Prefix variable before command
HOSTNAME="D9999-150" ./GKInstall.sh
```

### Testing Validation

After each test, check the script output for:
- `Hostname detection successful` message
- Extracted Store ID, Workstation ID, Environment
- Which detection method was used (Priority 0-4)

## Best Practices

1. **Always test with the actual regex pattern** you plan to deploy
2. **Test edge cases**: minimum/maximum lengths, different environments
3. **Test priority system**: Verify CLI parameters override hostname detection
4. **Test both platforms**: Ensure regex works on both Windows and Linux
5. **Document your patterns**: Keep a reference of patterns used in production
6. **Use descriptive test hostnames**: Make it obvious what each test validates

## Related Documentation

- [Detection Analysis](detection-analysis.md) - In-depth analysis of detection methods
- [CLI Parameters Feature](cli-parameters-feature.md) - CLI parameter documentation
- [CLAUDE.md](../CLAUDE.md) - Full project documentation
