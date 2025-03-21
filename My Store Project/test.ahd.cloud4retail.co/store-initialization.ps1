param (
    [Parameter(Mandatory=$true)]
    [string]$ComponentType,
    [Parameter(Mandatory=$true)]
    [string]$base_url,
    [Parameter(Mandatory=$true)]
    [string]$StoreId,
    [Parameter(Mandatory=$true)]
    [string]$WorkstationId
)

# Paths
$tokensPath = Join-Path $PSScriptRoot "helper\tokens"

# Verify paths exist
if (-Not (Test-Path $tokensPath)) {
    Write-Host "Tokens path does not exist: $tokensPath"
    exit 1
}

# Read the access token created by onboarding.ps1
$accessTokenPath = Join-Path $tokensPath "access_token.txt"
if (-Not (Test-Path $accessTokenPath)) {
    Write-Host "Access token file does not exist. Please run onboarding.ps1 first."
    exit 1
}

$accessToken = Get-Content -Path $accessTokenPath -Raw

# Common headers for all API calls
$headers = @{
    "Authorization" = "Bearer $accessToken"
    "Content-Type" = "application/json; variant=Plain; charset=UTF-8"
    "Accept" = "application/json; variant=Plain; charset=UTF-8"
    "GK-Accept-Redirect" = "308"
}

# Map ComponentType to systemName for matching in the API response
$systemNameMap = @{
    'POS' = 'AHD-OPOS-CLOUD'
    'WDM' = 'AHD-wdm'
    'FLOW-SERVICE' = 'GKR-FLOWSERVICE-CLOUD'
    'LPA-SERVICE' = 'AHD-lps-lpa'
    'STOREHUB-SERVICE' = 'AHD-sh-cloud'
}

# Get the systemName for the current component
$currentSystemName = $systemNameMap[$ComponentType]
if (-Not $currentSystemName) {
    Write-Host "Error: No systemName mapping found for ComponentType: $ComponentType"
    Write-Host "Cannot proceed without a valid system name mapping."
    exit 1
}

Write-Host "Using systemName: $currentSystemName for component: $ComponentType"

