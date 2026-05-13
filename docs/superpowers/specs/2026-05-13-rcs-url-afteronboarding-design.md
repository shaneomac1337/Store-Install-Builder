# RCS URL injection via `afterOnboardingProperties`

**Date**: 2026-05-13
**Status**: Approved (pending user review)

## Problem

When `--rcsUrl` is set (either as a direct URL or `autodetect`), the component installer should receive the RCS URL as part of the onboarding token itself, not only as a trailing line in `installationtoken.txt`. The onboarding token request body must include an `afterOnboardingProperties` array entry, e.g.:

```json
{
  "restrictions": {
    "clientType": "opos-onex-cloud",
    "tenantId": "001",
    "lifespan": 86400,
    "maxUsageCount": 10000
  },
  "afterOnboardingProperties": [
    { "key": "rcs.url", "value": "http://localhost:8080/rcs" }
  ]
}
```

This change applies to **all non-RCS components**. The `RCS-SERVICE` onboarding body remains unchanged.

The existing behavior of appending `rcs.url=<url>` to `installationtoken.txt` is preserved unchanged ("belt and suspenders").

## Constraints

- Only triggered when `--rcsUrl` CLI parameter is provided (non-empty).
- `autodetect` resolves via the existing config-service lookup path (`system.properties` → `rcs.url`).
- Disk JSON files in `helper/onboarding/` are NOT mutated. Injection is in-memory only, before POST.
- `RCS-SERVICE` onboarding body remains literally unchanged.
- `MQTT-BROKER` and all other non-RCS components receive the injection.
- Update mode (`isUpdate=true`) skips onboarding entirely; the legacy `onboarding.token` file is reused as today.
- Server-side onboarding endpoint accepts `afterOnboardingProperties` (verified by user).
- Template JSON files in `helper/onboarding/` do NOT contain an `afterOnboardingProperties` field today, so injection always adds a new key, never overwrites.

## Architecture

### Current flow (today)

```
GKInstall.ps1 starts
   |
   v
[For each component, if !isUpdate]
   onboarding.ps1 -ComponentType X
     - acquires OAuth access_token, writes access_token.txt
     - POSTs helper/onboarding/<component>.onboarding.json as-is
     - saves onboarding.token
   |
   v
Autodetect block (if $rcsUrl -eq "autodetect")
   - reads access_token.txt
   - calls config-service child-nodes
   - calls config-service parameter-contents (system.properties)
   - regex-extracts rcs.url
   - sets $rcsUrl to resolved value
   |
   v
Installation token assembly
   - if $rcsUrl set: append "`nrcs.url=$rcsUrl" to installationtoken.txt
```

### New flow

```
GKInstall.ps1 starts
   |
   v
[If $rcsUrl is set]
   Pre-acquire OAuth access_token (new block in GKInstall, reuses pattern at line 1334+)
     - writes access_token.txt
   |
   v
[If $rcsUrl -eq "autodetect"]
   Autodetect block runs HERE (moved up from line 2144)
     - reads access_token.txt (just created)
     - resolves $rcsUrl to actual URL
     - on failure: same prompt as today (continue without / abort)
   |
   v
[For each component, if !isUpdate]
   onboarding.ps1 -ComponentType X -rcsUrl $rcsUrl    <-- NEW PARAM
     - re-acquires OAuth (overwrites access_token.txt — harmless)
     - reads helper/onboarding/<component>.onboarding.json
     - IF $rcsUrl set AND ComponentType -ne "RCS-SERVICE":
         parse JSON in-memory
         inject afterOnboardingProperties array
         re-serialize
     - POSTs body
     - saves onboarding.token
   |
   v
Installation token assembly (UNCHANGED)
   - if $rcsUrl set: append "`nrcs.url=$rcsUrl" to installationtoken.txt
```

## Components

### `GKInstall.ps1.template` / `GKInstall.sh.template`

**New block (PowerShell):**
```powershell
# Pre-acquire OAuth + resolve RCS URL before onboarding
if ($rcsUrl) {
    # OAuth acquisition (extract or copy pattern from line 1334+)
    # writes helper\tokens\access_token.txt

    if ($rcsUrl -eq "autodetect") {
        # Existing autodetect logic (currently at line 2144-2221) moved here
        # On success: $rcsUrl = resolved value
        # On failure: prompt user (continue/abort), same as today
    }
}

# Existing per-component onboarding loop — pass new -rcsUrl param
.\onboarding.ps1 -ComponentType $ComponentType -base_url $base_url -tenant_id $tenantId -rcsUrl $rcsUrl
```

**Remove duplicate:** The autodetect block originally at line 2144-2221 is deleted (logic moved up).

**Preserved:** Lines 2223-2226 — `if ($rcsUrl -and $rcsUrl -ne "autodetect") { $installationToken += "`nrcs.url=$rcsUrl" }` stays. By the time we reach this point, `$rcsUrl` is either empty (autodetect failed and user continued) or a resolved URL. The `-ne "autodetect"` guard is now a no-op (autodetect already resolved or emptied) but kept for safety.

**Bash mirror:** Same restructure in `.sh.template`. Use jq for JSON manipulation if available; fall back to manual key insertion via sed/awk for environments without jq (same `JQ_AVAILABLE` flag pattern already used at line 837-840).

### `onboarding.ps1.template` / `onboarding.sh.template`

**New param:**
```powershell
param(
    [string]$ComponentType,
    [string]$base_url,
    [string]$tenant_id,
    [string]$rcsUrl = ""   # NEW
)
```

**Modified body assembly (PowerShell):**
```powershell
$body = Get-Content -Path $jsonPath -Raw

