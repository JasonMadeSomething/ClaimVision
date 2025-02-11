# Load API details and credentials from payload file
$payloadPath = "$PSScriptRoot\..\payloads\admin_role_test.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.BaseUrl
$adminUsername = $payload.AdminUsername
$adminPassword = $payload.AdminPassword
$userToModify = $payload.UserToModify
$role = $payload.Role

Write-Host "🌍 Base API URL: $baseUrl"

# Step 1: Authenticate Admin
$response = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
    -Method Post `
    -Headers @{"Content-Type"="application/json"} `
    -Body (ConvertTo-Json -Compress -Depth 2 @{
        username = $adminUsername
        password = $adminPassword
    }) `
    -UseBasicParsing

$token = ($response.Content | ConvertFrom-Json).id_token

# Debug: Ensure token is retrieved
if (-not $token) {
    Write-Host "❌ ERROR: Access token is null or empty!"
    exit 1
}

Write-Host "🔑 Retrieved Access Token"

# Step 2: Modify User Role (Add user to "admin" group)
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{"action" = "add"; "role" = $role} | ConvertTo-Json -Compress

$response = Invoke-WebRequest -Uri "$baseUrl/admin/users/$userToModify/role" `
    -Method Put `
    -Headers $headers `
    -Body $body `
    -UseBasicParsing

Write-Host "✅ Role Addition Response: $($response.Content)"

# Step 3: Remove user from "admin" group
$body = @{"action" = "remove"; "role" = $role} | ConvertTo-Json -Compress

$response = Invoke-WebRequest -Uri "$baseUrl/admin/users/$userToModify/role" `
    -Method Put `
    -Headers $headers `
    -Body $body `
    -UseBasicParsing

Write-Host "✅ Role Removal Response: $($response.Content)"
