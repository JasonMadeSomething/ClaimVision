# Define path to payload file
$payloadFile = "$PSScriptRoot\..\payloads\files_payload.json"

# Load payload data
$payload = Get-Content -Raw -Path $payloadFile | ConvertFrom-Json

# Extract values from payload
$baseUrl = $payload.base_url
$username = $payload.username
$password = $payload.password
$files = $payload.files  # Array of file objects with paths & names

# Authenticate and retrieve the token
$loginResponse = Invoke-WebRequest -Uri "$baseUrl/auth/login" `
    -Method Post `
    -Headers @{"Content-Type"="application/json"} `
    -Body (@{username=$username; password=$password} | ConvertTo-Json -Compress) `
    -UseBasicParsing

$token = ($loginResponse.Content | ConvertFrom-Json).id_token
Write-Output "✅ Authentication successful!"

# Define headers for API requests
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}

# Function to convert a file to Base64
function Convert-FileToBase64($filePath) {
    return [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($filePath))
}

# List to track uploaded file IDs
$uploadedFileIds = @()

# 1️⃣ Upload a Single File
$singleFile = $files[0]  # First file from payload
$singleFileData = @{
    file_name = $singleFile.name
    file_data = Convert-FileToBase64 -filePath $singleFile.path
} | ConvertTo-Json -Compress -Depth 2

$singleUploadResponse = Invoke-WebRequest -Uri "$baseUrl/files/upload" `
    -Method POST `
    -Headers $headers `
    -Body $singleFileData `
    -UseBasicParsing

$singleFileId = ($singleUploadResponse.Content | ConvertFrom-Json).file_id
$uploadedFileIds += $singleFileId
Write-Output "✅ Single file uploaded: $singleFileId"

# 2️⃣ Upload Multiple Files
foreach ($file in $files[1..($files.Length - 1)]) {
    $fileData = @{
        file_name = $file.name
        file_data = Convert-FileToBase64 -filePath $file.path
    } | ConvertTo-Json -Compress -Depth 2

    $uploadResponse = Invoke-WebRequest -Uri "$baseUrl/files/upload" `
        -Method POST `
        -Headers $headers `
        -Body $fileData `
        -UseBasicParsing

    $fileId = ($uploadResponse.Content | ConvertFrom-Json).file_id
    $uploadedFileIds += $fileId
    Write-Output "✅ File uploaded: $fileId"
}

# 3️⃣ Get All Files
$getAllResponse = Invoke-WebRequest -Uri "$baseUrl/files" `
    -Method GET `
    -Headers $headers `
    -UseBasicParsing

$allFiles = $getAllResponse.Content | ConvertFrom-Json
Write-Output "📂 Retrieved all files: $($allFiles | ConvertTo-Json -Depth 3)"

# 4️⃣ Get a Single File’s Metadata
$getSingleResponse = Invoke-WebRequest -Uri "$baseUrl/files/$singleFileId" `
    -Method GET `
    -Headers $headers `
    -UseBasicParsing

Write-Output "📄 Single file metadata: $($getSingleResponse.Content)"

# 5️⃣ Update a File’s Metadata
$updateFileData = @{
    description = "Updated file description"
} | ConvertTo-Json -Compress

$updateResponse = Invoke-WebRequest -Uri "$baseUrl/files/$singleFileId" `
    -Method PUT `
    -Headers $headers `
    -Body $updateFileData `
    -UseBasicParsing

Write-Output "✏ File metadata updated: $($updateResponse.Content)"

# 6️⃣ Delete Each Uploaded File
foreach ($fileId in $uploadedFileIds) {
    $deleteResponse = Invoke-WebRequest -Uri "$baseUrl/files/$fileId" `
        -Method DELETE `
        -Headers $headers `
        -UseBasicParsing

    Write-Output "🗑 File deleted: $fileId"
}

Write-Output "✅ File CRUD test completed successfully!"
