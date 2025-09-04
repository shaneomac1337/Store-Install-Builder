# Test script to debug Employee Hub Service API call
param(
    [string]$base_url = "test.cse.cloud4retail.co",
    [string]$tenant_id = "001",
    [string]$fresh_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Im9hdXRoMi5rZXkuMSJ9.eyJzY29wZSI6WyJHSyJdLCJpZF90b2tlbiI6eyJ0ZW5hbnRfaWQiOiIwMDEiLCJzdWIiOiIxMDAxIiwic2VsZWN0ZWRfc3RvcmUiOnsiYnVzaW5lc3NVbml0R3JvdXBJZCI6IjEwMDAwMDAwMDAwMDAwMTUwNyIsInN0b3JlTmFtZSI6IklkbmV0IFRlc3QgU3RvcmUiLCJzdG9yZUlkIjoiOTk5OSJ9LCJwcmVmZXJyZWRfdXNlcm5hbWUiOiIxMDAxIiwiZ2l2ZW5fbmFtZSI6bnVsbCwibG9jYWxlIjoiZW4tVVMiLCJhdXRob3JpdGllcyI6WyJiOmN1c3QuY3VzdG9tZXIuaW1wb3J0ZXIiLCJiOnRlbmFudC5zdGF0dXMubWFuYWdlbWVudCIsImI6dGVuYW50Lm1ndC5jcmVhdG9yIiwiYWRtaW5fZ2xvYmFsIiwiYjpjdXN0LmN1c3RvbWVyLmNyZWF0ZSIsImI6aWFtLmNsaWVudC5tYW5hZ2VyIiwiYjpjdXN0LmN1c3RvbWVyLmRlbGV0ZSIsImI6ZnJhdWQudHguY2ZnLWJ1IiwiYWRtaW4iLCJiOmVpbnYudmFsaWRhdGlvbiIsImNwc19yZXN0X2FwaV9yZXNvdXJjZXMiLCJST0xFX0JBU0tFVF9SRUFEIiwiYjpjdXN0LmN1c3RvbWVyLnJlYWQiLCJiOmJ1c2luZXNzLWtwaS5tZXRyaWMucmVhZGVyIiwiYjplaW52LmNyZWF0aW9uIiwiYjpjdXN0LmN1c3RvbWVyLmFnZVZlcmlmaWVyIiwiYjpjdXN0LnByaXZhY3kucmVhZCIsImZkc19yZXN0X2FwaV9yZXNvdXJjZXMiLCJiOmNvbmZpZy5hbnktY2ZnLmVkaXQiLCJiOmNvbmZpZy5hbnktY2ZnLnJlYWQiLCJiOmJ1c2luZXNzLWtwaS5tc3ItcmVxLmNyZWF0b3IiLCJiOmRzZy5jb250ZW50Lm1hbmFnZSIsImI6Y3VzdC5jdXN0b21lci5lZGl0IiwiQ1NFX2FkbWluIl0sImF1ZCI6W10sImF6cCI6ImxhdW5jaHBhZCIsImV4cCI6MTc1NjExNzI1MiwiaWF0IjoxNzU2MTEzNjUyLCJmYW1pbHlfbmFtZSI6bnVsbCwiZW1haWwiOm51bGwsInByb3BlcnRpZXMiOnsicmVhbG0iOiJURUNITklDQUwifX0sImV4cCI6MTc1NjExNzI1MiwianRpIjoiOWI0ZTk1MjktM2I5Ni00MTkzLTk2MjUtNmVhYjczMTk5YTU5IiwiY2xpZW50X2lkIjoibGF1bmNocGFkIn0.Jg5P1g4o1JmG-P8-gmq-64xsvjQ-zrWEgundw7IHgqYsafQfbEMKLE183wx8uBWPLK15ao8Cw3jg_RES8tXP6-Ei1JWVHSHgR9WuHFVH7My0lwWTuznVDbUp2T9laK4bqDCC5RnMlFpNEBNY3--0zBuVOfrsbm10jYKMthdrbVNQ5wTyospPINuSnLlwLqPJP6qzmqQHKY5hnVPFr4Zpz-CXTgE-n1Ds2bxYLfdTj1XS9LHANvWaFENMYWEkdksatJGACazT8_VMtJ_ZSIwdsFvh6Zl8IJjOVxxzCO1YpdeqhHnzb5-fJLBoQEOm6FPulQrrrYQutE156a44yMJULA"
)

