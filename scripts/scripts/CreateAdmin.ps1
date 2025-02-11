# Load API details and credentials from payload file
$payloadPath = "$PSScriptRoot\..\payloads\admin_user.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.BaseUrl
$UserPoolId = $payload.UserPoolId
$Username = $payload.Username
$Password = $payload.Password
$Email = $payload.Email
$GroupName = $payload.GroupName

Write-Host "Base API URL: $baseUrl"

# ✅ Step 1: Cleanup before running the test
Write-Host "Cleaning up existing admin users before test..."
aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $Username --no-cli-pager 2>$null

# ✅ Step 2: Create Admin User (Setup)
try {
    Write-Host "Creating test admin user: $Username"
    aws cognito-idp admin-create-user --user-pool-id $UserPoolId --username $Username `
        --user-attributes Name="email",Value="$Email" Name="email_verified",Value="true" `
        --message-action SUPPRESS

    Write-Host "Setting password for test admin user: $Username"
    aws cognito-idp admin-set-user-password --user-pool-id $UserPoolId --username $Username `
        --password $Password --permanent

    Write-Host "Adding user to the admin group"
    aws cognito-idp admin-add-user-to-group --user-pool-id $UserPoolId --username $Username --group-name $GroupName

    Start-Sleep -Seconds 5  # Ensures Cognito user creation has propagated

} catch {
    Write-Host "ERROR: Failed to create admin user. Running cleanup..."
    aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $Username --no-cli-pager
    exit 1
}

# ✅ Step 3: Authenticate Admin and Retrieve Token
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
        -Method Post `
        -Headers @{"Content-Type"="application/json"} `
        -Body (ConvertTo-Json -Compress -Depth 2 @{
            username = $Username
            password = $Password
        }) `
        -UseBasicParsing

    # Extract access token
    $token = ($response.Content | ConvertFrom-Json).id_token

    if (-not $token) {
        throw "Failed to retrieve access token!"
    }

    Write-Host "Access token retrieved successfully"

} catch {
    Write-Host "ERROR: Failed to authenticate admin user. Running cleanup..."
    aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $Username --no-cli-pager
    exit 1
}

# ✅ Step 4: Assign Admin Role via API
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}

$roleAssignmentUrl = "$baseUrl/admin/users/$Username/role"

try {
    Write-Host "Assigning admin role to user via API: $roleAssignmentUrl"
    $body = @{ action = "add"; role = "admin" } | ConvertTo-Json -Compress

    $roleResponse = Invoke-WebRequest -Uri $roleAssignmentUrl `
        -Method Put `
        -Headers $headers `
        -Body $body `
        -UseBasicParsing

    Write-Host "Admin role assigned successfully"

} catch {
    Write-Host "ERROR: Failed to assign admin role. Running cleanup..."
    aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $Username --no-cli-pager
    exit 1
}

# ✅ Step 5: Cleanup after the test (Optional: Can be skipped if the user should persist)
try {
    Write-Host "Cleaning up test admin user..."
    aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $Username --no-cli-pager
    Write-Host "Test completed successfully"
} catch {
    Write-Host "WARNING: Failed to clean up test admin user."
}
