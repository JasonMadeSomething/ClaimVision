# Load API details and credentials from payload file
$payloadPath = "$PSScriptRoot\..\payloads\claims_test.json"
$payload = Get-Content -Raw -Path $payloadPath | ConvertFrom-Json

$baseUrl = $payload.BaseUrl
$username = $payload.Username
$password = $payload.Password

Write-Host "🌍 Base API URL: $baseUrl"

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

# Step 2: Define Headers
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}

# Step 3: Create a claim
$claimData = $payload.ClaimData | ConvertTo-Json -Compress
Write-Host "📝 Creating Claim: $claimData"

$createResponse = Invoke-WebRequest -Uri "$baseUrl/claims" `
    -Method Post `
    -Headers $headers `
    -Body $claimData `
    -UseBasicParsing

$createdClaim = $createResponse.Content | ConvertFrom-Json
$claimId = $createdClaim.id

Write-Host "✅ Created Claim ID: $claimId"

# Step 4: Retrieve the created claim
$retrieveResponse = Invoke-WebRequest -Uri "$baseUrl/claims/$claimId" `
    -Method Get `
    -Headers $headers `
    -UseBasicParsing

Write-Host "📥 Retrieved Claim: $($retrieveResponse.Content)"

# Step 5: Update the claim
$updatedClaimData = $payload.UpdatedClaimData | ConvertTo-Json -Compress
Write-Host "✏ Updating Claim: $updatedClaimData"

$updateResponse = Invoke-WebRequest -Uri "$baseUrl/claims/$claimId" `
    -Method Put `
    -Headers $headers `
    -Body $updatedClaimData `
    -UseBasicParsing

Write-Host "✅ Updated Claim: $($updateResponse.Content)"

# Step 6: Delete the claim
Write-Host "🗑 Deleting Claim ID: $claimId"

$deleteResponse = Invoke-WebRequest -Uri "$baseUrl/claims/$claimId" `
    -Method Delete `
    -Headers $headers `
    -UseBasicParsing

Write-Host "✅ Deleted Claim: $($deleteResponse.Content)"

Write-Host "🎉 Claim CRUD cycle completed successfully!"