Write-Host "=== Employee Hub Service API Test ==="
Write-Host "Base URL: $base_url"
Write-Host "Tenant ID: $tenant_id"
Write-Host ""

# Test 1: Check if token file exists
Write-Host "1. Checking token file..."
$tokenFile = Join-Path $PSScriptRoot "helper\tokens\access_token.txt"
Write-Host "Token file path: $tokenFile"

if (-not (Test-Path $tokenFile)) {
    Write-Host "❌ ERROR: Bearer token file not found at $tokenFile"
    Write-Host "Available files in helper\tokens:"
    $tokensDir = Join-Path $PSScriptRoot "helper\tokens"
    if (Test-Path $tokensDir) {
        Get-ChildItem $tokensDir | ForEach-Object { Write-Host "  - $($_.Name)" }
    } else {
        Write-Host "  ❌ Tokens directory doesn't exist: $tokensDir"
    }
    exit 1
}

$bearerToken = Get-Content $tokenFile -Raw
if ([string]::IsNullOrWhiteSpace($bearerToken)) {
    Write-Host "❌ ERROR: Bearer token is empty"
    exit 1
}

$bearerToken = $bearerToken.Trim()
Write-Host "✅ Token file found and loaded (length: $($bearerToken.Length) characters)"
Write-Host "Token preview: $($bearerToken.Substring(0, [Math]::Min(50, $bearerToken.Length)))..."
Write-Host ""

# Test 2: Test basic connectivity
Write-Host "2. Testing basic connectivity..."
$testUrl = "https://$base_url"
try {
    $testResponse = Invoke-WebRequest -Uri $testUrl -Method Head -TimeoutSec 10 -UseBasicParsing
    Write-Host "✅ Basic connectivity OK (Status: $($testResponse.StatusCode))"
} catch {
    Write-Host "❌ Basic connectivity failed: $($_.Exception.Message)"
}
Write-Host ""

# Test 3: Test API endpoint with minimal request
Write-Host "3. Testing API endpoint with minimal request..."
$apiUrl = "https://$base_url/employee-hub-service/services/rest/v1/properties?scope=FP&referenceId=platform"
Write-Host "API URL: $apiUrl"

try {
    # Simple request with just authorization header
    $headers = @{
        "authorization" = "Bearer $bearerToken"
    }
    
    Write-Host "Making request with authorization header only..."
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -Headers $headers -TimeoutSec 30
    Write-Host "✅ API call successful!"
    Write-Host "Response type: $($response.GetType().Name)"
    Write-Host "Response count: $($response.Count)"
    
    # Show first few properties
    Write-Host ""
    Write-Host "First 5 properties:"
    $response | Select-Object -First 5 | ForEach-Object {
        Write-Host "  - $($_.propertyId): $($_.value)"
    }
    
} catch {
    Write-Host "❌ API call failed: $($_.Exception.Message)"
    Write-Host "Exception type: $($_.Exception.GetType().Name)"
    if ($_.Exception.Response) {
        Write-Host "HTTP Status: $($_.Exception.Response.StatusCode)"
        Write-Host "HTTP Status Description: $($_.Exception.Response.StatusDescription)"
    }
}
Write-Host ""

