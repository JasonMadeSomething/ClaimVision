# Load API details and credentials from payload file
$payloadPath = "$PSScriptRoot\..\payloads\admin_test.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.BaseUrl
$Username = $payload.Username
$Password = $payload.Password
$UserPoolId = $payload.UserPoolId

Write-Host "Base API URL: $baseUrl"

# Step 1: Cleanup (Ensure no existing test admin users)
Write-Host "Cleaning up existing admin users before test..."
aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $Username --no-cli-pager 2>$null

# Step 2: Create Admin User (Setup)
Write-Host "Creating test admin user: $Username"
aws cognito-idp admin-create-user --user-pool-id $UserPoolId --username $Username `
    --user-attributes Name="email",Value="$Username@example.com" Name="email_verified",Value="true" `
    --message-action SUPPRESS

Write-Host "Setting password for test admin user: $Username"
aws cognito-idp admin-set-user-password --user-pool-id $UserPoolId --username $Username `
    --password $Password --permanent

Write-Host "Adding user to the admin group"
aws cognito-idp admin-add-user-to-group --user-pool-id $UserPoolId --username $Username --group-name "admin"

Start-Sleep -Seconds 5 # Wait to ensure user propagation in Cognito

# Step 3: Authenticate Admin and Retrieve Token
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

if (-not $token) {
    Write-Host "ERROR: Failed to retrieve access token!"
    exit 1
}

Write-Host "Access token retrieved successfully"

# Step 4: Define Headers
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}

# Step 5: Fetch Admin Users
$adminUsersUrl = "$baseUrl/admin/users"
Write-Host "Testing Admin Users Endpoint: $adminUsersUrl"

try {
    $adminUsersResponse = Invoke-WebRequest -Uri $adminUsersUrl `
        -Method Get `
        -Headers $headers `
        -UseBasicParsing

    Write-Host "Admin Users Response: $($adminUsersResponse.Content | ConvertFrom-Json | ConvertTo-Json -Depth 3)"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
    exit 1
}

# Step 6: Cleanup (Remove test admin user after test)
Write-Host "Cleaning up test admin user..."
aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $Username --no-cli-pager

Write-Host "Test completed successfully"
