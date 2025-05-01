# Test-RegistrationAPI.ps1
# Script to test the registration flow via the API

# Get the directory of this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Initialize test results tracking
$global:TestResults = @{
    Passed = @()
    Failed = @()
    Warnings = @()
    TotalSteps = 12
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
        $global:TestResults.Passed += @{
            Step = $StepName
            Message = $Message
        }
        Write-Host "✅ $StepName - $Message" -ForegroundColor Green
    }
    elseif ($Status -eq "Failed") {
        $global:TestResults.Failed += @{
            Step = $StepName
            Message = $Message
        }
        Write-Host "❌ $StepName - $Message" -ForegroundColor Red
    }
    else {
        $global:TestResults.Warnings += @{
            Step = $StepName
            Message = $Message
        }
        Write-Host "⚠️ $StepName - $Message" -ForegroundColor Yellow
    }
    
    $global:TestResults.CompletedSteps++
}

# Function to display test summary
function Show-TestSummary {
    $passCount = $global:TestResults.Passed.Count
    $failCount = $global:TestResults.Failed.Count
    $warnCount = $global:TestResults.Warnings.Count
    
    Write-Host "`n========== TEST SUMMARY ==========" -ForegroundColor Cyan
    Write-Host "Total Steps: $($global:TestResults.TotalSteps)" -ForegroundColor White
    Write-Host "Completed: $($global:TestResults.CompletedSteps)" -ForegroundColor White
    Write-Host "Passed: $passCount" -ForegroundColor Green
    Write-Host "Failed: $failCount" -ForegroundColor Red
    Write-Host "Warnings: $warnCount" -ForegroundColor Yellow
    
    if ($passCount -gt 0) {
        Write-Host "`nPASSED STEPS:" -ForegroundColor Green
        foreach ($result in $global:TestResults.Passed) {
            Write-Host "  ✅ $($result.Step)" -ForegroundColor Green
        }
    }
    
    if ($failCount -gt 0) {
        Write-Host "`nFAILED STEPS:" -ForegroundColor Red
        foreach ($result in $global:TestResults.Failed) {
            Write-Host "  ❌ $($result.Step): $($result.Message)" -ForegroundColor Red
        }
    }
    
    if ($warnCount -gt 0) {
        Write-Host "`nWARNINGS:" -ForegroundColor Yellow
        foreach ($result in $global:TestResults.Warnings) {
            Write-Host "  ⚠️ $($result.Step): $($result.Message)" -ForegroundColor Yellow
        }
    }
    
    # Check if Skipped array exists
    if ($null -ne $global:TestResults.Skipped) {
        $skipCount = $global:TestResults.Skipped.Count
        Write-Host "Skipped: $skipCount" -ForegroundColor Yellow
        
        if ($skipCount -gt 0) {
            Write-Host "`nSKIPPED STEPS:" -ForegroundColor Yellow
            foreach ($result in $global:TestResults.Skipped) {
                Write-Host "  ⚠️ $($result.Step): $($result.Message)" -ForegroundColor Yellow
            }
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
    
    # Set PGPASSWORD environment variable for passwordless connection
    $env:PGPASSWORD = $DbPassword
    
    try {
        Write-Host "Performing comprehensive database cleanup..." -ForegroundColor Yellow
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
        
        # Find test user by email
        if ($TestUserEmail) {
            $getUserQuery = "SELECT id, cognito_sub FROM users WHERE email = '$TestUserEmail';"
            $psqlGetUserCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$getUserQuery`" -t"
            $userResult = Invoke-Expression $psqlGetUserCommand
            
            if ($userResult) {
                # Parse the result (format: " id | cognito_sub ")
                $userResult = $userResult.Trim()
                if ($userResult -match "([a-f0-9-]+)\s*\|\s*([a-f0-9-]+)") {
                    $userId = $matches[1].Trim()
                    $cognitoSub = $matches[2].Trim()
                    
                    Write-Host "Found test user with ID: $userId" -ForegroundColor Green
                    
                    # 1. Delete any items created by this user's claims
                    Write-Host "Deleting items created in claims by this user..." -ForegroundColor Yellow
                    $getClaimsQuery = "SELECT id FROM claims WHERE user_id = '$userId';"
                    $psqlGetClaimsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$getClaimsQuery`" -t"
                    $claimsResult = Invoke-Expression $psqlGetClaimsCommand
                    
                    if ($claimsResult) {
                        $claimIds = $claimsResult -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
                        foreach ($claimId in $claimIds) {
                            # Delete item_files associations
                            $deleteItemFilesQuery = "DELETE FROM item_files WHERE item_id IN (SELECT id FROM items WHERE claim_id = '$claimId');"
                            $psqlDeleteItemFilesCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteItemFilesQuery`""
                            Invoke-Expression $psqlDeleteItemFilesCommand
                            
                            # Delete items
                            $deleteItemsQuery = "DELETE FROM items WHERE claim_id = '$claimId';"
                            $psqlDeleteItemsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteItemsQuery`""
                            Invoke-Expression $psqlDeleteItemsCommand
                            
                            Write-Host "Deleted items for claim ID: $claimId" -ForegroundColor Green
                        }
                    }
                    
                    # 2. Find groups created by this user
                    $getGroupsQuery = "SELECT id FROM groups WHERE created_by = '$userId';"
                    $psqlGetGroupsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$getGroupsQuery`" -t"
                    $groupsResult = Invoke-Expression $psqlGetGroupsCommand
                    
                    if ($groupsResult) {
                        $groupIds = $groupsResult -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
                        
                        foreach ($groupId in $groupIds) {
                            Write-Host "Processing group ID: $groupId" -ForegroundColor Yellow
                            
                            # 3. Delete all files associated with this group
                            Write-Host "Deleting files for group ID: $groupId" -ForegroundColor Yellow
                            $deleteFilesQuery = "DELETE FROM files WHERE group_id = '$groupId';"
                            $psqlDeleteFilesCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteFilesQuery`""
                            Invoke-Expression $psqlDeleteFilesCommand
                            
                            # 4. Delete all claims associated with this group
                            Write-Host "Deleting claims for group ID: $groupId" -ForegroundColor Yellow
                            $deleteClaimsQuery = "DELETE FROM claims WHERE group_id = '$groupId';"
                            $psqlDeleteClaimsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteClaimsQuery`""
                            Invoke-Expression $psqlDeleteClaimsCommand
                            
                            # 5. Delete all items associated with this group
                            Write-Host "Deleting items for group ID: $groupId" -ForegroundColor Yellow
                            $deleteItemsQuery = "DELETE FROM items WHERE group_id = '$groupId';"
                            $psqlDeleteItemsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteItemsQuery`""
                            Invoke-Expression $psqlDeleteItemsCommand
                            
                            # 6. Delete all labels associated with this group
                            Write-Host "Deleting labels for group ID: $groupId" -ForegroundColor Yellow
                            $deleteLabelsQuery = "DELETE FROM labels WHERE group_id = '$groupId';"
                            $psqlDeleteLabelsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteLabelsQuery`""
                            Invoke-Expression $psqlDeleteLabelsCommand
                            
                            # 7. Delete all group memberships for this group
                            Write-Host "Deleting group memberships for group ID: $groupId" -ForegroundColor Yellow
                            $deleteMembershipsQuery = "DELETE FROM group_memberships WHERE group_id = '$groupId';"
                            $psqlDeleteMembershipsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteMembershipsQuery`""
                            Invoke-Expression $psqlDeleteMembershipsCommand
                            
                            # 8. Delete permissions for this group
                            Write-Host "Deleting permissions for group ID: $groupId" -ForegroundColor Yellow
                            $deletePermissionsQuery = "DELETE FROM permissions WHERE group_id = '$groupId';"
                            $psqlDeletePermissionsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deletePermissionsQuery`""
                            Invoke-Expression $psqlDeletePermissionsCommand
                            
                            # 9. Delete the group itself
                            Write-Host "Deleting group with ID: $groupId" -ForegroundColor Yellow
                            $deleteGroupQuery = "DELETE FROM groups WHERE id = '$groupId';"
                            $psqlDeleteGroupCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteGroupQuery`""
                            Invoke-Expression $psqlDeleteGroupCommand
                        }
                    }
                    
                    # 10. Clean up any lingering permissions and group memberships
                    Write-Host "Cleaning up lingering permissions and group memberships..." -ForegroundColor Yellow
                    
                    # Delete permissions for test users
                    $deletePermissionsQuery = "DELETE FROM permissions WHERE user_id IN (SELECT id FROM users WHERE email = '$TestUserEmail');"
                    $psqlDeletePermissionsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deletePermissionsQuery`""
                    Invoke-Expression $psqlDeletePermissionsCommand
                    
                    # Delete group memberships for test users
                    $deleteMembershipsQuery = "DELETE FROM group_memberships WHERE user_id IN (SELECT id FROM users WHERE email = '$TestUserEmail');"
                    $psqlDeleteMembershipsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteMembershipsQuery`""
                    Invoke-Expression $psqlDeleteMembershipsCommand
                    
                    # 11. Clean up any test files that might have been uploaded by other test runs
                    # This is important to avoid conflicts with file hash uniqueness constraints
                    Write-Host "Cleaning up test files from previous test runs..." -ForegroundColor Yellow
                    
                    # Delete files with test image names
                    $testImageNames = @("test_image1.jpg", "test_image2.jpg", "test_image3.jpg", "Spoon.jpg", "dog.jpg", "outlet.jpg")
                    foreach ($imageName in $testImageNames) {
                        $deleteTestFilesQuery = "DELETE FROM files WHERE file_name = '$imageName';"
                        $psqlDeleteTestFilesCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteTestFilesQuery`""
                        Invoke-Expression $psqlDeleteTestFilesCommand
                    }
                    
                    # Delete items with test names
                    $testItemNames = @("Test Item", "Spoon", "Outlet", "Dog")
                    foreach ($itemName in $testItemNames) {
                        $deleteTestItemsQuery = "DELETE FROM items WHERE name = '$itemName';"
                        $psqlDeleteTestItemsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteTestItemsQuery`""
                        Invoke-Expression $psqlDeleteTestItemsCommand
                    }
                    
                    # 12. Delete the user
                    Write-Host "Deleting user with ID: $userId" -ForegroundColor Yellow
                    $deleteUserQuery = "DELETE FROM users WHERE id = '$userId';"
                    $psqlDeleteUserCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteUserQuery`""
                    Invoke-Expression $psqlDeleteUserCommand
                }
            }
        }
        
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

# Function to check file processing status via API
function Test-FileProcessingStatusViaAPI {
    param (
        [string]$ApiBaseUrl,
        [string]$ClaimId,
        [hashtable]$Headers,
        [array]$FileNames
    )
    
    Write-Host "Checking file processing status via API..." -ForegroundColor Yellow
    
    $allFilesProcessed = $false
    $maxAttempts = 12  # Maximum number of attempts (12 * 10 seconds = 120 seconds total)
    $attempt = 0
    
    while (-not $allFilesProcessed -and $attempt -lt $maxAttempts) {
        $attempt++
        $processedCount = 0
        
        # Get all files for the claim
        $getFilesUrl = "$ApiBaseUrl/claims/$ClaimId/files"
        Write-Host "GET $getFilesUrl (Attempt $attempt of $maxAttempts)" -ForegroundColor Gray
        
        try {
            $filesResponse = Invoke-RestMethod -Uri $getFilesUrl -Method Get -Headers $Headers -ErrorAction Stop
            # Check if we have any files in the response
            if ($filesResponse.data.files -and $filesResponse.data.files.Count -gt 0) {
                Write-Host "Found $($filesResponse.data.files.Count) files in API response" -ForegroundColor Green
                
                # Check if all our uploaded files are in the response and processed
                foreach ($fileName in $FileNames) {
                    # Debug the files array
                    Write-Host "Looking for file name: $fileName in response" -ForegroundColor Yellow
                    
                    # Check each file in the response
                    $foundFile = $false
                    foreach ($file in $filesResponse.data.files) {
                        Write-Host "Checking file with name: $($file.file_name)" -ForegroundColor Gray
                        if ($file.file_name -eq $fileName) {
                            Write-Host "File $fileName found in API response with status: $($file.status)" -ForegroundColor Green
                            $processedCount++
                            $foundFile = $true
                            break
                        }
                    }
                    
                    if (-not $foundFile) {
                        Write-Host "File $fileName not found in API response yet" -ForegroundColor Yellow
                    }
                }
            } else {
                Write-Host "No files found in API response yet" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "Error checking files via API:" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
        }
        
        if ($processedCount -eq $FileNames.Count) {
            $allFilesProcessed = $true
            Write-Host "All files found in API response!" -ForegroundColor Green
        } else {
            Write-Host "Waiting for files to appear in API... ($processedCount / $($FileNames.Count) found, attempt $attempt of $maxAttempts)" -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }
    }
    
    # Return both the processing status and the correct file IDs from the API
    $result = @{
        Processed = $allFilesProcessed
        FileIds = @()
    }
    
    # If we found files in the API, collect their IDs
    if ($filesResponse -and $filesResponse.data -and $filesResponse.data.files) {
        foreach ($fileName in $FileNames) {
            foreach ($file in $filesResponse.data.files) {
                if ($file.name -eq $fileName) {
                    $result.FileIds += $file.id
                    break
                }
            }
        }
    }
    
    return $result
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
$DbHost = $Config.DB.Host
$DbUsername = $Config.DB.Username
$DbPassword = $Config.DB.Password
$DbName = $Config.DB.Name

# S3 bucket information
$S3_BUCKET_NAME = "claimvision-files-337214855826-dev"

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
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Cannot connect to database. This is expected if running outside the VPC." -ForegroundColor Yellow
        Write-Host "Skipping database operations." -ForegroundColor Yellow
        exit 1
    }
    
    if ($userId) {
        Write-Host "Type of userId: $($userId.GetType().FullName)" -ForegroundColor Yellow
        Write-Host "User ID: $userId" -ForegroundColor Yellow
        
        # Handle the array type by converting to string and cleaning it
        $userIdString = $userId -join ""
        $userIdString = $userIdString.Trim()
        Write-Host "Cleaned User ID: $userIdString" -ForegroundColor Yellow
        
        Write-Host "User $($TestUser.Email) exists in database with ID: $userIdString, deleting..." -ForegroundColor Yellow
        
        # First, delete any files associated with the user's group
        $getGroupQuery = "SELECT id FROM groups WHERE created_by = '$userIdString';"
        $psqlGetGroupCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$getGroupQuery`" -t"
        $groupId = Invoke-Expression $psqlGetGroupCommand
        
        if ($groupId) {
            # Handle the array type by converting to string and cleaning it
            $groupIdString = $groupId -join ""
            $groupIdString = $groupIdString.Trim()
            Write-Host "Cleaned Group ID: $groupIdString" -ForegroundColor Yellow
            
            Write-Host "Found group ID: $groupIdString" -ForegroundColor Yellow
            
            # Delete files associated with claims
            $deleteFilesQuery = "DELETE FROM files WHERE group_id = '$groupIdString';"
            $psqlDeleteFilesCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteFilesQuery`""
            Invoke-Expression $psqlDeleteFilesCommand
            
            # Delete claims associated with the group
            $deleteClaimsQuery = "DELETE FROM claims WHERE group_id = '$groupIdString';"
            $psqlDeleteClaimsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteClaimsQuery`""
            Invoke-Expression $psqlDeleteClaimsCommand
            
            # Delete labels for this group
            $deleteLabelsQuery = "DELETE FROM labels WHERE group_id = '$groupIdString';"
            $psqlDeleteLabelsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteLabelsQuery`""
            Invoke-Expression $psqlDeleteLabelsCommand
            
            # Delete group memberships for this group
            $deleteMembershipsQuery = "DELETE FROM group_memberships WHERE group_id = '$groupIdString';"
            $psqlDeleteMembershipsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteMembershipsQuery`""
            Invoke-Expression $psqlDeleteMembershipsCommand
            
            # Delete permissions for this group
            $deletePermissionsQuery = "DELETE FROM permissions WHERE group_id = '$groupIdString';"
            $psqlDeletePermissionsCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deletePermissionsQuery`""
            Invoke-Expression $psqlDeletePermissionsCommand
            
            # Delete the group
            $deleteGroupQuery = "DELETE FROM groups WHERE id = '$groupIdString';"
            $psqlDeleteGroupCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteGroupQuery`""
            Invoke-Expression $psqlDeleteGroupCommand
            
            # Delete the user
            $deleteUserQuery = "DELETE FROM users WHERE id = '$userIdString';"
            $psqlDeleteCommand = "psql -h $DbHost -U $DbUsername -d $DbName -c `"$deleteUserQuery`""
            Invoke-Expression $psqlDeleteCommand
            
            Write-Host "Group and associated data deleted" -ForegroundColor Green
        }
        
        Write-Host "User deleted from database" -ForegroundColor Green
    } else {
        Write-Host "User $($TestUser.Email) does not exist in database" -ForegroundColor Green
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
    $global:TestResults.Passed += @{
        Step = "User Registration"
        Message = "User registered successfully"
    }
    
} catch {
    Write-Host "Error registering user via API:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
    $global:TestResults.Failed += @{
        Step = "User Registration"
        Message = $_.Exception.Message
    }
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
    $global:TestResults.Passed += @{
        Step = "User Confirmation"
        Message = "User confirmed in Cognito"
    }
} catch {
    Write-Host "Error confirming user in Cognito:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    $global:TestResults.Failed += @{
        Step = "User Confirmation"
        Message = $_.Exception.Message
    }
    Show-TestSummary
    exit 1
}

# Step 3: Login with the API
Write-Host "`nStep 3: Logging in with API..." -ForegroundColor Blue
$loginUrl = "$apiBaseUrl/auth/login"
Write-Host "POST $loginUrl" -ForegroundColor Gray

$loginBody = @{
    email = $TestUser.Email
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
    
    $global:TestResults.Passed += @{
        Step = "User Login"
        Message = "Login successful, tokens received"
    }
    
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

    # Now create a claim
    $createClaimUrl = "$apiBaseUrl/claims"
    Write-Host "POST $createClaimUrl" -ForegroundColor Gray

    # Set up headers with the access token
    $headers = @{
        "Authorization" = $authHeader
        "Content-Type" = "application/json"
    }

    # Create a claim without specifying group_id - the API will infer it
    $claimBody = @{
        title = "Test Claim $(Get-Date -Format 'yyyyMMdd-HHmmss')"
        description = "This is a test claim created by the automated test script"
        date_of_loss = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
    } | ConvertTo-Json

    try {
        $claimResponse = Invoke-RestMethod -Uri $createClaimUrl -Method Post -Headers $headers -Body $claimBody -ErrorAction Stop
        Write-Host "Create Claim API Response:" -ForegroundColor Green
        Write-Output ($claimResponse | ConvertTo-Json -Depth 10)
        
        # Extract claim ID for future API calls
        $claimId = $claimResponse.data.id
        
        if ($claimId) {
            $global:TestResults.Passed += @{
                Step = "Create Claim"
                Message = "Successfully created claim with ID: $claimId"
            }
            
            # Step 5: Upload files to the claim
            Write-Host "`nStep 5: Uploading files..." -ForegroundColor Blue
                    
            # Get test images from the scripts/images folder
            $imagesDir = Join-Path $ScriptDir "images"
            if (-not (Test-Path $imagesDir)) {
                Write-Host "Images directory not found: $imagesDir" -ForegroundColor Red
                $global:TestResults.Failed += @{
                    Step = "Upload Files"
                    Message = "Images directory not found"
                }
            } else {
                $imageFiles = Get-ChildItem -Path $imagesDir -Filter "*.jpg"
                Write-Host "Found $($imageFiles.Count) test images in $imagesDir" -ForegroundColor Green
            }
                    
            if ($imageFiles -and $imageFiles.Count -gt 0) {
                try {
                    # Step 5.1: Get pre-signed URLs for file uploads
                    $getUploadUrlsUrl = "$apiBaseUrl/claims/$claimId/upload-url"
                    Write-Host "POST $getUploadUrlsUrl" -ForegroundColor Gray
                    
                    # Prepare file info for pre-signed URL request
                    $filesToUpload = @()
                    foreach ($file in $imageFiles) {
                        # Get MIME type based on file extension
                        $contentType = switch ($file.Extension.ToLower()) {
                            ".jpg"  { "image/jpeg" }
                            ".jpeg" { "image/jpeg" }
                            ".png"  { "image/png" }
                            ".gif"  { "image/gif" }
                            ".pdf"  { "application/pdf" }
                            default { "application/octet-stream" }
                        }
                        
                        $filesToUpload += @{
                            name = $file.Name
                            content_type = $contentType
                        }
                    }
                    
                    $uploadUrlsBody = @{
                        files = $filesToUpload
                    } | ConvertTo-Json
                    
                    # Set up headers with the access token
                    #$headers = @{
                    #    "Authorization" = $authHeader
                    #    "Content-Type" = "application/json"
                    #}
                    
                    # Request pre-signed URLs
                    $uploadUrlsResponse = Invoke-RestMethod -Uri $getUploadUrlsUrl -Method Post -Headers $headers -Body $uploadUrlsBody -ErrorAction Stop
                    Write-Host "Get Upload URLs Response:" -ForegroundColor Green
                    Write-Output ($uploadUrlsResponse | ConvertTo-Json -Depth 10)
                    
                    # Step 5.2: Upload files using pre-signed URLs
                    $fileIds = @()
                    $s3Keys = @()
                    
                    foreach ($fileInfo in $uploadUrlsResponse.data.files) {
                        if ($fileInfo.status -eq "ready") {
                            # Find the corresponding file
                            $file = $imageFiles | Where-Object { $_.Name -eq $fileInfo.name } | Select-Object -First 1
                            
                            if ($file) {
                                $uploadUrl = $fileInfo.upload_url
                                Write-Host "Uploading file $($file.Name) to pre-signed URL..." -ForegroundColor Gray
                                
                                try {
                                    # Read file content as bytes
                                    $fileContent = [System.IO.File]::ReadAllBytes($file.FullName)
                                    
                                    # Upload directly to S3 using pre-signed URL
                                    # Note: We use Invoke-WebRequest instead of Invoke-RestMethod for better control
                                    $uploadResponse = Invoke-WebRequest -Uri $uploadUrl -Method PUT -Body $fileContent -ContentType $fileInfo.content_type -ErrorAction Stop
                                    
                                    if ($uploadResponse.StatusCode -eq 200) {
                                        Write-Host "Successfully uploaded file $($file.Name)" -ForegroundColor Green
                                        # Store S3 key for later use
                                        $s3Keys += $fileInfo.s3_key
                                        
                                        # Wait a moment for the S3 event to trigger processing
                                        Start-Sleep -Seconds 2
                                        
                                        # Extract file ID from S3 key
                                        # S3 key format: pending/{claim_id}/{user_id}/{file_id}/{filename}
                                        $s3KeyParts = $fileInfo.s3_key -split '/'
                                        if ($s3KeyParts.Count -ge 4) {
                                            $fileId = $s3KeyParts[3]  # Extract file_id from the path
                                            $fileIds += $fileId
                                            Write-Host "Extracted file ID: $fileId" -ForegroundColor Green
                                        }
                                    }
                                } catch {
                                    Write-Host "Error uploading file to S3:" -ForegroundColor Red
                                    Write-Host $_.Exception.Message -ForegroundColor Red
                                    if ($_.Exception.Response) {
                                        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                                        $reader.BaseStream.Position = 0
                                        $reader.DiscardBufferedData()
                                        $responseBody = $reader.ReadToEnd()
                                        Write-Host "Response body: $responseBody" -ForegroundColor Red
                                    }
                                }
                            }
                        } else {
                            Write-Host "Error getting pre-signed URL for $($fileInfo.name): $($fileInfo.error)" -ForegroundColor Red
                        }
                    }
                    
                    if ($fileIds.Count -gt 0) {
                        $global:TestResults.Passed += @{
                            Step = "Upload Files"
                            Message = "Successfully uploaded $($fileIds.Count) files"
                        }
                        
                        # Wait for files to be processed before proceeding
                        $fileResult = Test-FileProcessingStatusViaAPI -ApiBaseUrl $apiBaseUrl -ClaimId $claimId -Headers $headers -FileNames $imageFiles.Name
                        
                        if (-not $fileResult.Processed) {
                            Write-Host "Warning: Not all files were processed within the timeout period. Proceeding anyway..." -ForegroundColor Yellow
                        }
                        
                        # Get the correct file IDs from the API response
                        $apiFileIds = $fileResult.FileIds
                        Write-Host "Using file IDs from API: $($apiFileIds -join ', ')" -ForegroundColor Green
                        
                        # Step 6: Create items using two different approaches
                        Write-Host "`nStep 6: Creating items..." -ForegroundColor Blue
                        $createItemUrl = "$apiBaseUrl/claims/$claimId/items"
                        
                        # Approach 1: Create an item WITHOUT a file
                        Write-Host "Approach 1: Creating an item without a file..." -ForegroundColor Cyan
                        $itemBody1 = @{
                            name = "Test Item Without File"
                            description = "This is a test item created by the automated test script"
                        } | ConvertTo-Json
                        
                        try {
                            $itemResponse1 = Invoke-RestMethod -Uri $createItemUrl -Method Post -Headers $headers -ContentType "application/json" -Body $itemBody1 -ErrorAction Stop
                            Write-Host "Create Item (No File) API Response:" -ForegroundColor Green
                            Write-Output ($itemResponse1 | ConvertTo-Json -Depth 10)
                            
                            # Extract item ID for future API calls
                            $itemId1 = $itemResponse1.data.id
                            
                            if ($itemId1) {
                                $global:TestResults.Passed += @{
                                    Step = "Create Item (No File)"
                                    Message = "Successfully created item with ID: $itemId1"
                                }
                                
                                # Now add a file to this item
                                if ($apiFileIds.Count -gt 0) {
                                    $addFileUrl = "$apiBaseUrl/items/$itemId1/files"
                                    $addFileBody = @{
                                        file_ids = @($apiFileIds[0])
                                    } | ConvertTo-Json
                                    
                                    try {
                                        $addFileResponse = Invoke-RestMethod -Uri $addFileUrl -Method Post -Headers $headers -ContentType "application/json" -Body $addFileBody -ErrorAction Stop
                                        Write-Host "Add File to Item API Response:" -ForegroundColor Green
                                        Write-Output ($addFileResponse | ConvertTo-Json -Depth 10)
                                        $global:TestResults.Passed += @{
                                            Step = "Add File to Item"
                                            Message = "Successfully added file to item"
                                        }
                                    } catch {
                                        Write-Host "Error adding file to item:" -ForegroundColor Red
                                        Write-Host $_.Exception.Message -ForegroundColor Red
                                        $global:TestResults.Failed += @{
                                            Step = "Add File to Item"
                                            Message = $_.Exception.Message
                                        }
                                    }
                                }
                            } else {
                                $global:TestResults.Failed += @{
                                    Step = "Create Item (No File)"
                                    Message = "Did not receive item ID in response"
                                }
                            }
                        } catch {
                            Write-Host "Error creating item without file:" -ForegroundColor Red
                            Write-Host $_.Exception.Message -ForegroundColor Red
                            $global:TestResults.Failed += @{
                                Step = "Create Item (No File)"
                                Message = $_.Exception.Message
                            }
                        }
                        
                        # Approach 2: Create an item WITH a file
                        if ($apiFileIds.Count -gt 1) {
                            Write-Host "Approach 2: Creating an item with a file..." -ForegroundColor Cyan
                            $itemBody2 = @{
                                name = "Test Item With File"
                                description = "This item was created with a file attachment"
                                file_ids = @($apiFileIds[1])  # Use the second file ID from API
                            } | ConvertTo-Json
                            
                            try {
                                $itemResponse2 = Invoke-RestMethod -Uri $createItemUrl -Method Post -Headers $headers -ContentType "application/json" -Body $itemBody2 -ErrorAction Stop
                                Write-Host "Create Item (With File) API Response:" -ForegroundColor Green
                                Write-Output ($itemResponse2 | ConvertTo-Json -Depth 10)
                                
                                # Extract item ID for future API calls
                                $itemId2 = $itemResponse2.data.id
                                
                                if ($itemId2) {
                                    $global:TestResults.Passed += @{
                                        Step = "Create Item (With File)"
                                        Message = "Successfully created item with ID: $itemId2"
                                    }
                                    
                                    # Now add another file to this item
                                    if ($apiFileIds.Count -gt 2) {
                                        $addFileUrl = "$apiBaseUrl/items/$itemId2/files"
                                        $addFileBody = @{
                                            file_ids = @($apiFileIds[2])  # Use the third file ID from API
                                        } | ConvertTo-Json
                                        
                                        try {
                                            $addFileResponse = Invoke-RestMethod -Uri $addFileUrl -Method Post -Headers $headers -ContentType "application/json" -Body $addFileBody -ErrorAction Stop
                                            Write-Host "Add Second File to Item API Response:" -ForegroundColor Green
                                            Write-Output ($addFileResponse | ConvertTo-Json -Depth 10)
                                            $global:TestResults.Passed += @{
                                                Step = "Add Second File to Item"
                                                Message = "Successfully added second file to item"
                                            }
                                        } catch {
                                            Write-Host "Error adding second file to item:" -ForegroundColor Red
                                            Write-Host $_.Exception.Message -ForegroundColor Red
                                            $global:TestResults.Failed += @{
                                                Step = "Add Second File to Item"
                                                Message = $_.Exception.Message
                                            }
                                        }
                                    }
                                } else {
                                    $global:TestResults.Failed += @{
                                        Step = "Create Item (With File)"
                                        Message = "Did not receive item ID in response"
                                    }
                                }
                            } catch {
                                Write-Host "Error creating item with file:" -ForegroundColor Red
                                Write-Host $_.Exception.Message -ForegroundColor Red
                                $global:TestResults.Failed += @{
                                    Step = "Create Item (With File)"
                                    Message = $_.Exception.Message
                                }
                            }
                        }
                    }
                } catch {
                    Write-Host "Error creating items:" -ForegroundColor Red
                    Write-Host $_.Exception.Message -ForegroundColor Red
                }
            } else {
                $global:TestResults.Failed += @{
                    Step = "Upload Files"
                    Message = "No files were successfully uploaded"
                }
            }
        } else {
            $global:TestResults.Skipped += @{
                Step = "Upload Files"
                Message = "No test images found"
            }
        }
    } catch {
        Write-Host "Error with claim creation:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        $global:TestResults.Failed += @{
            Step = "Claim Creation Process"
            Message = $_.Exception.Message
        }
    }
    
    if (-not $claimId) {
        $global:TestResults.Failed += @{
            Step = "Create Claim"
            Message = "Did not receive claim ID in response"
        }
    }
}

# Add missing catch block for the login try statement
catch {
    Write-Host "Error during login process:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    $global:TestResults.Failed += @{
        Step = "User Login"
        Message = $_.Exception.Message
    }
    exit 1
}

# Step 7: Get item details
Write-Host "`nStep 7: Getting item details..." -ForegroundColor Blue
                
# Try to get details for the first item
if ($itemId1) {
    $getItemUrl = "$apiBaseUrl/items/$itemId1"
    Write-Host "GET $getItemUrl" -ForegroundColor Gray
    
    try {
        $itemDetailsResponse = Invoke-RestMethod -Uri $getItemUrl -Method Get -Headers $headers -ErrorAction Stop
        Write-Host "Get Item API Response:" -ForegroundColor Green
        Write-Output ($itemDetailsResponse | ConvertTo-Json -Depth 10)
        $global:TestResults.Passed += @{
            Step = "Get Item"
            Message = "Successfully retrieved item details"
        }
    } catch {
        Write-Host "Error getting item details:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        $global:TestResults.Failed += @{
            Step = "Get Item"
            Message = $_.Exception.Message
        }
    }
} elseif ($itemId2) {
    # If first item creation failed, try with the second item
    $getItemUrl = "$apiBaseUrl/items/$itemId2"
    Write-Host "GET $getItemUrl" -ForegroundColor Gray
    
    try {
        $itemDetailsResponse = Invoke-RestMethod -Uri $getItemUrl -Method Get -Headers $headers -ErrorAction Stop
        Write-Host "Get Item API Response:" -ForegroundColor Green
        Write-Output ($itemDetailsResponse | ConvertTo-Json -Depth 10)
        $global:TestResults.Passed += @{
            Step = "Get Item"
            Message = "Successfully retrieved item details"
        }
    } catch {
        Write-Host "Error getting item details:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        $global:TestResults.Failed += @{
            Step = "Get Item"
            Message = $_.Exception.Message
        }
    }
} else {
    Write-Host "Skipping item details retrieval - no item IDs available" -ForegroundColor Yellow
    if ($null -eq $global:TestResults.Skipped) {
        $global:TestResults.Skipped = @()
    }
    $global:TestResults.Skipped += @{
        Step = "Get Item"
        Message = "No item IDs available to retrieve"
    }
}

    
# Step 10: Teardown - Clean up items, S3 objects, and files
Write-Host "`nStep 10: Cleaning up resources..." -ForegroundColor Blue