# Test 4: Test with both headers
Write-Host "4. Testing API endpoint with both headers..."
try {
    $headers = @{
        "authorization" = "Bearer $bearerToken"
        "gk-tenant-id" = $tenant_id
    }
    
    Write-Host "Making request with authorization + gk-tenant-id headers..."
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -Headers $headers -TimeoutSec 30
    Write-Host "✅ API call with both headers successful!"
    Write-Host "Response count: $($response.Count)"
    
    # Extract version information
    Write-Host ""
    Write-Host "Version information found:"
    $versionProperties = @("POSClient_Version", "WDM_Version", "FlowService_Version", "LPA_Version", "StoreHub_Version")
    foreach ($prop in $versionProperties) {
        $found = $response | Where-Object { $_.propertyId -eq $prop }
        if ($found) {
            Write-Host "  ✅ $prop = $($found.value)"
        } else {
            Write-Host "  ❌ $prop = NOT FOUND"
        }
    }
    
} catch {
    Write-Host "❌ API call with both headers failed: $($_.Exception.Message)"
    Write-Host "Exception type: $($_.Exception.GetType().Name)"
    if ($_.Exception.Response) {
        Write-Host "HTTP Status: $($_.Exception.Response.StatusCode)"
        Write-Host "HTTP Status Description: $($_.Exception.Response.StatusDescription)"
    }
}
Write-Host ""

# Test 5: Test with curl (if available)
Write-Host "5. Testing with curl (if available)..."
try {
    $curlTest = & curl --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ curl is available, testing..."
        $curlCommand = "curl -s -k -H `"authorization: Bearer $bearerToken`" -H `"gk-tenant-id: $tenant_id`" `"$apiUrl`""
        Write-Host "Curl command: $curlCommand"
        
        $curlResponse = & curl -s -k -H "authorization: Bearer $bearerToken" -H "gk-tenant-id: $tenant_id" "$apiUrl"
        if ($LASTEXITCODE -eq 0 -and $curlResponse) {
            Write-Host "✅ Curl request successful!"
            Write-Host "Response length: $($curlResponse.Length) characters"
            Write-Host "Response preview: $($curlResponse.Substring(0, [Math]::Min(200, $curlResponse.Length)))..."
        } else {
            Write-Host "❌ Curl request failed (exit code: $LASTEXITCODE)"
        }
    } else {
        Write-Host "❌ curl not available"
    }
} catch {
    Write-Host "❌ curl test failed: $($_.Exception.Message)"
}

Write-Host ""

# Test 6: Test exact Postman approach
Write-Host "6. Testing exact Postman approach..."
try {
    $headers=@{}
    $headers.Add("authorization", "Bearer $fresh_token")
    $headers.Add("gk-tenant-id", "001")
    $response = Invoke-RestMethod -Uri 'https://test.cse.cloud4retail.co/employee-hub-service/services/rest/v1/properties?scope=FP&referenceId=platform' -Method GET -Headers $headers

    Write-Host "✅ Postman approach successful!"
    Write-Host "Response count: $($response.Count)"

    # Extract version information
    Write-Host ""
    Write-Host "Version information found with Postman approach:"
    $versionProperties = @("POSClient_Version", "WDM_Version", "FlowService_Version", "LPA_Version", "StoreHub_Version")
    foreach ($prop in $versionProperties) {
        $found = $response | Where-Object { $_.propertyId -eq $prop }
        if ($found) {
            Write-Host "  ✅ $prop = $($found.value)"
        } else {
            Write-Host "  ❌ $prop = NOT FOUND"
        }
    }

} catch {
    Write-Host "❌ Postman approach failed: $($_.Exception.Message)"
    Write-Host "Exception type: $($_.Exception.GetType().Name)"
    if ($_.Exception.Response) {
        Write-Host "HTTP Status: $($_.Exception.Response.StatusCode)"
        Write-Host "HTTP Status Description: $($_.Exception.Response.StatusDescription)"
    }
}
Write-Host ""

