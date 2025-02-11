# Load user details from payload file
$payloadPath = "$PSScriptRoot\..\payloads\admin_user.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$UserPoolId = $payload.UserPoolId
$Username = $payload.Username
$Password = $payload.Password
$Email = $payload.Email
$GroupName = $payload.GroupName

# Step 1: Create the user
aws cognito-idp admin-create-user --user-pool-id $UserPoolId --username $Username `
    --user-attributes Name="email",Value="$Email" Name="email_verified",Value="true" `
    --message-action SUPPRESS

# Step 2: Set a password and confirm the user
aws cognito-idp admin-set-user-password --user-pool-id $UserPoolId --username $Username `
    --password $Password --permanent

# Step 3: Add user to the "admin" group
aws cognito-idp admin-add-user-to-group --user-pool-id $UserPoolId --username $Username `
    --group-name $GroupName

Write-Host "✅ Admin user '$Username' created, confirmed, and assigned to the '$GroupName' group."
