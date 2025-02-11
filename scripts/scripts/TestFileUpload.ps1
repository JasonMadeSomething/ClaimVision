# Load API details and credentials from payload file
$payloadPath = "$PSScriptRoot\..\payloads\file_upload_test.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.BaseUrl
$username = $payload.Username
$password = $payload.Password
$filePath = $payload.FilePath
$fileName = $payload.FileName

Write-Host "🌍 Base API URL: $baseUrl"
Write-Host "📂 Uploading File: $fileName from $filePath"

# Step 1: Authenticate and retrieve token
$response = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
    -Method Post `
    -Headers @{"Content-Type"="application/json"} `
    -Body (ConvertTo-Json -Compress -Depth 2 @{username = $username; password = $password}) `
    -UseBasicParsing

$token = ($response.Content | ConvertFrom-Json).id_token

# Debug: Ensure token is retrieved
if (-not $token) {
    Write-Host "❌ ERROR: Access token is null or empty!"
    exit 1
}

Write-Host "🔑 Retrieved Access Token"

# Step 2: Read file and encode in base64
if (-Not (Test-Path $filePath)) {
    Write-Host "❌ ERROR: File '$filePath' not found!"
    exit 1
}

$fileContent = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($filePath))

# Step 3: Prepare JSON Payload
$body = @{
    file_name = $fileName
    file_data = $fileContent
} | ConvertTo-Json -Compress -Depth 2

# Step 4: Define Headers
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}

# Step 5: Invoke API to Upload File
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/files/upload" `
        -Method POST `
        -Headers $headers `
        -Body $body `
        -UseBasicParsing

    Write-Host "✅ Upload Successful! Response: $($response.Content)"
} catch {
    Write-Host "❌ Upload Failed: $($_.Exception.Message)"
}