# Test 7: Test token generation process
Write-Host "7. Testing token generation process..."
try {
    # Check if credential files exist
    $tokensPath = Join-Path $PSScriptRoot "helper\tokens"
    $basicAuthPath = Join-Path $tokensPath "basic_auth_password.txt"
    $formPasswordPath = Join-Path $tokensPath "form_password.txt"

    Write-Host "Tokens path: $tokensPath"
    Write-Host "Basic auth path: $basicAuthPath"
    Write-Host "Form password path: $formPasswordPath"

    if (Test-Path $basicAuthPath) {
        $basicAuthPassword = Get-Content $basicAuthPath -Raw
        Write-Host "✅ Basic auth password found (length: $($basicAuthPassword.Trim().Length))"
    } else {
        Write-Host "❌ Basic auth password file not found"
    }

    if (Test-Path $formPasswordPath) {
        $formPassword = Get-Content $formPasswordPath -Raw
        Write-Host "✅ Form password found (length: $($formPassword.Trim().Length))"
    } else {
        Write-Host "❌ Form password file not found"
    }

    # Try to generate a fresh token
    if ((Test-Path $basicAuthPath) -and (Test-Path $formPasswordPath)) {
        Write-Host ""
        Write-Host "Attempting to generate fresh token..."

        $username = "launchpad"
        $password = Get-Content $basicAuthPath -Raw
        $formPassword = Get-Content $formPasswordPath -Raw

        # Create Basic Auth header
        $base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${username}:$($password.Trim())"))

        # Prepare form data
        $formData = @{
            grant_type = "password"
            username = "1001"
            password = $formPassword.Trim()
        }

        # Make OAuth token request
        $tokenUrl = "https://$base_url/auth-service/tenants/${tenant_id}/oauth/token"
        Write-Host "Token URL: $tokenUrl"
        Write-Host "Username: 1001"
        Write-Host "Grant type: password"

        $tokenResponse = Invoke-RestMethod -Uri $tokenUrl -Method Post -Headers @{Authorization = "Basic $base64Auth"} -Body $formData -ContentType "application/x-www-form-urlencoded"

        $generatedToken = $tokenResponse.access_token
        Write-Host "✅ Fresh token generated successfully!"
        Write-Host "Generated token length: $($generatedToken.Length)"
        Write-Host "Generated token preview: $($generatedToken.Substring(0, [Math]::Min(50, $generatedToken.Length)))..."

        # Test the generated token
        Write-Host ""
        Write-Host "Testing generated token..."
        $testHeaders = @{
            "authorization" = "Bearer $generatedToken"
            "gk-tenant-id" = $tenant_id
        }

        $testResponse = Invoke-RestMethod -Uri $apiUrl -Method Get -Headers $testHeaders -TimeoutSec 30
        Write-Host "✅ Generated token works!"
        Write-Host "Response count: $($testResponse.Count)"

    }

} catch {
    Write-Host "❌ Token generation test failed: $($_.Exception.Message)"
    Write-Host "Exception type: $($_.Exception.GetType().Name)"
    if ($_.Exception.Response) {
        Write-Host "HTTP Status: $($_.Exception.Response.StatusCode)"
        Write-Host "HTTP Status Description: $($_.Exception.Response.StatusDescription)"
    }
}
Write-Host ""

# Test 8: Test with fresh token from parameter (original approach)
if ($fresh_token -and $fresh_token -ne "") {
    Write-Host "6. Testing with fresh token from parameter..."
    try {
        $headers = @{
            "authorization" = "Bearer $fresh_token"
            "gk-tenant-id" = $tenant_id
        }

        Write-Host "Making request with fresh token..."
        $response = Invoke-RestMethod -Uri $apiUrl -Method Get -Headers $headers -TimeoutSec 30
        Write-Host "✅ API call with fresh token successful!"
        Write-Host "Response count: $($response.Count)"

        # Extract version information
        Write-Host ""
        Write-Host "Version information found with fresh token:"
        $versionProperties = @("POSClient_Version", "WDM_Version", "FlowService_Version", "LPA_Version", "StoreHub_Version")
        foreach ($prop in $versionProperties) {
            $found = $response | Where-Object { $_.propertyId -eq $prop }
            if ($found) {
                Write-Host "  ✅ $prop = $($found.value)"
            } else {
                Write-Host "  ❌ $prop = NOT FOUND"
            }
        }

    } catch {
        Write-Host "❌ API call with fresh token failed: $($_.Exception.Message)"
        Write-Host "Exception type: $($_.Exception.GetType().Name)"
        if ($_.Exception.Response) {
            Write-Host "HTTP Status: $($_.Exception.Response.StatusCode)"
            Write-Host "HTTP Status Description: $($_.Exception.Response.StatusDescription)"
        }
    }
    Write-Host ""
}

Write-Host "=== Test Complete ==="
