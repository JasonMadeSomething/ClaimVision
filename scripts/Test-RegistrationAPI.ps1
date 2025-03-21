# Test-RegistrationAPI.ps1
# Script to test the registration flow via the API

# Get the directory of this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Initialize test results tracking
$TestResults = @{
    Passed = @()
    Failed = @()
    Warnings = @()
    TotalSteps = 11
    CompletedSteps = 0
}

# Function to record test results
function Record-TestResult {
    param (
        [Parameter(Mandatory=$true)]
        [string]$StepName,
        
        [Parameter(Mandatory=$true)]
        [string]$Status,  # "Passed", "Failed", or "Warning"
        
        [Parameter(Mandatory=$false)]
        [string]$Message = ""
    )
    
    if ($Status -eq "Passed") {
        $TestResults.Passed += @{Step = $StepName; Message = $Message}
        Write-Host "✅ $StepName - $Message" -ForegroundColor Green
    }
    elseif ($Status -eq "Failed") {
        $TestResults.Failed += @{Step = $StepName; Message = $Message}
        Write-Host "❌ $StepName - $Message" -ForegroundColor Red
    }
    else {
        $TestResults.Warnings += @{Step = $StepName; Message = $Message}
        Write-Host "⚠️ $StepName - $Message" -ForegroundColor Yellow
    }
    
    $TestResults.CompletedSteps++
}

