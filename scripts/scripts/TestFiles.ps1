# Load API details and test files from payload file
$payloadPath = "$PSScriptRoot\..\payloads\file_test.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.base_url
$files = $payload.files
$UserPoolId = $payload.user_pool_id
$Username = $payload.username
$Password =  $payload.password

Write-Host "Creating test user: $Username"

# Step 1: Create user
aws cognito-idp admin-create-user `
    --user-pool-id $UserPoolId `
    --username $Username `
    --user-attributes Name="email",Value="$Username@example.com" Name="email_verified",Value="true" `
    --message-action SUPPRESS > $null

# Step 2: Set password
aws cognito-idp admin-set-user-password `
    --user-pool-id $UserPoolId `
    --username $Username `
    --password $Password `
    --permanent

Write-Host "User $Username created and password set."

# ✅ Step 1: Authenticate User and Retrieve Token
try {
    Write-Host "Authenticating user..."
    $loginResponse = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
        -Method Post `
        -Headers @{"Content-Type"="application/json"} `
        -Body (@{username=$username; password=$password} | ConvertTo-Json -Compress) `
        -UseBasicParsing

    $token = ($loginResponse.Content | ConvertFrom-Json).id_token
    if (-not $token) {
        throw "Failed to retrieve access token!"
    }

    Write-Host "Access token retrieved successfully."
} catch {
    Write-Host "ERROR: $_"
    exit 1
}

# ✅ Step 2: Upload Multiple Files in One Request
try {
    Write-Host "Uploading files..."
    $filePayload = @()

    foreach ($file in $files) {
        $filePath = "$PSScriptRoot\$($file.path)"
        if (-Not (Test-Path $filePath)) {
            Write-Host "WARNING: File not found -> $filePath. Skipping..."
            continue
        }

        $fileData = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($filePath))
        $filePayload += @{ file_name = $file.name; file_data = $fileData }
    }

    $uploadBody = @{ files = $filePayload } | ConvertTo-Json -Depth 3 -Compress
    $uploadHeaders = @{
        "Authorization" = "Bearer $token"
        "Content-Type"  = "application/json"
    }

    $uploadResponse = Invoke-WebRequest -Uri "$baseUrl/files/upload" `
        -Method POST `
        -Headers $uploadHeaders `
        -Body $uploadBody `
        -UseBasicParsing

    $uploadedFiles = ($uploadResponse.Content | ConvertFrom-Json).files
    Write-Host "Files uploaded successfully: $($uploadedFiles | ConvertTo-Json -Depth 3)"

} catch {
    Write-Host "ERROR: $_"
    exit 1
}

# ✅ Step 3: Verify Files Were Uploaded
try {
    Write-Host "Retrieving uploaded files..."
    $getFilesResponse = Invoke-WebRequest -Uri "$baseUrl/files" `
        -Method GET `
        -Headers $uploadHeaders `
        -UseBasicParsing

    $retrievedFiles = ($getFilesResponse.Content | ConvertFrom-Json)
    Write-Host "Retrieved files: $($retrievedFiles | ConvertTo-Json -Depth 3)"

} catch {
    Write-Host "ERROR: $_"
    exit 1
}

# ✅ Step 4: Update Metadata via PATCH
try {
    Write-Host "Updating metadata for uploaded files..."
    foreach ($file in $uploadedFiles) {
        $fileId = $file.file_id
        $metadataUpdate = @{
            description = "Updated description for $($file.file_name)"
            labels = @("updated-label-1", "updated-label-2")
        }

        $response = Invoke-WebRequest -Uri "$baseUrl/files/$fileId" `
            -Method PATCH `
            -Headers $uploadHeaders `
            -Body ($metadataUpdate | ConvertTo-Json -Depth 3 -Compress) `
            -UseBasicParsing

        $updatedFile = ($response.Content | ConvertFrom-Json)
        Write-Host "Metadata for $($updatedFile.file_name) updated successfully."
    }
    Write-Host "Metadata updated successfully."
} catch {
    Write-Host "ERROR: $_"
}

# ✅ Step 5: Replace File via PUT
try {
    Write-Host "Replacing uploaded files..."
    foreach ($file in $uploadedFiles) {
        $fileId = $file.file_id
        $newFilePath = Join-Path -Path $PSScriptRoot -ChildPath $files[0].path

        if (-Not (Test-Path $newFilePath)) {
            Write-Host "WARNING: Replacement file not found -> $newFilePath. Skipping..."
            continue
        }

        $newFileData = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($newFilePath))
        $replacePayload = @{ file_name = $file.file_name; file_data = $newFileData }

        $response = Invoke-WebRequest -Uri "$baseUrl/files/$fileId" `
            -Method PUT `
            -Headers $uploadHeaders `
            -Body ($replacePayload | ConvertTo-Json -Depth 3 -Compress) `
            -UseBasicParsing

        $replacedFile = ($response.Content | ConvertFrom-Json)
        Write-Host "File replaced successfully: $($replacedFile.file_name)"
    }

    Write-Host "Files replaced successfully."
} catch {
    Write-Host "ERROR: $_"
}

# ✅ Step 6: Cleanup - Delete Uploaded Files
try {
    Write-Host "Cleaning up uploaded files..."
    foreach ($file in $uploadedFiles) {
        $fileId = $file.file_id
        Write-Host "Deleting file: $fileId"

        $response = Invoke-WebRequest -Uri "$baseUrl/files/$fileId" `
            -Method DELETE `
            -Headers $uploadHeaders `
            -UseBasicParsing

        $deletedFile = ($response.Content | ConvertFrom-Json)
        Write-Host "File deleted successfully: $($deletedFile.file_name)."
    }

    Write-Host "Cleanup complete. All uploaded files deleted."
} catch {
    Write-Host "ERROR: $_"
} finally {
    aws cognito-idp admin-delete-user --user-pool-id $userpool --username $username
}

Write-Host "File upload test completed successfully."