try {
    # First API call - Get Business Unit
    $buUrl = "https://$base_url/swee-sdc/tenants/003/services/rest/master-data/v1/business-units/$StoreId"
    $buResponse = Invoke-RestMethod -Uri $buUrl -Method Get -Headers $headers
    Write-Host "Successfully retrieved business unit information"
    
    # Extract businessUnitGroupID from the key object in the response
    $businessUnitGroupId = $buResponse.key.businessUnitGroupID
    
    if (-Not $businessUnitGroupId) {
        Write-Host "Failed to get businessUnitGroupID from response"
        Write-Host "Response content:"
        Write-Host ($buResponse | ConvertTo-Json -Depth 10)
        exit 1
    }

    Write-Host "Found businessUnitGroupID: $businessUnitGroupId"

    # Second API call - Try to Get Workstation first
    $wsUrl = "https://$base_url/swee-sdc/tenants/003/services/rest/master-data/v1/workstations/(businessUnitGroupId=$businessUnitGroupId,workstationId=$WorkstationId)"
    try {
        $wsResponse = Invoke-RestMethod -Uri $wsUrl -Method Get -Headers $headers
        Write-Host "Successfully retrieved existing workstation information"
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 404) {
            Write-Host "Workstation not found, creating new workstation..."
            
            # Determine workstation type based on ComponentType
            $typeCode = switch ($ComponentType) {
                'LPA-SERVICE' { 'LPAS' }
                'STOREHUB-SERVICE' { 'SHS' }
                'FLOW-SERVICE' { 'EDGE' }
                'POS' { 'POS' }
                'WDM' { 'WDM' }
                default { 'POS' }
            }

            # Create workstation payload
            $wsCreateUrl = "https://$base_url/swee-sdc/tenants/003/services/rest/master-data/v1/workstations"
            $wsPayload = @{
                workstation = @{
                    key = @{
                        workstationID = $WorkstationId
                        businessUnitGroupID = $businessUnitGroupId
                    }
                    typeCode = $typeCode
                    createTimestampUTC0 = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
                }
            } | ConvertTo-Json -Depth 10

            $wsResponse = Invoke-RestMethod -Uri $wsCreateUrl -Method Post -Headers $headers -Body $wsPayload
            Write-Host "Successfully created new workstation"
        }
        else {
            Write-Host "Error accessing workstation:"
            Write-Host $_
            if ($_.Exception.Response) {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $reader.BaseStream.Position = 0
                $reader.DiscardBufferedData()
                $responseBody = $reader.ReadToEnd()
                Write-Host "Response body: $responseBody"
            }
            exit 1
        }
    }

    # Save responses to files for reference
    $buResponse | ConvertTo-Json -Depth 10 | Set-Content -Path "business-unit.json" -NoNewline
    $wsResponse | ConvertTo-Json -Depth 10 | Set-Content -Path "workstation.json" -NoNewline
    Write-Host "Saved response data to business-unit.json and workstation.json"

    # Get store information using get_store.json
    $initPath = Join-Path $PSScriptRoot "helper\init"
    $getStoreJsonPath = Join-Path $initPath "get_store.json"
    
    if (-Not (Test-Path $initPath)) {
        New-Item -ItemType Directory -Path $initPath -Force | Out-Null
        Write-Host "Created init directory: $initPath"
    }
    
    if (-Not (Test-Path $getStoreJsonPath)) {
        Write-Host "Warning: get_store.json not found at: $getStoreJsonPath"
    } else {
        Write-Host "Making API call to get store information..."
        
        # Read the get_store.json file
        $getStoreJson = Get-Content -Path $getStoreJsonPath -Raw
        
        # Make the API call to get store information
        $storeUrl = "https://$base_url/config-service/services/rest/infrastructure/v1/structure/child-nodes/search"
        
        try {
            $storeResponse = Invoke-RestMethod -Uri $storeUrl -Method Post -Headers $headers -Body $getStoreJson -ContentType "application/json; variant=Plain; charset=UTF-8"
            Write-Host "Successfully retrieved store information"
            
            # Save the response to storemanager.json
            $storemanagerPath = Join-Path $initPath "storemanager.json"
            $storeResponse | ConvertTo-Json -Depth 10 | Set-Content -Path $storemanagerPath -NoNewline
            Write-Host "Store information saved to: $storemanagerPath"
            
            # Extract structure unique name for the current component
            $structureUniqueName = ""
            if (Test-Path $storemanagerPath) {
                try {
                    $storeManagerData = Get-Content -Path $storemanagerPath -Raw | ConvertFrom-Json
                    
                    # Look for the structure that matches our system name
                    foreach ($item in $storeManagerData.childNodeList) {
                        if ($item.systemName -eq $currentSystemName) {
                            $structureUniqueName = $item.structureUniqueName
                            Write-Host "Found matching structure for ${currentSystemName}: $structureUniqueName"
                            break
                        }
                    }
                    
                    if ([string]::IsNullOrEmpty($structureUniqueName)) {
                        Write-Host "Error: No matching structure found for system name: ${currentSystemName}"
                        Write-Host "Cannot proceed without a matching structure in the API response."
                        exit 1
                    }
                } catch {
                    Write-Host "Error parsing storemanager.json: $_"
                    Write-Host "Cannot proceed without a valid structure pattern from the API response."
                    exit 1
                }
            } else {
                Write-Host "Error: storemanager.json not found"
                Write-Host "Cannot proceed without a valid structure pattern from the API response."
                exit 1
            }
            
            # Save the structure unique name to a file for reference
            $structureNamePath = Join-Path $initPath "structure_name.txt"
            $structureUniqueName | Set-Content -Path $structureNamePath -NoNewline
            Write-Host "Structure unique name saved to: $structureNamePath"
            
            # Only proceed with configuration update for StoreHub components
            if ($ComponentType -eq 'STOREHUB-SERVICE' -or $ComponentType -eq 'SH') {
                # Now update the configuration using update_config.json from the storehub directory
                $storehubDir = Join-Path $initPath "storehub"
                $updateConfigPath = Join-Path $storehubDir "update_config.json"
                
                if (Test-Path $updateConfigPath) {
                    Write-Host "Updating StoreHub configuration using update_config.json..."
                    
                    # Read the update_config.json template
                    $updateConfigJson = Get-Content -Path $updateConfigPath -Raw
                    
                    # Get hostname
                    $hostname = $env:COMPUTERNAME
                    if ([string]::IsNullOrEmpty($hostname)) {
                        $hostname = "localhost"
                    }
                    
                    # Get version from config
                    $version = "v1.1.0"  # Default version
                    
                    # Replace placeholders in the template
                    $updateConfigJson = $updateConfigJson -replace '@STRUCTURE_UNIQUE_NAME@', $structureUniqueName
                    $updateConfigJson = $updateConfigJson -replace '@HOSTNAME@', $hostname
                    
                    # Write the updated content back to the file
                    $updateConfigJson | Set-Content -Path $updateConfigPath -NoNewline
                    Write-Host "Updated update_config.json with structure unique name and hostname"
                    
                    # Make the API call to update the configuration
                    $configUrl = "https://$base_url/config-service/services/rest/config-management/v1/parameter-contents/plain"
                    
                    try {
                        $configResponse = Invoke-RestMethod -Uri $configUrl -Method Post -Headers $headers -Body $updateConfigJson -ContentType "application/json; variant=Plain; charset=UTF-8"
                        Write-Host "Successfully updated StoreHub configuration"
                        
                        # Save the response to config_response.json
                        $configResponsePath = Join-Path $storehubDir "config_response.json"
                        $configResponse | ConvertTo-Json -Depth 10 | Set-Content -Path $configResponsePath -NoNewline
                        Write-Host "Configuration response saved to: $configResponsePath"
                    } catch {
                        Write-Host "Error updating StoreHub configuration: $_"
                        if ($_.Exception.Response) {
                            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                            $reader.BaseStream.Position = 0
                            $reader.DiscardBufferedData()
                            $responseBody = $reader.ReadToEnd()
                            Write-Host "Response body: $responseBody"
                        }
                        # Continue execution even if this call fails
                    }
                } else {
                    Write-Host "Warning: StoreHub update_config.json not found at: $updateConfigPath"
                }
            } else {
                Write-Host "Skipping configuration update - not a StoreHub component"
            }
        } catch {
            Write-Host "Error retrieving store information: $_"
            if ($_.Exception.Response) {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $reader.BaseStream.Position = 0
                $reader.DiscardBufferedData()
                $responseBody = $reader.ReadToEnd()
                Write-Host "Response body: $responseBody"
            }
            # Continue execution even if this call fails
        }
    }

    # Explicitly return success
    exit 0
}
catch {
    Write-Host "Error occurred: $_"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $reader.DiscardBufferedData()
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response body: $responseBody"
    }
    exit 1
} 