# First, delete any items created during the test
$itemIds = @()
if ($itemId1) { $itemIds += $itemId1 }
if ($itemId2) { $itemIds += $itemId2 }

if ($itemIds.Count -gt 0) {
    Write-Host "Deleting items via API..." -ForegroundColor Yellow
    foreach ($itemId in $itemIds) {
        $deleteItemUrl = "$apiBaseUrl/items/$itemId"
        Write-Host "DELETE $deleteItemUrl" -ForegroundColor Gray
        
        try {
            $deleteItemResponse = Invoke-RestMethod -Uri $deleteItemUrl -Method Delete -Headers $headers -ErrorAction Stop
            Write-Host "Delete Item API Response:" -ForegroundColor Green
            Write-Output ($deleteItemResponse | ConvertTo-Json -Depth 10)
            Write-Host "Successfully deleted item with ID: $itemId" -ForegroundColor Green
        } catch {
            Write-Host "Error deleting item:" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
        }
    }
}

# Next, clean up S3 objects
if ($null -ne $s3Keys -and $s3Keys.Count -gt 0) {
    Write-Host "Cleaning up S3 objects..." -ForegroundColor Yellow
    foreach ($s3Key in $s3Keys) {
        Write-Host "Deleting S3 object: $s3Key" -ForegroundColor Gray
        try {
            # Use AWS CLI to delete the S3 object
            $deleteS3Command = "aws s3 rm s3://$S3_BUCKET_NAME/$s3Key"
            Write-Host "Running: $deleteS3Command" -ForegroundColor Gray
            
            # In PowerShell, we need to handle AWS CLI commands carefully
            $result = Invoke-Expression $deleteS3Command 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Warning: AWS CLI command returned exit code $LASTEXITCODE" -ForegroundColor Yellow
                Write-Host $result -ForegroundColor Yellow
            } else {
                Write-Host "Successfully deleted S3 object: $s3Key" -ForegroundColor Green
            }
        } catch {
            Write-Host "Error deleting S3 object: $s3Key" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
        }
    }
}

