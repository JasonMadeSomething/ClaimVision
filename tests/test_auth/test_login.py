import json
import boto3
import pytest
from auth.login import lambda_handler as login_handler
from utils import response

def test_login_success(mock_cognito):
    """Ensure login succeeds with correct credentials."""
    mock_cognito.initiate_auth.return_value = {
        "AuthenticationResult": {
            "AccessToken": "mock_access_token",
            "IdToken": "mock_id_token",
            "RefreshToken": "mock_refresh_token"
        }
    }
    
    event = {
        "body": json.dumps({
            "username": "validuser",
            "password": "CorrectPass123"
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 200, f"Expected 200, got {login_response['statusCode']}"
    assert "access_token" in body["data"], "Access token missing in response"

def test_login_incorrect_password(mock_cognito):
    """Ensure login fails with incorrect password."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.NotAuthorizedException
    
    event = {
        "body": json.dumps({
            "username": "validuser",
            "password": "WrongPass123"
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
    assert "Invalid username or password" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_nonexistent_user(mock_cognito):
    """Ensure login fails if user does not exist."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.UserNotFoundException
    
    event = {
        "body": json.dumps({
            "username": "nonexistentuser",
            "password": "SomePass123"
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 404, f"Expected 404, got {login_response['statusCode']}"
    assert "User does not exist" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_missing_fields(mock_cognito):
    """Ensure login fails if required fields are missing."""
    event = {
        "body": json.dumps({
            "username": ""  # Missing password
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 400, f"Expected 400, got {login_response['statusCode']}"
    assert "missing_fields" in body.get("data", {}), "Missing fields not reported in response"

def test_login_unconfirmed_user(mock_cognito):
    """Ensure login fails if the user has not confirmed their email."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.UserNotConfirmedException
    
    event = {
        "body": json.dumps({
            "username": "unconfirmeduser",
            "password": "SomePass123"
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 403, f"Expected 403, got {login_response['statusCode']}"
    assert "not confirmed" in body["error_details"].lower(), f"Unexpected error details: {body.get('error_details')}"

def test_login_brute_force_protection(mock_cognito):
    """Ensure login fails if too many failed attempts are made."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.PasswordResetRequiredException
    
    event = {
        "body": json.dumps({
            "username": "validuser",
            "password": "SomePass123"
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 403, f"Expected 403, got {login_response['statusCode']}"
    assert "reset" in body["error_details"].lower(), f"Unexpected error details: {body.get('error_details')}"

def test_login_invalid_json_body(mock_cognito):
    """Ensure login fails if the request body is not valid JSON."""
    event = {
        "body": "{invalid json"
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 400, f"Expected 400, got {login_response['statusCode']}"
    assert "Invalid" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_cognito_unavailable(mock_cognito):
    """Ensure login fails gracefully if Cognito is unavailable."""
    mock_cognito.initiate_auth.side_effect = Exception("Service unavailable")
    
    event = {
        "body": json.dumps({
            "username": "validuser",
            "password": "SomePass123"
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 500, f"Expected 500, got {login_response['statusCode']}"
    assert "Service unavailable" in body["error_details"], f"Unexpected error details: {body.get('error_details')}"

def test_login_expired_password(mock_cognito):
    """Ensure login fails if the user must reset their password."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.NotAuthorizedException("Password has expired")
    
    event = {
        "body": json.dumps({
            "username": "validuser",
            "password": "ExpiredPass123"
        })
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 401, f"Expected 401, got {login_response['statusCode']}"
    assert "password" in body["error_details"].lower(), f"Unexpected error details: {body.get('error_details')}"
