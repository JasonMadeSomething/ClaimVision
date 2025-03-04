import json
import pytest
from auth.confirm import lambda_handler as confirm_handler
from unittest.mock import patch
from botocore.exceptions import ClientError
@patch("auth.confirm.cognito_client")
def test_confirm_success(mock_cognito):
    """Ensure confirmation succeeds with a valid code."""
    mock_cognito.confirm_sign_up.return_value = {} 

    event = {
        "body": json.dumps({
            "username": "validuser",
            "code": "123456"
        })
    }
    
    response = confirm_handler(event, None)
    body = json.loads(response["body"])
    mock_cognito.confirm_sign_up.assert_called_once()
    print(body)
    assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
    assert "User confirmed successfully" in body["message"]

@patch("auth.confirm.cognito_client")
def test_confirm_invalid_code(mock_cognito):
    """Ensure confirmation fails with an invalid code."""

    mock_cognito.confirm_sign_up.side_effect = ClientError(
        {"Error": {"Code": "CodeMismatchException", "Message": "Invalid confirmation code"}},
        "ConfirmSignUp"
    )  # ✅ Correctly simulate Cognito error

    event = {
        "body": json.dumps({
            "username": "validuser",
            "code": "wrongcode"
        })
    }

    response = confirm_handler(event, None)
    body = json.loads(response["body"])

    print(f"🔍 DEBUG: Cognito response: {response}")  # ✅ Log for debugging
    print(f"🔍 DEBUG: Cognito called? {mock_cognito.confirm_sign_up.called}")  # ✅ Verify mock is called

    assert response["statusCode"] == 400, f"Expected 400, got {response['statusCode']}"
    assert "Invalid confirmation code" in body["error_details"]


@patch("auth.confirm.cognito_client")
def test_confirm_expired_code(mock_cognito):
    """Ensure confirmation fails with an expired code."""

    mock_cognito.confirm_sign_up.side_effect = ClientError(
        {"Error": {"Code": "ExpiredCodeException", "Message": "Confirmation code expired"}},
        "ConfirmSignUp"
    )  # ✅ Correct way to simulate Cognito error

    event = {
        "body": json.dumps({
            "username": "validuser",
            "code": "expiredcode"
        })
    }

    response = confirm_handler(event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400, f"Expected 400, got {response['statusCode']}"





@patch("auth.confirm.cognito_client")
def test_confirm_user_not_found(mock_cognito):
    """Ensure confirmation fails if user does not exist."""

    mock_cognito.confirm_sign_up.side_effect = ClientError(
        {"Error": {"Code": "UserNotFoundException", "Message": "User not found"}},
        "ConfirmSignUp"
    )  # ✅ Correctly simulate Cognito error

    event = {
        "body": json.dumps({
            "username": "nonexistentuser",
            "code": "123456"
        })
    }

    response = confirm_handler(event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404, f"Expected 404, got {response['statusCode']}"
    assert "User not found" in body["message"]

@patch("auth.confirm.cognito_client")
def test_confirm_missing_fields(mock_cognito):
    """Ensure confirmation fails if required fields are missing."""
    event = { "body": json.dumps({}) }
    
    response = confirm_handler(event, None)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 400, f"Expected 400, got {response['statusCode']}"
    assert "missing_fields" in body["data"]

@patch("auth.confirm.cognito_client")
def test_confirm_cognito_unavailable(mock_cognito):
    """Ensure confirmation fails gracefully if Cognito is unavailable."""

    mock_cognito.confirm_sign_up.side_effect = ClientError(
        {"Error": {"Code": "InternalErrorException", "Message": "Cognito service error"}},
        "ConfirmSignUp"
    )  # ✅ Correctly simulate Cognito failure

    event = {
        "body": json.dumps({
            "username": "validuser",
            "code": "123456"
        })
    }

    response = confirm_handler(event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 500, f"Expected 500, got {response['statusCode']}"
    assert "Internal server error" in body["error_details"]