if ($rcsUrl -and $ComponentType -ne "RCS-SERVICE") {
    $bodyObj = $body | ConvertFrom-Json
    $afterProps = @(@{ key = "rcs.url"; value = $rcsUrl })
    $bodyObj | Add-Member -NotePropertyName afterOnboardingProperties -NotePropertyValue $afterProps
    $body = $bodyObj | ConvertTo-Json -Depth 10
}

# Existing POST stays the same
Invoke-RestMethod -Uri $onboardingUrl -Method Post -Headers $headers -Body $body
```

**Bash equivalent (jq):**
```bash
body=$(cat "$jsonPath")
if [ -n "$rcs_url" ] && [ "$ComponentType" != "RCS-SERVICE" ]; then
    if command -v jq >/dev/null 2>&1; then
        body=$(echo "$body" | jq --arg url "$rcs_url" \
            '. + {afterOnboardingProperties: [{key: "rcs.url", value: $url}]}')
    else
        # Fallback: manual injection before closing brace
        body=$(echo "$body" | sed 's/}$/,"afterOnboardingProperties":[{"key":"rcs.url","value":"'"$rcs_url"'"}]}/')
    fi
fi
curl -X POST ... --data "$body"
```

## Data flow

| Step | Input | Output |
|------|-------|--------|
| 1. GKInstall parses CLI | `--rcsUrl <val>` | `$rcsUrl` populated |
| 2. (if rcsUrl set) Pre-acquire OAuth | credentials from `helper/tokens/` | `access_token.txt` |
| 3. (if autodetect) Resolve URL | bearer token, storeNumber, tenantId | `$rcsUrl` = resolved URL |
| 4. onboarding.ps1 per component | `-rcsUrl $rcsUrl`, JSON template | POST body (with/without `afterOnboardingProperties`) → onboarding.token |
| 5. Installation token | `$rcsUrl`, onboarding.token | `installationtoken.txt` (with `rcs.url=` line if set) |

## Error handling

- **Autodetect API call fails** (network, auth, structure): same prompt as today — "Continue without rcs.url? Y/abort". If Y → `$rcsUrl=""` → no injection, no install token append.
- **JSON parsing fails** in onboarding.ps1: log warning, fall back to POSTing original unmodified body. Don't fail the whole install over the injection.
- **Server rejects body** (if afterOnboardingProperties unsupported): caught by existing try/catch in onboarding.ps1, logged via `Log-ApiResponse -Status "FAILURE"`. Component install aborted as today.

## Testing

| Test | Expectation |
|------|-------------|
| rcsUrl unset, all components | Body unchanged from today. No new fields. |
| rcsUrl = literal URL, POS | Body has `afterOnboardingProperties[0] = {key:"rcs.url", value:"<url>"}` |
| rcsUrl = literal URL, RCS-SERVICE | Body unchanged. No injection. |
| rcsUrl = literal URL, MQTT-BROKER | Body has afterOnboardingProperties. |
| rcsUrl = autodetect, autodetect succeeds | Resolved URL appears in afterOnboardingProperties for non-RCS components |
| rcsUrl = autodetect, autodetect fails + user continues | No injection (rcsUrl emptied) |
| rcsUrl set, isUpdate=true | onboarding skipped (no injection); installationtoken.txt still gets line |
| Bash: rcsUrl set, jq available | jq path used, body modified correctly |
| Bash: rcsUrl set, jq unavailable | sed fallback inserts field correctly |

Add unit tests to `tests/unit/test_generator_integration.py` covering generated script content (regex assertions on rendered `.ps1` / `.sh` files).

## Files Changed

1. `gk_install_builder/templates/GKInstall.ps1.template` — relocate autodetect block, add OAuth pre-acquisition, pass `-rcsUrl` to onboarding.ps1
2. `gk_install_builder/templates/GKInstall.sh.template` — same for bash
3. `gk_install_builder/templates/onboarding.ps1.template` — new `-rcsUrl` param, in-memory JSON injection
4. `gk_install_builder/templates/onboarding.sh.template` — new `--rcsUrl` arg, jq + sed fallback injection
5. `tests/unit/test_generator_integration.py` — new assertions on generated script content

## Out of scope

- No change to `installationtoken.txt` legacy `rcs.url=` line — kept unchanged.
- No change to `system.properties` storage format on RCS side.
- No change to the autodetect API endpoint or its response parsing.
- No change to `helper/onboarding/*.onboarding.json` files on disk.
- No new CLI parameters beyond reusing `--rcsUrl`.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| OAuth pre-acquisition fails in environments where onboarding.ps1's acquisition would succeed | Low | Use identical credential paths; reuse existing pattern at line 1334+. |
| Bash sed fallback corrupts JSON when template body shape changes | Medium | Anchor sed pattern to closing `}` at end of file. Add unit test for fallback. Both jq and sed paths covered in tests. |
| Update mode (isUpdate=true) installations get stale onboarding.token without new properties | Low | Existing limitation. Documented. Fresh install required to pick up afterOnboardingProperties. |
| Autodetect ordering change (now pre-onboarding) breaks if storeNumber/tenantId not yet resolved | Low | Verified: `$tenantId` finalized by line 1329, `$storeNumber` by line ~1973, onboarding call at line 1997. New block fits at line ~1990. |

## Open questions

None. Design complete pending user review.
