# ============================================================================
# Native hostname detection test (PowerShell 7)
#
# Tests hostname regex patterns directly without Docker.
# Auto-extracts regex and group mappings from generated install scripts.
#
# Usage:
#   pwsh ./scripts/test-hostname.ps1                            # All NEXA test cases
#   pwsh ./scripts/test-hostname.ps1 RO93L01-R005               # Single hostname
#   pwsh ./scripts/test-hostname.ps1 RO93L01-R005 1234-101      # Multiple hostnames
#   pwsh ./scripts/test-hostname.ps1 -Regex '^[A-Z]{2}([0-9])[0-9][A-Z]([0-9]{2})-(.+)$' -StoreGroup 3 -WsGroup 2 -EnvGroup 1
#   pwsh ./scripts/test-hostname.ps1 -InstallPath "D:\output\prod.example.com"
# ============================================================================

param(
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$Hostnames,
    [string]$Regex,
    [int]$StoreGroup = 0,
    [int]$WsGroup = 0,
    [int]$EnvGroup = 0,
    [string]$InstallPath
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# Find install directory
if ($InstallPath) {
    $InstallDir = $InstallPath
} else {
    $InstallDir = Join-Path $ProjectDir "QA" "qa.cloud4retail.co"
}

# --- Auto-extraction helpers ---

function Extract-RegexFromPs1 {
    param([string]$Path)
    $content = Get-Content $Path -Raw
    $result = @{ Regex = ""; StoreGroup = 0; WsGroup = 0; EnvGroup = 0 }

    # Extract regex from: if ($hs -match 'REGEX') {
    if ($content -match "\`$hs -match '([^']+)'") {
        $result.Regex = $matches[1]
    }

    # Extract store group from: $storeId = $matches[N]
    if ($content -match '\$storeId\s*=\s*\$matches\[(\d+)\]') {
        $result.StoreGroup = [int]$matches[1]
    }

    # Extract workstation group from: $workstationId = $matches[N]
    if ($content -match '\$workstationId\s*=\s*\$matches\[(\d+)\]') {
        $result.WsGroup = [int]$matches[1]
    }

    # Check for environment group in 3-group comment
    if ($content -match '3-group pattern: Environment \((\d+)\)') {
        $result.EnvGroup = [int]$matches[1]
    }

    return $result
}

function Extract-RegexFromSh {
    param([string]$Path)
    $content = Get-Content $Path -Raw
    $result = @{ Regex = ""; StoreGroup = 0; WsGroup = 0; EnvGroup = 0 }

    # Extract regex from: [[ "$hs" =~ REGEX ]] or [[ "$hostname" =~ REGEX ]]
    if ($content -match '\[\[\s+"\$(hs|hostname)"\s+=~\s+(.+?)\s+\]\]') {
        $result.Regex = $matches[2]
    }

    # Extract store group from: storeId="${BASH_REMATCH[N]}"
    if ($content -match 'storeId="\$\{BASH_REMATCH\[(\d+)\]\}"') {
        $result.StoreGroup = [int]$matches[1]
    }

    # Extract workstation group from: workstationId="${BASH_REMATCH[N]}"
    if ($content -match 'workstationId="\$\{BASH_REMATCH\[(\d+)\]\}"') {
        $result.WsGroup = [int]$matches[1]
    }

    return $result
}

# --- Detect script and extract regex ---

$ScriptName = ""
if (-not $Regex) {
    $ps1Path = Join-Path $InstallDir "GKInstall.ps1"
    $shPath  = Join-Path $InstallDir "GKInstall.sh"

    if (Test-Path $ps1Path) {
        $ScriptName = "GKInstall.ps1"
        $extracted = Extract-RegexFromPs1 -Path $ps1Path
        $Regex = $extracted.Regex
        if ($StoreGroup -eq 0) { $StoreGroup = $extracted.StoreGroup }
        if ($WsGroup -eq 0)    { $WsGroup    = $extracted.WsGroup }
        if ($EnvGroup -eq 0)   { $EnvGroup   = $extracted.EnvGroup }
        Write-Host "Source:  $InstallDir\$ScriptName" -ForegroundColor Green
    } elseif (Test-Path $shPath) {
        $ScriptName = "GKInstall.sh"
        $extracted = Extract-RegexFromSh -Path $shPath
        $Regex = $extracted.Regex
        if ($StoreGroup -eq 0) { $StoreGroup = $extracted.StoreGroup }
        if ($WsGroup -eq 0)    { $WsGroup    = $extracted.WsGroup }
        if ($EnvGroup -eq 0)   { $EnvGroup   = $extracted.EnvGroup }
        Write-Host "Source:  $InstallDir\$ScriptName" -ForegroundColor Green
    }

    if (-not $Regex) {
        $Regex = '^([0-9]{4})-([0-9]{3})$'
        Write-Host "No generated script found in $InstallDir" -ForegroundColor Yellow
        Write-Host "Using default regex" -ForegroundColor Yellow
    }
}

# Apply defaults for group mappings if still not set
if ($StoreGroup -eq 0) { $StoreGroup = 1 }
if ($WsGroup -eq 0)    { $WsGroup    = 2 }

# --- Default NEXA test hostnames ---

if (-not $Hostnames -or $Hostnames.Count -eq 0) {
    $Hostnames = @(
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
}

# --- Display configuration ---

Write-Host ""
Write-Host "Regex:             $Regex" -ForegroundColor Cyan
Write-Host "Store Group:       $StoreGroup" -ForegroundColor Cyan
Write-Host "Workstation Group: $WsGroup" -ForegroundColor Cyan
if ($EnvGroup -gt 0) {
    Write-Host "Environment Group: $EnvGroup" -ForegroundColor Cyan
}
Write-Host ""

# --- Test each hostname ---

$passed = 0
$failed = 0

foreach ($hn in $Hostnames) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  HOSTNAME: $hn" -ForegroundColor Yellow
    Write-Host "------------------------------------------------------------"

    if ($hn -match $Regex) {
        # Save all capture groups before $matches gets overwritten
        $groups = @{}
        for ($i = 0; $i -lt $matches.Count; $i++) {
            $groups[$i] = $matches[$i]
        }
        $totalGroups = $matches.Count - 1

        Write-Host "  Result:         MATCH" -ForegroundColor Green
        Write-Host "  Capture Groups: $totalGroups"
        for ($i = 1; $i -le $totalGroups; $i++) {
            Write-Host "    Group ${i}: $($groups[$i])"
        }

        # Extract values using configured group mappings
        $storeId = if ($StoreGroup -le $totalGroups) { $groups[$StoreGroup] } else { "N/A" }
        $wsId    = if ($WsGroup -le $totalGroups)    { $groups[$WsGroup] }    else { "N/A" }

        # Apply store number extraction (same logic as generated scripts)
        $storeNumber = $storeId
        if ($storeId -match '.*-(\d{4})$') {
            $storeNumber = $matches[1]
        }

        # Validate (same rules as generated scripts)
        $validStore = $storeNumber -match '^[A-Za-z0-9_.-]+$'
        $validWs    = $wsId -match '^[0-9]+$'

        Write-Host ""
        Write-Host "  Store ID:       $storeNumber" -ForegroundColor $(if ($validStore) { "Green" } else { "Red" })
        Write-Host "  Workstation ID: $wsId" -ForegroundColor $(if ($validWs) { "Green" } else { "Red" })

        if ($EnvGroup -gt 0 -and $EnvGroup -le $totalGroups) {
            Write-Host "  Environment:    $($groups[$EnvGroup])" -ForegroundColor Cyan
        }

        if ($validStore -and $validWs) {
            $passed++
        } else {
            Write-Host "  VALIDATION FAILED" -ForegroundColor Red
            $failed++
        }
    } else {
        Write-Host "  Result:         NO MATCH" -ForegroundColor Red
        $failed++
    }

    Write-Host ""
}

# --- Summary ---

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Total:  $($Hostnames.Count)"
Write-Host "  Passed: $passed" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