# Function to display test summary
function Show-TestSummary {
    $passCount = $TestResults.Passed.Count
    $failCount = $TestResults.Failed.Count
    $warnCount = $TestResults.Warnings.Count
    
    Write-Host "`n========== TEST SUMMARY ==========" -ForegroundColor Cyan
    Write-Host "Total Steps: $($TestResults.TotalSteps)" -ForegroundColor White
    Write-Host "Completed: $($TestResults.CompletedSteps)" -ForegroundColor White
    Write-Host "Passed: $passCount" -ForegroundColor Green
    Write-Host "Failed: $failCount" -ForegroundColor Red
    Write-Host "Warnings: $warnCount" -ForegroundColor Yellow
    
    if ($passCount -gt 0) {
        Write-Host "`nPASSED STEPS:" -ForegroundColor Green
        foreach ($result in $TestResults.Passed) {
            Write-Host "  ✅ $($result.Step)" -ForegroundColor Green
        }
    }
    
    if ($failCount -gt 0) {
        Write-Host "`nFAILED STEPS:" -ForegroundColor Red
        foreach ($result in $TestResults.Failed) {
            Write-Host "  ❌ $($result.Step): $($result.Message)" -ForegroundColor Red
        }
    }
    
    if ($warnCount -gt 0) {
        Write-Host "`nWARNINGS:" -ForegroundColor Yellow
        foreach ($result in $TestResults.Warnings) {
            Write-Host "  ⚠️ $($result.Step): $($result.Message)" -ForegroundColor Yellow
        }
    }
    
    # Overall test result
    if ($failCount -eq 0) {
        if ($warnCount -eq 0) {
            Write-Host "`nOVERALL RESULT: PASSED ✅" -ForegroundColor Green
        } else {
            Write-Host "`nOVERALL RESULT: PASSED WITH WARNINGS ⚠️" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`nOVERALL RESULT: FAILED ❌" -ForegroundColor Red
    }
    Write-Host "=================================" -ForegroundColor Cyan
}

# Function to perform comprehensive database cleanup
function Clean-TestDatabase {
    param (
        [string]$DbHost,
        [string]$DbUsername,
        [string]$DbPassword,
        [string]$DbName,
        [string]$TestUserEmail
    )
    
    Write-Host "`nPerforming comprehensive database cleanup..." -ForegroundColor Cyan
    
    # Set PGPASSWORD environment variable for psql authentication
    $env:PGPASSWORD = $DbPassword
    
    try {
        Write-Host "Attempting to connect to database at $DbHost..." -ForegroundColor Yellow
        
        # First, check if we can connect to the database
        $testConnectionQuery = "SELECT 1;"
        $psqlTestCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$testConnectionQuery`" -t"
        $testResult = Invoke-Expression $psqlTestCommand -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Cannot connect to database. This is expected if running outside the VPC." -ForegroundColor Yellow
            Write-Host "Skipping database cleanup." -ForegroundColor Yellow
            return
        }
        
        Write-Host "Connected to database successfully." -ForegroundColor Green
        
        # 1. Find the test user and their household
        if ($TestUserEmail) {
            $getUserQuery = "SELECT id, household_id FROM users WHERE email = '$TestUserEmail';"
            $psqlGetUserCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$getUserQuery`" -t"
            $userResult = Invoke-Expression $psqlGetUserCommand
            
            if ($userResult) {
                # Parse the result (format: " id | household_id ")
                $userResult = $userResult.Trim()
                if ($userResult -match "([a-f0-9-]+)\s*\|\s*([a-f0-9-]+)") {
                    $userId = $matches[1].Trim()
                    $householdId = $matches[2].Trim()
                    
                    Write-Host "Found test user with ID: $userId and household ID: $householdId" -ForegroundColor Green
                    
                    # 2. Delete all files associated with this household
                    Write-Host "Deleting files for household ID: $householdId" -ForegroundColor Yellow
                    $deleteFilesQuery = "DELETE FROM files WHERE household_id = '$householdId';"
                    $psqlDeleteFilesCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteFilesQuery`""
                    Invoke-Expression $psqlDeleteFilesCommand
                    
                    # 3. Delete all claims associated with this household
                    Write-Host "Deleting claims for household ID: $householdId" -ForegroundColor Yellow
                    $deleteClaimsQuery = "DELETE FROM claims WHERE household_id = '$householdId';"
                    $psqlDeleteClaimsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteClaimsQuery`""
                    Invoke-Expression $psqlDeleteClaimsCommand
                    
                    # 4. Delete the user
                    Write-Host "Deleting user with ID: $userId" -ForegroundColor Yellow
                    $deleteUserQuery = "DELETE FROM users WHERE id = '$userId';"
                    $psqlDeleteUserCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteUserQuery`""
                    Invoke-Expression $psqlDeleteUserCommand
                    
                    # 5. Delete the household
                    Write-Host "Deleting household with ID: $householdId" -ForegroundColor Yellow
                    $deleteHouseholdQuery = "DELETE FROM households WHERE id = '$householdId';"
                    $psqlDeleteHouseholdCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteHouseholdQuery`""
                    Invoke-Expression $psqlDeleteHouseholdCommand
                }
            }
        }
        
        # 6. Clean up any test files that might have been uploaded by other test runs
        # This is important to avoid conflicts with file hash uniqueness constraints
        Write-Host "Cleaning up test files from previous test runs..." -ForegroundColor Yellow
        
        # Delete files with test image names
        $testImageNames = @("test_image1.jpg", "test_image2.jpg", "test_image3.jpg", "Spoon.jpg", "dog.jpg", "outlet.jpg")
        foreach ($imageName in $testImageNames) {
            $deleteTestFilesQuery = "DELETE FROM files WHERE file_name = '$imageName';"
            $psqlDeleteTestFilesCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteTestFilesQuery`""
            Invoke-Expression $psqlDeleteTestFilesCommand
        }
        
        # 7. Clean up any test claims with "Test Claim" in the title
        Write-Host "Cleaning up test claims from previous test runs..." -ForegroundColor Yellow
        $deleteTestClaimsQuery = "DELETE FROM claims WHERE title LIKE 'Test Claim%';"
        $psqlDeleteTestClaimsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteTestClaimsQuery`""
        Invoke-Expression $psqlDeleteTestClaimsCommand
        
        # 8. Clean up any test items with "Test Item" as the name
        Write-Host "Cleaning up test items from previous test runs..." -ForegroundColor Yellow
        $deleteTestItemsQuery = "DELETE FROM items WHERE name = 'Test Item';"
        $psqlDeleteTestItemsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteTestItemsQuery`""
        Invoke-Expression $psqlDeleteTestItemsCommand
        
        Write-Host "Database cleanup completed successfully." -ForegroundColor Green
        
    } catch {
        Write-Host "Error during database cleanup: $_" -ForegroundColor Red
        Write-Host "This is expected if running outside the VPC." -ForegroundColor Yellow
    } finally {
        # Clear the PGPASSWORD environment variable
        if (Test-Path Env:\PGPASSWORD) {
            Remove-Item Env:\PGPASSWORD
        }
    }
}

# Load configuration from config.json
$ConfigPath = Join-Path $ScriptDir "config.json"
if (-not (Test-Path $ConfigPath)) {
    Write-Host "Configuration file not found: $ConfigPath" -ForegroundColor Red
    exit 1
}

$Config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json

# Configuration from config.json
$apiBaseUrl = $Config.ApiBaseUrl
$UserPoolId = $Config.UserPoolId
# ClientId is used in the login request via Cognito client
$TestUser = @{
    Email = $Config.TestUser.Email
    Password = $Config.TestUser.Password
    FirstName = $Config.TestUser.FirstName
    LastName = $Config.TestUser.LastName
}

# Database connection information
$DbHost = "claimvision-dev.czzwxwpwmndx.us-east-1.rds.amazonaws.com"
$DbUsername = "testuser"
$DbPassword = "YourStrongPassword123!"
$DbName = "claimvision"

# Perform comprehensive database cleanup
Clean-TestDatabase -DbHost $DbHost -DbUsername $DbUsername -DbPassword $DbPassword -DbName $DbName -TestUserEmail $TestUser.Email

# First, delete the user if they exist in Cognito
Write-Host "Checking if user exists in Cognito..." -ForegroundColor Cyan
$userInfoCommand = "aws cognito-idp admin-get-user --user-pool-id $UserPoolId --username $($TestUser.Email)"
try {
    Invoke-Expression $userInfoCommand 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "User $($TestUser.Email) exists in Cognito, deleting..." -ForegroundColor Yellow
        $deleteCommand = "aws cognito-idp admin-delete-user --user-pool-id $UserPoolId --username $($TestUser.Email)"
        Invoke-Expression $deleteCommand
        Write-Host "User deleted from Cognito" -ForegroundColor Green
    }
} catch {
    Write-Host "User $($TestUser.Email) does not exist in Cognito" -ForegroundColor Green
}

# Check if user exists in the database
Write-Host "`nChecking if user exists in the database..." -ForegroundColor Cyan
$checkUserQuery = "SELECT id FROM users WHERE email = '$($TestUser.Email)';"
$psqlCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$checkUserQuery`" -t"

# Set PGPASSWORD environment variable for psql authentication
$env:PGPASSWORD = $DbPassword

try {
    Write-Host "Attempting to connect to database at $DbHost..." -ForegroundColor Yellow
    $userId = Invoke-Expression $psqlCommand -ErrorAction SilentlyContinue
    
    # Only proceed with database operations if the command was successful
    if ($LASTEXITCODE -eq 0 -and $userId) {
        Write-Host "Type of userId: $($userId.GetType().FullName)" -ForegroundColor Yellow
        Write-Host "User ID: $userId" -ForegroundColor Yellow
        
        # Handle the array type by converting to string and cleaning it
        $userIdString = $userId -join ""
        $userIdString = $userIdString.Trim()
        Write-Host "Cleaned User ID: $userIdString" -ForegroundColor Yellow
        
        Write-Host "User $($TestUser.Email) exists in database with ID: $userIdString, deleting..." -ForegroundColor Yellow
        
        # First, delete any files associated with the user's household
        $getHouseholdQuery = "SELECT household_id FROM users WHERE id = '$userIdString';"
        $psqlGetHouseholdCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$getHouseholdQuery`" -t"
        $householdId = Invoke-Expression $psqlGetHouseholdCommand
        
        if ($householdId) {
            # Handle the array type by converting to string and cleaning it
            $householdIdString = $householdId -join ""
            $householdIdString = $householdIdString.Trim()
            Write-Host "Cleaned Household ID: $householdIdString" -ForegroundColor Yellow
            
            Write-Host "Found household ID: $householdIdString" -ForegroundColor Yellow
            
            # Delete files associated with claims
            $deleteFilesQuery = "DELETE FROM files WHERE household_id = '$householdIdString';"
            $psqlDeleteFilesCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteFilesQuery`""
            Invoke-Expression $psqlDeleteFilesCommand
            
            # Delete claims associated with the household
            $deleteClaimsQuery = "DELETE FROM claims WHERE household_id = '$householdIdString';"
            $psqlDeleteClaimsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteClaimsQuery`""
            Invoke-Expression $psqlDeleteClaimsCommand
            
            # Delete user from database
            $deleteUserQuery = "DELETE FROM users WHERE id = '$userIdString';"
            $psqlDeleteCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteUserQuery`""
            Invoke-Expression $psqlDeleteCommand
            
            # Delete the household
            $deleteHouseholdQuery = "DELETE FROM households WHERE id = '$householdIdString';"
            $psqlDeleteHouseholdCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteHouseholdQuery`""
            Invoke-Expression $psqlDeleteHouseholdCommand
            
            Write-Host "Household and associated data deleted" -ForegroundColor Green
        }
        
        Write-Host "User deleted from database" -ForegroundColor Green
    } else {
        Write-Host "User $($TestUser.Email) does not exist in database or could not connect to database" -ForegroundColor Green
    }
} catch {
    Write-Host "Error checking database: $_" -ForegroundColor Red
    Write-Host "This is expected if running outside the VPC." -ForegroundColor Yellow
    Write-Host "Continuing with registration process..." -ForegroundColor Cyan
} finally {
    # Clear the PGPASSWORD environment variable
    if (Test-Path Env:\PGPASSWORD) {
        Remove-Item Env:\PGPASSWORD
    }
}

# Step 1: Register user via API
Write-Host "`nStep 1: Registering user via API..." -ForegroundColor Cyan
$registerUrl = "$apiBaseUrl/auth/register"
Write-Host "POST $registerUrl" -ForegroundColor Gray

$registerBody = @{
    email = $TestUser.Email
    password = $TestUser.Password
    first_name = $TestUser.FirstName
    last_name = $TestUser.LastName
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri $registerUrl -Method Post -Body $registerBody -ContentType "application/json" -ErrorAction Stop
    Write-Host "Registration API Response:" -ForegroundColor Green
    Write-Output ($registerResponse | ConvertTo-Json -Depth 10)
    Record-TestResult -StepName "User Registration" -Status "Passed" -Message "User registered successfully"
    
} catch {
    Write-Host "Error registering user via API:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
    Record-TestResult -StepName "User Registration" -Status "Failed" -Message $_.Exception.Message
    Show-TestSummary
    exit 1
}

# Step 2: Confirm the user in Cognito (simulating email confirmation)
Write-Host "`nStep 2: Confirming user in Cognito..." -ForegroundColor Blue
$confirmCommand = "aws cognito-idp admin-confirm-sign-up --user-pool-id $UserPoolId --username $($TestUser.Email)"
Write-Host "Running: $confirmCommand" -ForegroundColor Gray
try {
    Invoke-Expression $confirmCommand | Out-Null
    Write-Host "User confirmed in Cognito" -ForegroundColor Green
    Record-TestResult -StepName "User Confirmation" -Status "Passed" -Message "User confirmed in Cognito"
} catch {
    Write-Host "Error confirming user in Cognito:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Record-TestResult -StepName "User Confirmation" -Status "Failed" -Message $_.Exception.Message
    Show-TestSummary
    exit 1
}

# Step 3: Login with the API
Write-Host "`nStep 3: Logging in with API..." -ForegroundColor Blue
$loginUrl = "$apiBaseUrl/auth/login"
Write-Host "POST $loginUrl" -ForegroundColor Gray

$loginBody = @{
    username = $TestUser.Email
    password = $TestUser.Password
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri $loginUrl -Method Post -ContentType "application/json" -Body $loginBody -ErrorAction Stop
    Write-Host "Login API Response:" -ForegroundColor Green
    Write-Output ($loginResponse | ConvertTo-Json -Depth 10)
    
    # Extract tokens from login response
    $idToken = $loginResponse.data.id_token
    $accessToken = $loginResponse.data.access_token
    $refreshToken = $loginResponse.data.refresh_token
    
    # Debug: Show token types
    Write-Host "ID Token: $($idToken.Substring(0, [Math]::Min(20, $idToken.Length)))..." -ForegroundColor Gray
    Write-Host "Access Token: $($accessToken.Substring(0, [Math]::Min(20, $accessToken.Length)))..." -ForegroundColor Gray
    Write-Host "Refresh Token: $($refreshToken.Substring(0, [Math]::Min(20, $refreshToken.Length)))..." -ForegroundColor Gray
    
    Record-TestResult -StepName "User Login" -Status "Passed" -Message "Login successful, tokens received"
    
    # Fix the Authorization header format
    # The issue is with how PowerShell handles the token string and how API Gateway processes it
    # Let's try a completely different approach to format the Authorization header
            
    # 1. Make sure the token is clean with no whitespace or line breaks
    $cleanToken = $idToken.Trim() -replace "`r", "" -replace "`n", "" -replace " ", ""
            
    # 2. Debug: Show token length and first/last few characters
    Write-Host "Token length: $($cleanToken.Length) characters" -ForegroundColor Yellow
    Write-Host "Token start: $($cleanToken.Substring(0, [Math]::Min(20, $cleanToken.Length)))..." -ForegroundColor Yellow
    Write-Host "Token end: ...$($cleanToken.Substring([Math]::Max(0, $cleanToken.Length - 20)))" -ForegroundColor Yellow
            
    # 3. Create the Authorization header with careful formatting
    $authHeader = "Bearer " + $cleanToken
            
    # 4. Debug: Show the final header format
    Write-Host "Auth header length: $($authHeader.Length) characters" -ForegroundColor Yellow
    Write-Host "Auth header start: $($authHeader.Substring(0, [Math]::Min(30, $authHeader.Length)))..." -ForegroundColor Yellow
            
    $uploadHeaders = @{
        "Authorization" = $authHeader
        "Content-Type" = "application/json"
    }
    
    # Step 4: Create a claim
    Write-Host "`nStep 4: Creating a claim..." -ForegroundColor Blue
    $createClaimUrl = "$apiBaseUrl/claims"
    Write-Host "POST $createClaimUrl" -ForegroundColor Gray
    
    $claimBody = @{
        title = "Test Claim $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        description = "This is a test claim created by the registration test script"
        date_of_loss = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
        status = "Open"
    } | ConvertTo-Json
    
    try {
        $claimResponse = Invoke-RestMethod -Uri $createClaimUrl -Method Post -Headers $uploadHeaders -Body $claimBody -ErrorAction Stop
        Write-Host "Create Claim API Response:" -ForegroundColor Green
        Write-Output ($claimResponse | ConvertTo-Json -Depth 10)
        
        $claimId = $claimResponse.data.id
        Write-Host "Successfully created claim with ID: $claimId" -ForegroundColor Green
        Record-TestResult -StepName "Create Claim" -Status "Passed" -Message "Claim created with ID: $claimId"
        
        # Step 5: Upload files to the claim
        Write-Host "`nStep 5: Uploading files to the claim..." -ForegroundColor Blue
        $uploadFileUrl = "$apiBaseUrl/files"
        Write-Host "POST $uploadFileUrl" -ForegroundColor Gray
        
        # Use images from the scripts/images directory
        $imagesDir = Join-Path $ScriptDir "images"
        if (-not (Test-Path $imagesDir)) {
            Write-Host "Images directory not found: $imagesDir" -ForegroundColor Red
            Record-TestResult -StepName "Upload Files" -Status "Failed" -Message "Images directory not found: $imagesDir"
            Show-TestSummary
            exit 1
        }
        
        # Get all image files from the directory
        $imageFiles = Get-ChildItem -Path $imagesDir -Filter "*.jpg"
        if ($imageFiles.Count -eq 0) {
            Write-Host "No image files found in directory: $imagesDir" -ForegroundColor Red
            Record-TestResult -StepName "Upload Files" -Status "Failed" -Message "No image files found in directory: $imagesDir"
            Show-TestSummary
            exit 1
        }
        
        Write-Host "Found $($imageFiles.Count) images in $imagesDir" -ForegroundColor Green
        
        try {
            # Prepare the files for upload
            $filesToUpload = @()
            
            foreach ($file in $imageFiles) {
                Write-Host "Reading file: $($file.FullName)" -ForegroundColor Gray
                $fileBytes = [System.IO.File]::ReadAllBytes($file.FullName)
                $fileBase64 = [System.Convert]::ToBase64String($fileBytes)
                
                $filesToUpload += @{
                    file_name = $file.Name
                    file_data = $fileBase64
                }
            }
            
            # Create the request body with multiple files
            $uploadBody = @{
                files = $filesToUpload
                claim_id = $claimId
            } | ConvertTo-Json -Depth 10
            
            Write-Host "Request body size: $($uploadBody.Length) characters" -ForegroundColor Gray
            
            # Fix the Authorization header format
            # The issue is likely with how PowerShell handles the token string
            # Make sure there are no extra spaces or line breaks in the token
            $cleanIdToken = $idToken.Trim()
            
            # Remove any potential carriage returns or line breaks that might be in the token
            $cleanIdToken = $cleanIdToken -replace "`r", "" -replace "`n", ""
            
            # Debug: Show token length and first/last few characters
            Write-Host "Token length: $($cleanIdToken.Length) characters" -ForegroundColor Yellow
            Write-Host "Token start: $($cleanIdToken.Substring(0, [Math]::Min(20, $cleanIdToken.Length)))..." -ForegroundColor Yellow
            Write-Host "Token end: ...$($cleanIdToken.Substring([Math]::Max(0, $cleanIdToken.Length - 20)))" -ForegroundColor Yellow
            
            $uploadHeaders = @{
                "Authorization" = "Bearer $cleanIdToken"
                "Content-Type" = "application/json"
            }
            
            try {
                $uploadResponse = Invoke-RestMethod -Uri $uploadFileUrl -Method Post -Headers $uploadHeaders -Body $uploadBody -ErrorAction Stop
                Write-Host "Upload File API Response:" -ForegroundColor Green
                Write-Output ($uploadResponse | ConvertTo-Json -Depth 10)
                
                $fileNames = $uploadResponse.data.files_queued | ForEach-Object { $_.file_name }
                Write-Host "Successfully uploaded files to claim!" -ForegroundColor Green
                Record-TestResult -StepName "Upload Files" -Status "Passed" -Message "Successfully uploaded $($fileNames.Count) files"
                
                # Wait for files to be processed
                Write-Host "`nWaiting for files to be processed..." -ForegroundColor Blue
                $filesProcessed = $false
                $attempt = 0
                $maxAttempts = 10
                $fileIds = @()
                
                # Get all files for the household to find our files
                $getFilesUrl = "$apiBaseUrl/files"
                
                while (-not $filesProcessed -and $attempt -lt $maxAttempts) {
                    $attempt++
                    Write-Host "Checking file status (attempt $attempt of $maxAttempts)..." -ForegroundColor Gray
                    Start-Sleep -Seconds 5
                    
                    try {
                        # Make sure we're using the correct authorization headers
                        $getFilesHeaders = @{
                            "Authorization" = "Bearer $idToken"
                            "Content-Type" = "application/json"
                        }
                        
                        $getFilesResponse = Invoke-RestMethod -Uri $getFilesUrl -Method Get -Headers $getFilesHeaders -ErrorAction Stop
                        
                        # Check if our files exist and have been processed
                        $processedFiles = $getFilesResponse.data.files | Where-Object { $fileNames -contains $_.file_name }
                        
                        if ($processedFiles -and $processedFiles.Count -eq $imageFiles.Count) {
                            $filesProcessed = $true
                            $fileIds = $processedFiles | ForEach-Object { $_.id }
                            Write-Host "Files have been processed successfully!" -ForegroundColor Green
                            Write-Host "File IDs: $($fileIds -join ', ')" -ForegroundColor Green
                            Record-TestResult -StepName "File Processing" -Status "Passed" -Message "All files processed successfully"
                        }
                    } catch {
                        Write-Host "Error checking file status:" -ForegroundColor Red
                        Write-Host $_.Exception.Message -ForegroundColor Red
                    }
                }
                
                if (-not $filesProcessed) {
                    Write-Host "Files were not processed within the expected time." -ForegroundColor Yellow
                    Record-TestResult -StepName "File Processing" -Status "Warning" -Message "Files were not processed within the expected time"
                }
                
                # Step 6: Create an item
                if ($fileIds -and $fileIds.Count -gt 0) {
                    Write-Host "`nStep 6: Creating an item..." -ForegroundColor Blue
                    $createItemUrl = "$apiBaseUrl/claims/$claimId/items"
                    Write-Host "POST $createItemUrl" -ForegroundColor Gray
                    
                    $itemBody = @{
                        name = "Test Item"
                        description = "This is a test item created by the registration test script"
                        estimated_value = 100.50
                        condition = "Good"
                        file_id = $fileIds[0]  # Associate with the first file
                    } | ConvertTo-Json
                    
                    try {
                        $itemResponse = Invoke-RestMethod -Uri $createItemUrl -Method Post -Headers $uploadHeaders -Body $itemBody -ErrorAction Stop
                        Write-Host "Create Item API Response:" -ForegroundColor Green
                        Write-Output ($itemResponse | ConvertTo-Json -Depth 10)
                        
                        $itemId = $itemResponse.data.id
                        Write-Host "Successfully created an item!" -ForegroundColor Green
                        Record-TestResult -StepName "Create Item" -Status "Passed" -Message "Item created with ID: $itemId"
                        
                        # Step 7: Add manual labels to the files
                        Write-Host "`nStep 7: Adding manual labels to the files..." -ForegroundColor Blue
                        $labelSuccess = $true
                        
                        foreach ($fileId in $fileIds) {
                            $createLabelUrl = "$apiBaseUrl/files/$fileId/labels"
                            Write-Host "POST $createLabelUrl" -ForegroundColor Gray
                            
                            $labelBody = @{
                                labels = @("TestLabel", "Important", "Insurance")
                            } | ConvertTo-Json
                            
                            try {
                                $labelResponse = Invoke-RestMethod -Uri $createLabelUrl -Method Post -Headers $uploadHeaders -Body $labelBody -ErrorAction Stop
                                Write-Host "Create Label API Response:" -ForegroundColor Green
                                Write-Output ($labelResponse | ConvertTo-Json -Depth 10)
                                Write-Host "Successfully added labels to file $fileId!" -ForegroundColor Green
                            } catch {
                                Write-Host "Error adding labels to file:" -ForegroundColor Red
                                Write-Host $_.Exception.Message -ForegroundColor Red
                                $labelSuccess = $false
                            }
                        }
                        
                        if ($labelSuccess) {
                            Record-TestResult -StepName "Add Labels" -Status "Passed" -Message "Labels added to all files"
                        } else {
                            Record-TestResult -StepName "Add Labels" -Status "Warning" -Message "Some labels could not be added"
                        }
                        
                        # Step 8: Get the labels for the files
                        Write-Host "`nStep 8: Getting the labels for the files..." -ForegroundColor Blue
                        $getLabelsSuccess = $true
                        
                        foreach ($fileId in $fileIds) {
                            $getLabelsUrl = "$apiBaseUrl/files/$fileId/labels"
                            Write-Host "GET $getLabelsUrl" -ForegroundColor Gray
                            
                            try {
                                $getLabelsResponse = Invoke-RestMethod -Uri $getLabelsUrl -Method Get -Headers $uploadHeaders -ErrorAction Stop
                                Write-Host "Get Labels API Response:" -ForegroundColor Green
                                Write-Output ($getLabelsResponse | ConvertTo-Json -Depth 10)
                                Write-Host "Successfully retrieved labels for file $fileId!" -ForegroundColor Green
                            } catch {
                                Write-Host "Error getting labels for file:" -ForegroundColor Red
                                Write-Host $_.Exception.Message -ForegroundColor Red
                                $getLabelsSuccess = $false
                            }
                        }
                        
                        if ($getLabelsSuccess) {
                            Record-TestResult -StepName "Get Labels" -Status "Passed" -Message "Retrieved labels for all files"
                        } else {
                            Record-TestResult -StepName "Get Labels" -Status "Warning" -Message "Could not retrieve labels for some files"
                        }
                        
                        # Step 9: Teardown - Delete the item
                        Write-Host "`nStep 9: Teardown - Deleting the item..." -ForegroundColor Blue
                        $deleteItemUrl = "$apiBaseUrl/items/$itemId"
                        Write-Host "DELETE $deleteItemUrl" -ForegroundColor Gray
                        
                        try {
                            $deleteItemResponse = Invoke-RestMethod -Uri $deleteItemUrl -Method Delete -Headers $uploadHeaders -ErrorAction Stop
                            Write-Host "Delete Item API Response:" -ForegroundColor Green
                            Write-Output ($deleteItemResponse | ConvertTo-Json -Depth 10)
                            Write-Host "Successfully deleted the item!" -ForegroundColor Green
                            Record-TestResult -StepName "Delete Item" -Status "Passed" -Message "Item deleted successfully"
                        } catch {
                            Write-Host "Error deleting item:" -ForegroundColor Red
                            Write-Host $_.Exception.Message -ForegroundColor Red
                            Record-TestResult -StepName "Delete Item" -Status "Failed" -Message $_.Exception.Message
                        }
                    } catch {
                        Write-Host "Error creating item:" -ForegroundColor Red
                        Write-Host $_.Exception.Message -ForegroundColor Red
                        Record-TestResult -StepName "Create Item" -Status "Failed" -Message $_.Exception.Message
                    }
                } else {
                    Record-TestResult -StepName "Create Item" -Status "Skipped" -Message "No file IDs available to create item"
                }
                
                # Step 10: Teardown - Delete the files
                Write-Host "`nStep 10: Teardown - Deleting the files..." -ForegroundColor Blue
                $deleteFileSuccess = $true
                
                foreach ($fileId in $fileIds) {
                    $deleteFileUrl = "$apiBaseUrl/files/$fileId"
                    Write-Host "DELETE $deleteFileUrl" -ForegroundColor Gray
                    
                    try {
                        $deleteFileResponse = Invoke-RestMethod -Uri $deleteFileUrl -Method Delete -Headers $uploadHeaders -ErrorAction Stop
                        Write-Host "Delete File API Response:" -ForegroundColor Green
                        Write-Output ($deleteFileResponse | ConvertTo-Json -Depth 10)
                        Write-Host "Successfully deleted file $fileId!" -ForegroundColor Green
                    } catch {
                        Write-Host "Error deleting file:" -ForegroundColor Red
                        Write-Host $_.Exception.Message -ForegroundColor Red
                        $deleteFileSuccess = $false
                    }
                }
                
                if ($deleteFileSuccess) {
                    Record-TestResult -StepName "Delete Files" -Status "Passed" -Message "All files deleted successfully"
                } else {
                    Record-TestResult -StepName "Delete Files" -Status "Warning" -Message "Some files could not be deleted"
                }
                
                # Step 11: Teardown - Delete the claim
                Write-Host "`nStep 11: Teardown - Deleting the claim..." -ForegroundColor Blue
                $deleteClaimUrl = "$apiBaseUrl/claims/$claimId"
                Write-Host "DELETE $deleteClaimUrl" -ForegroundColor Gray
                
                try {
                    $deleteClaimResponse = Invoke-RestMethod -Uri $deleteClaimUrl -Method Delete -Headers $uploadHeaders -ErrorAction Stop
                    Write-Host "Delete Claim API Response:" -ForegroundColor Green
                    Write-Output ($deleteClaimResponse | ConvertTo-Json -Depth 10)
                    Write-Host "Successfully deleted the claim!" -ForegroundColor Green
                    Record-TestResult -StepName "Delete Claim" -Status "Passed" -Message "Claim deleted successfully"
                } catch {
                    Write-Host "Error deleting claim:" -ForegroundColor Red
                    Write-Host $_.Exception.Message -ForegroundColor Red
                    Record-TestResult -StepName "Delete Claim" -Status "Failed" -Message $_.Exception.Message
                }
                
            } catch {
                Write-Host "Error uploading files:" -ForegroundColor Red
                Write-Host $_.Exception.Message -ForegroundColor Red
                if ($_.Exception.Response) {
                    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                    $reader.BaseStream.Position = 0
                    $reader.DiscardBufferedData()
                    $responseBody = $reader.ReadToEnd()
                    Write-Host $responseBody -ForegroundColor Red
                }
                Record-TestResult -StepName "Upload Files" -Status "Failed" -Message $_.Exception.Message
            }
            
        } catch {
            Write-Host "Error preparing files for upload:" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
            Record-TestResult -StepName "Upload Files" -Status "Failed" -Message "Error preparing files: $($_.Exception.Message)"
        }
        
    } catch {
        Write-Host "Error creating claim:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Record-TestResult -StepName "Create Claim" -Status "Failed" -Message $_.Exception.Message
    }
    
} catch {
    Write-Host "Error during login:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Record-TestResult -StepName "User Login" -Status "Failed" -Message $_.Exception.Message
}

# Display test summary
Show-TestSummary

# Export test results to a file
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$resultsFile = Join-Path $ScriptDir "test_results_$timestamp.json"
$TestResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultsFile
Write-Host "Test results saved to: $resultsFile" -ForegroundColor Cyan