# Then, delete file records from the database
foreach ($fileId in $fileIds) {
    $deleteFileUrl = "$apiBaseUrl/files/$fileId"
    Write-Host "DELETE $deleteFileUrl" -ForegroundColor Gray
    
    try {
        $deleteFileResponse = Invoke-RestMethod -Uri $deleteFileUrl -Method Delete -Headers $headers -ErrorAction Stop
        Write-Host "Delete File API Response:" -ForegroundColor Green
        Write-Output ($deleteFileResponse | ConvertTo-Json -Depth 10)
        Write-Host "Successfully deleted file with ID: $fileId" -ForegroundColor Green
    } catch {
        Write-Host "Error deleting file:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}

# Step 11: Delete the claim
Write-Host "`nStep 11: Deleting claim..." -ForegroundColor Blue
# Only attempt to delete the claim if we have a valid claim ID
if ($claimId) {
    $deleteClaimUrl = "$apiBaseUrl/claims/$claimId"
    Write-Host "DELETE $deleteClaimUrl" -ForegroundColor Gray
    
    try {
        $deleteClaimResponse = Invoke-RestMethod -Uri $deleteClaimUrl -Method Delete -Headers $headers -ErrorAction Stop
        Write-Host "Delete Claim API Response:" -ForegroundColor Green
        Write-Output ($deleteClaimResponse | ConvertTo-Json -Depth 10)
        Write-Host "Successfully deleted claim!" -ForegroundColor Green
        $global:TestResults.Passed += @{
            Step = "Delete Claim"
            Message = "Successfully deleted claim"
        }
    } catch {
        Write-Host "Error deleting claim:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        $global:TestResults.Failed += @{
            Step = "Delete Claim"
            Message = $_.Exception.Message
        }
    }
} else {
    Write-Host "Skipping claim deletion - no claim ID available" -ForegroundColor Yellow
    if ($null -eq $global:TestResults.Skipped) {
        $global:TestResults.Skipped = @()
    }
    $global:TestResults.Skipped += @{
        Step = "Delete Claim"
        Message = "No claim ID available to delete"
    }
}

# Display test summary
Show-TestSummary

# Export test results to a file
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$resultsFile = Join-Path $ScriptDir "test_results_$timestamp.json"
$global:TestResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultsFile
Write-Host "Test results saved to: $resultsFile" -ForegroundColor Cyan
