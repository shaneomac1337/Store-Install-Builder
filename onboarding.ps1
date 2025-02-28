param (
    [string]$ComponentType = "POS",
    [string]$base_url = "test.cse.cloud4retail.co"  # Add this parameter
)

# API endpoint
$url = "https://$base_url/auth-service/tenants/001/oauth/token"

# Basic Auth credentials
$username = "launchpad"

# Function to Base64 encode
function Encode-Base64 {
    param($plainText)
    return [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($plainText))
}

# Function to Base64 decode
function Decode-Base64 {
    param($encodedText)
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encodedText))
}

# Paths
$tokensPath = Join-Path $PSScriptRoot "helper\tokens"
$onboardingPath = Join-Path $PSScriptRoot "helper\onboarding"

# Verify paths exist
if (-Not (Test-Path $tokensPath)) {
    Write-Host "Tokens path does not exist: $tokensPath"
    exit
}

if (-Not (Test-Path $onboardingPath)) {
    Write-Host "Onboarding path does not exist: $onboardingPath"
    exit
}

# Verify files exist
$basicAuthPath = Join-Path $tokensPath "basic_auth_password.txt"
$formPasswordPath = Join-Path $tokensPath "form_password.txt"

if (-Not (Test-Path $basicAuthPath)) {
    Write-Host "Basic auth password file does not exist: $basicAuthPath"
    exit
}

if (-Not (Test-Path $formPasswordPath)) {
    Write-Host "Form password file does not exist: $formPasswordPath"
    exit
}

# Load and decode passwords
$basicAuthPassword = Decode-Base64 (Get-Content $basicAuthPath)
$formPassword = Decode-Base64 (Get-Content $formPasswordPath)

# Use decoded passwords
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${username}:${basicAuthPassword}"))

# Form data with decrypted password
$body = @{
    username = "1001"
    password = $formPassword
    grant_type = "password"
}

# Corrected form data construction using WebUtility
$formData = ($body.GetEnumerator() | ForEach-Object {
    "$([System.Net.WebUtility]::UrlEncode($_.Key))=$([System.Net.WebUtility]::UrlEncode($_.Value))"
}) -join '&'

# Make the API call
try {
    $response = Invoke-RestMethod -Uri $url -Method Post `
        -Headers @{Authorization = "Basic $base64Auth"} `
        -Body $formData `
        -ContentType "application/x-www-form-urlencoded"
    
    # Save the access token without extra newline
    $accessToken = $response.access_token
    Set-Content -Path (Join-Path $tokensPath "access_token.txt") -Value $accessToken -NoNewline
    Write-Host "Access token successfully saved"

    # Second API call using the token
    $onboardingUrl = "https://$base_url/cims/services/rest/cims/v1/onboarding/tokens"
    $headers = @{
        "Authorization" = "Bearer $accessToken"
        "Content-Type" = "application/json"
    }

    # Determine JSON file based on ComponentType
    $jsonFile = if ($ComponentType -eq "WDM") {
        "wdm.onboarding.json"
    } else {
        "pos.onboarding.json"
    }

    # Read JSON from selected file
    $jsonPath = Join-Path $onboardingPath $jsonFile
    try {
        $body = Get-Content -Path $jsonPath -Raw
    }
    catch {
        Write-Host "Error reading JSON file: $_"
        exit
    }

    try {
        $onboardingResponse = Invoke-RestMethod -Uri $onboardingUrl -Method Post `
            -Headers $headers `
            -Body $body
        
        # Save the onboarding token without extra newline
        $onboardingToken = $onboardingResponse.token
        Set-Content -Path "onboarding.token" -Value $onboardingToken -NoNewline
        Write-Host "$ComponentType onboarding token successfully saved to onboarding.token"
    }
    catch {
        Write-Host "Error in $ComponentType onboarding request: $_"
    }
}
catch {
    Write-Host "Error occurred: $_"
} 