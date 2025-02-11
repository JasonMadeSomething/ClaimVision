# Load API details and credentials from payload file
$payloadPath = "$PSScriptRoot\..\payloads\admin_user.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.BaseUrl
$Username = $payload.Username
$Password = $payload.Password
$Email = $payload.Email
$GroupName = $payload.GroupName

Write-Host "Starting test setup for admin user: $Username"

# ✅ Step 1: Cleanup Before Running Test (AWS CLI)
Write-Host "Cleaning up existing admin users before test..."
aws cognito-idp admin-delete-user --user-pool-id $payload.UserPoolId --username $Username --no-cli-pager 2>$null

# ✅ Step 2: Create Admin User via API
try {
    Write-Host "Creating admin user via API..."
    $body = @{
        username = $Username
        password = $Password
        email    = $Email
    } | ConvertTo-Json -Compress

    $registerResponse = Invoke-WebRequest -Uri "$baseUrl/auth/register" `
        -Method Post `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body `
        -UseBasicParsing

    if ($registerResponse.StatusCode -ne 201) {
        throw "Failed to create user. Status Code: $($registerResponse.StatusCode)"
    }

    Write-Host "User registered successfully"
    
} catch {
    Write-Host "ERROR: $_. Running cleanup..."
    aws cognito-idp admin-delete-user --user-pool-id $payload.UserPoolId --username $Username --no-cli-pager 2>$null
    exit 1
}

# ✅ Step 3: Confirm User using AWS CLI (since confirmation code is not available via API)
try {
    Write-Host "Confirming admin user using AWS CLI..."
    
    aws cognito-idp admin-confirm-sign-up --user-pool-id $payload.UserPoolId --username $Username --no-cli-pager

    Write-Host "User confirmed successfully"

} catch {
    Write-Host "ERROR: $_. Running cleanup..."
    aws cognito-idp admin-delete-user --user-pool-id $payload.UserPoolId --username $Username --no-cli-pager 2>$null
    exit 1
}


# ✅ Step 4: Authenticate Admin and Retrieve Token via API
try {
    Write-Host "Authenticating admin user..."
    $loginBody = @{ username = $Username; password = $Password } | ConvertTo-Json -Compress

    $authResponse = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
        -Method Post `
        -Headers @{"Content-Type"="application/json"} `
        -Body $loginBody `
        -UseBasicParsing

    # Extract access token
    $token = ($authResponse.Content | ConvertFrom-Json).id_token

    if (-not $token) {
        throw "Failed to retrieve access token!"
    }

    Write-Host "Access token retrieved successfully"

} catch {
    Write-Host "ERROR: $_. Running cleanup..."
    aws cognito-idp admin-delete-user --user-pool-id $payload.UserPoolId --username $Username --no-cli-pager 2>$null
    exit 1
}
Write-Host "Raw API Response: $($response.Content)"


# ✅ Step 5: Assign Admin Role via API
# Validate and Format the Token
if (-not $token -or $token -eq "") {
    Write-Host "ERROR: Access token is empty or null."
    exit 1
}

# Debug: Print first 50 chars of token for validation
Write-Host "Retrieved Token (First 50 chars): $($token.Substring(0, [Math]::Min(50, $token.Length)))"

# Ensure Proper Authorization Header Formatting
$headers = @{
    "Authorization" = ("Bearer " + $token).Trim()
    "Content-Type"  = "application/json"
}

$roleAssignmentUrl = "$baseUrl/admin/users/$Username/role"

try {
    Write-Host "Assigning admin role via API..."
    $roleBody = @{ action = "add"; role = $groupName } | ConvertTo-Json -Compress

    $roleResponse = Invoke-WebRequest -Uri $roleAssignmentUrl `
        -Method Put `
        -Headers $headers `
        -Body $roleBody `
        -UseBasicParsing

    if ($roleResponse.StatusCode -ne 200) {
        throw "Failed to assign admin role. Status Code: $($roleResponse.StatusCode)"
    }

    Write-Host "Admin role assigned successfully"

} catch {
    Write-Host "ERROR: $_. Running cleanup..."
    aws cognito-idp admin-delete-user --user-pool-id $payload.UserPoolId --username $Username --no-cli-pager 2>$null
    exit 1
}

Write-Host "Admin user setup complete!"
