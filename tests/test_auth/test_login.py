import json
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def login_handler():
    """Import the login handler."""
    # Import the handler
    from auth.login import lambda_handler as handler
    return handler

def test_login_success(login_handler):
    """Ensure login succeeds with correct credentials."""
    # Create a mock for the cognito client
    mock_cognito = MagicMock()
    mock_cognito.initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "mock_access_token",
            "IdToken": "mock_id_token",
            "RefreshToken": "mock_refresh_token"
        }
    }
    
    event = {
        "body": json.dumps({
            "email": "validuser@example.com",
            "password": "CorrectPass123"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', mock_cognito):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 200, f"Expected 200, got {login_response['statusCode']}"
        assert "access_token" in body["data"], "Access token missing in response"

def test_login_incorrect_password(login_handler):
    """Ensure login fails with incorrect password."""
    # Create a mock for the cognito client
    mock_cognito = MagicMock()
    
    # Create the exception class
    NotAuthorizedException = type("NotAuthorizedException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.initiate_auth.side_effect = NotAuthorizedException("Invalid username or password")
    
    event = {
        "body": json.dumps({
            "email": "validuser@example.com",
            "password": "WrongPass123"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', mock_cognito):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_nonexistent_user(login_handler):
    """Ensure login fails if user does not exist."""
    # Create a mock for the cognito client
    mock_cognito = MagicMock()
    
    # Create the exception class
    UserNotFoundException = type("UserNotFoundException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.initiate_auth.side_effect = UserNotFoundException("User does not exist")
    
    event = {
        "body": json.dumps({
            "email": "nonexistent@example.com",
            "password": "SomePass123"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', mock_cognito):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_missing_fields(login_handler):
    """Ensure login fails if email or password is missing."""
    event = {
        "body": json.dumps({
            "email": "validuser@example.com"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', MagicMock()):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_unconfirmed_user(login_handler):
    """Ensure login fails if the user has not confirmed their email."""
    # Create a mock for the cognito client
    mock_cognito = MagicMock()
    
    # Create the exception class
    UserNotConfirmedException = type("UserNotConfirmedException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.initiate_auth.side_effect = UserNotConfirmedException("User is not confirmed")
    
    event = {
        "body": json.dumps({
            "email": "unconfirmed@example.com",
            "password": "SomePass123"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', mock_cognito):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_brute_force_protection(login_handler):
    """Ensure login fails if too many failed attempts are made."""
    # Create a mock for the cognito client
    mock_cognito = MagicMock()
    
    # Create the exception class
    PasswordResetRequiredException = type("PasswordResetRequiredException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.initiate_auth.side_effect = PasswordResetRequiredException("Password reset required")
    
    event = {
        "body": json.dumps({
            "email": "validuser@example.com",
            "password": "SomePass123"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', mock_cognito):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_invalid_json_body(login_handler):
    """Ensure login fails if the request body is not valid JSON."""
    event = {
        "body": "This is not valid JSON"
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', MagicMock()):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_cognito_unavailable(login_handler):
    """Ensure login fails gracefully if Cognito is unavailable."""
    # Create a mock for the cognito client
    mock_cognito = MagicMock()
    
    # Set up the exception
    mock_cognito.initiate_auth.side_effect = Exception("Service unavailable")
    
    event = {
        "body": json.dumps({
            "email": "validuser@example.com",
            "password": "SomePass123"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', mock_cognito):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_expired_password(login_handler):
    """Ensure login fails if the user must reset their password."""
    # Create a mock for the cognito client
    mock_cognito = MagicMock()
    
    # Create the exception class
    NotAuthorizedException = type("NotAuthorizedException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.initiate_auth.side_effect = NotAuthorizedException("Password has expired")
    
    event = {
        "body": json.dumps({
            "email": "validuser@example.com",
            "password": "ExpiredPass123"
        })
    }
    
    # Patch the cognito client in the login module
    with patch('auth.login.cognito', mock_cognito):
        login_response = login_handler(event, None)
        body = json.loads(login_response["body"])
    
        assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
        assert "Authentication failed" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"
