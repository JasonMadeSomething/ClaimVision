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
    assert "Invalid username or password" in body["message"], f"Unexpected message: {body['message']}"

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
    assert "User does not exist." in body["message"], f"Unexpected message: {body['message']}"

def test_login_missing_fields(mock_cognito):
    """Ensure login fails if required fields are missing."""
    event = {
        "body": json.dumps({})  # Empty request body
    }
    
    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])
    
    assert login_response["statusCode"] == 400, f"Expected 400, got {login_response['statusCode']}"
    assert "missing_fields" in body["data"], "Expected missing fields error"
    assert "username" in body["data"]["missing_fields"] and "password" in body["data"]["missing_fields"], "Missing fields not detected correctly"

def test_login_unconfirmed_user(mock_cognito):
    """Ensure login fails if the user has not confirmed their email."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.UserNotConfirmedException

    event = {
        "body": json.dumps({
            "username": "unconfirmeduser",
            "password": "ValidPass123!"
        })
    }

    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])

    assert login_response["statusCode"] == 403, f"Expected 403, got {login_response['statusCode']}"
    assert "User is not confirmed" in body["message"], f"Unexpected message: {body['message']}"

def test_login_brute_force_protection(mock_cognito):
    """Ensure login fails if too many failed attempts are made."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.TooManyRequestsException

    event = {
        "body": json.dumps({
            "username": "lockeduser",
            "password": "WrongPass123"
        })
    }

    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])

    assert login_response["statusCode"] == 429, f"Expected 429, got {login_response['statusCode']}"
    assert "Too many failed login attempts" in body["message"], f"Unexpected message: {body['message']}"

def test_login_invalid_json_body(mock_cognito):
    """Ensure login fails if the request body is not valid JSON."""
    event = {
        "body": "{invalid_json: true,"  # Corrupted JSON format
    }

    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])

    assert login_response["statusCode"] == 400, f"Expected 400, got {login_response['statusCode']}"
    assert "Invalid request format" in body["message"], f"Unexpected message: {body['message']}"

def test_login_cognito_unavailable(mock_cognito):
    """Ensure login fails gracefully if Cognito is unavailable."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.InternalErrorException

    event = {
        "body": json.dumps({
            "username": "validuser",
            "password": "CorrectPass123"
        })
    }

    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])

    assert login_response["statusCode"] == 500, f"Expected 500, got {login_response['statusCode']}"
    assert "Cognito is currently unavailable" in body["message"], f"Unexpected message: {body['message']}"

def test_login_expired_password(mock_cognito):
    """Ensure login fails if the user must reset their password."""
    mock_cognito.initiate_auth.side_effect = mock_cognito.exceptions.PasswordResetRequiredException

    event = {
        "body": json.dumps({
            "username": "userneedingreset",
            "password": "OldPass123!"
        })
    }

    login_response = login_handler(event, None)
    body = json.loads(login_response["body"])

    assert login_response["statusCode"] == 403, f"Expected 403, got {login_response['statusCode']}"
    assert "Password reset required" in body["message"], f"Unexpected message: {body['message']}"
