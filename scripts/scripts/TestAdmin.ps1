# Load API details and credentials from payload file
$payloadPath = "$PSScriptRoot\..\payloads\admin_test.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.BaseUrl
$Username = $payload.Username
$Password = $payload.Password

Write-Host "🌍 Base API URL: $baseUrl"

# Step 1: Authenticate Admin and Retrieve Token
$response = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
    -Method Post `
    -Headers @{"Content-Type"="application/json"} `
    -Body (ConvertTo-Json -Compress -Depth 2 @{
        username = $Username
        password = $Password
    }) `
    -UseBasicParsing

# Extract access token safely
$token = ($response.Content | ConvertFrom-Json).id_token

Write-Host "🔑 Retrieved Access Token"

# Debug: Ensure token is retrieved
if (-not $token) {
    Write-Host "❌ ERROR: Access token is null or empty!"
    exit 1
}

# Step 2: Define Headers
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}

# Step 3: Fetch Admin Users
$adminUsersUrl = "$baseUrl/admin/users"
Write-Host "📡 Testing Admin Users Endpoint: $adminUsersUrl"

try {
    $adminUsersResponse = Invoke-WebRequest -Uri $adminUsersUrl `
        -Method Get `
        -Headers $headers `
        -UseBasicParsing

    Write-Host "✅ Admin Users Response: $($adminUsersResponse.Content | ConvertFrom-Json | ConvertTo-Json -Depth 3)"
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)"
}
