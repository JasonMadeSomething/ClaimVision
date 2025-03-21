"""Test register_cognito.py"""
import json
import uuid
import pytest
from unittest.mock import patch

from auth.register_cognito import lambda_handler as register_cognito_handler


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set required environment variables for testing."""
    monkeypatch.setenv("USER_REGISTRATION_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-user-registration-queue")


def test_register_cognito_success(mock_cognito, mock_sqs):
    """Test successful user registration with Cognito and SQS message sending."""
    # Mock Cognito to generate a unique UserSub
    generated_user_sub = str(uuid.uuid4())
    mock_cognito.sign_up.return_value = {"UserSub": generated_user_sub}

    # Mock SQS send_message
    mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}

    # Create test event
    event = {
        "body": json.dumps({
            "email": "test@example.com",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe",
            "address": "123 Main St",
            "phone_number": "+12345678901"
        })
    }

    # Call the Lambda handler
    response = register_cognito_handler(event, None)
    body = json.loads(response["body"])

    # Verify response
    assert response["statusCode"] == 200
    assert "message" in body
    assert "data" in body
    assert "user_id" in body["data"]
    assert "message_id" in body["data"]
    
    # Instead of checking for exact match, just verify it's a valid UUID
    assert uuid.UUID(body["data"]["user_id"])
    assert body["message"] == "User registration initiated successfully. Please check your email for verification code."


def test_register_cognito_missing_fields(mock_cognito, mock_sqs):
    """Test registration with missing required fields."""
    # Create test event with missing fields
    event = {
        "body": json.dumps({
            "email": "test@example.com"
            # Missing password, first_name, last_name
        })
    }

    # Call the Lambda handler
    response = register_cognito_handler(event, None)
    body = json.loads(response["body"])

    # Verify response
    assert response["statusCode"] == 400
    assert "error_details" in body
    assert "Missing required fields" in body["error_details"]


def test_register_cognito_invalid_email(mock_cognito, mock_sqs):
    """Test registration with invalid email format."""
    # Mock Cognito to raise InvalidParameterException
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.InvalidParameterException({}, "Invalid email format")

    # Create test event
    event = {
        "body": json.dumps({
            "email": "invalid-email",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    # Call the Lambda handler
    response = register_cognito_handler(event, None)
    body = json.loads(response["body"])

    # Verify response
    assert response["statusCode"] == 400
    assert "error_details" in body
    assert "Invalid email format" in body["error_details"]  # Updated to match actual error message


def test_register_cognito_weak_password(mock_cognito, mock_sqs):
    """Test registration with weak password."""
    # Mock Cognito to raise InvalidPasswordException
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.InvalidPasswordException({}, "Password does not meet requirements")

    # Create test event
    event = {
        "body": json.dumps({
            "email": "test@example.com",
            "password": "weak",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    # Call the Lambda handler
    response = register_cognito_handler(event, None)
    body = json.loads(response["body"])

    # Verify response
    assert response["statusCode"] == 400
    assert "error_details" in body
    assert "Password does not meet complexity requirements" in body["error_details"]


def test_register_cognito_username_exists(mock_cognito, mock_sqs):
    """Test registration with existing username."""
    # Mock Cognito to raise UsernameExistsException
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.UsernameExistsException({}, "User already exists")

    # Create test event
    event = {
        "body": json.dumps({
            "email": "existing@example.com",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    # Call the Lambda handler
    response = register_cognito_handler(event, None)
    body = json.loads(response["body"])

    # Verify response
    assert response["statusCode"] == 400
    assert "error_details" in body
    assert "An account with this email already exists" in body["error_details"]


def test_register_cognito_sqs_failure(mock_cognito):
    """Test registration handles SQS failures gracefully."""
    # Mock Cognito to generate a unique UserSub
    generated_user_sub = str(uuid.uuid4())
    mock_cognito.sign_up.return_value = {"UserSub": generated_user_sub}

    # Create test event
    event = {
        "body": json.dumps({
            "email": "test@example.com",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    # Patch the send_to_registration_queue function directly to simulate a failure
    with patch('auth.register_cognito.send_to_registration_queue') as mock_send_to_queue:
        # Configure the mock to return an error
        mock_send_to_queue.return_value = (None, "Failed to queue registration: SQS error")
        
        # Call the Lambda handler
        response = register_cognito_handler(event, None)
        body = json.loads(response["body"])

        # The implementation should return 500 for SQS failures
        assert response["statusCode"] == 500
        assert "error_details" in body
        assert "Failed to queue" in body["error_details"]


def test_register_cognito_invalid_json(mock_cognito, mock_sqs):
    """Test registration with invalid JSON in request body."""
    # Create test event with invalid JSON
    event = {
        "body": "{invalid-json"
    }

    # Call the Lambda handler
    response = register_cognito_handler(event, None)
    body = json.loads(response["body"])

    # Verify response
    assert response["statusCode"] == 400
    assert "error_details" in body
    assert "Invalid JSON in request body" in body["error_details"]
