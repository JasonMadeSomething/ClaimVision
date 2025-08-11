# WebSocket Testing Script for ClaimVision
# This script helps test WebSocket connections using wscat

param (
    [string]$ApiUrl = "wss://ws.dev.claimvision.made-something.com",
    [string]$Token = "",
    [string]$Username = "",
    [System.Security.SecureString]$Password,
    [string]$ClientId = "",
    [switch]$Help
)

# Show help if requested
if ($Help) {
    Write-Host "ClaimVision WebSocket Test Script"
    Write-Host "--------------------------------"
    Write-Host "Usage: .\test_websocket.ps1 [-ApiUrl <WebSocket API URL>] [-Username <email>] [-Password <password>] [-ClientId <app client id>] [-Token <Cognito ID Token>]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -ApiUrl    : The WebSocket API URL (default: wss://ws.dev.claimvision.made-something.com)"
    Write-Host "  -Username  : Your Cognito username (email)"
    Write-Host "  -Password  : Your Cognito password (will be securely handled)"
    Write-Host "  -ClientId  : The Cognito app client ID"
    Write-Host "  -Token     : A valid Cognito ID token for authentication (if you already have one)"
    Write-Host "  -Help      : Show this help message"
    Write-Host ""
    Write-Host "Note: You can either provide a token directly using -Token or login with -Username/-Password/-ClientId"
    exit 0
}

# Check if wscat is installed
try {
    $wscatVersion = npx wscat --version
    Write-Host "Found wscat: $wscatVersion"
} catch {
    Write-Host "wscat not found. Installing wscat..."
    npm install -g wscat
}

# Validate parameters
if ([string]::IsNullOrEmpty($ApiUrl)) {
    Write-Host "Error: WebSocket API URL is required. Use -ApiUrl parameter." -ForegroundColor Red
    exit 1
}

# If no token is provided, try to login
if ([string]::IsNullOrEmpty($Token)) {
    # Check if we have credentials to login
    if ([string]::IsNullOrEmpty($Username) -or $null -eq $Password -or [string]::IsNullOrEmpty($ClientId)) {
        Write-Host "Error: Either provide a token with -Token or login credentials with -Username, -Password, and -ClientId" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "No token provided. Attempting to login with provided credentials..." -ForegroundColor Yellow
    
    # Install AWS CLI if not already installed
    try {
        $awsVersion = aws --version
        Write-Host "Found AWS CLI: $awsVersion"
    } catch {
        Write-Host "AWS CLI not found. Please install AWS CLI to use the login functionality." -ForegroundColor Red
        Write-Host "Visit: https://aws.amazon.com/cli/" -ForegroundColor Cyan
        exit 1
    }
    
    # Login using Cognito's InitiateAuth API
    try {
        # Convert SecureString to plain text for the API call (only in memory, not stored)
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        $authParams = @{
            "USERNAME" = $Username
            "PASSWORD" = $PlainPassword
        }
        
        # Clear the plain text password from memory as soon as possible
        $PlainPassword = $null
        [System.GC]::Collect()
        
        $authParamsJson = $authParams | ConvertTo-Json -Compress
        
        Write-Host "Authenticating with Cognito..." -ForegroundColor Yellow
        $authResult = aws cognito-idp initiate-auth `
            --auth-flow USER_PASSWORD_AUTH `
            --client-id $ClientId `
            --auth-parameters $authParamsJson `
            --query "AuthenticationResult" | ConvertFrom-Json
        
        if ($null -eq $authResult) {
            Write-Host "Authentication failed. Check your credentials and try again." -ForegroundColor Red
            exit 1
        }
        
        # Extract the ID token
        $Token = $authResult.IdToken
        
        if ([string]::IsNullOrEmpty($Token)) {
            Write-Host "Failed to get ID token from authentication response." -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Successfully authenticated with Cognito!" -ForegroundColor Green
    } catch {
        Write-Host "Error during authentication: $_" -ForegroundColor Red
        exit 1
    }
}

# Construct the WebSocket URL with the token
$fullUrl = "$ApiUrl/?token=$Token"

Write-Host "Connecting to: $ApiUrl" -ForegroundColor Green
Write-Host "Using Cognito token: $($Token.Substring(0, 20))..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Starting wscat connection. Press Ctrl+C to exit." -ForegroundColor Cyan
Write-Host "You can type JSON messages to send to the WebSocket server." -ForegroundColor Cyan
Write-Host "Example: { ""action"": ""ping"" }" -ForegroundColor Cyan

# Connect to the WebSocket server using wscat
Write-Host "Running: npx wscat -c ""$fullUrl""" -ForegroundColor DarkGray
npx wscat -c "$fullUrl" | Tee-Object -FilePath "websocket_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

Write-Host "WebSocket connection closed." -ForegroundColor Green
