"""Test register_cognito.py"""
import json
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set required environment variables for testing."""
    monkeypatch.setenv("USER_REGISTRATION_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue")
    monkeypatch.setenv("COGNITO_USER_POOL_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_testpool")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

@pytest.fixture
def register_handler():
    """Import the register handler."""
    # Import the handler
    from auth.register_cognito import lambda_handler as handler
    return handler


def test_register_cognito_success(register_handler):
    """Test successful user registration with Cognito and SQS message sending."""
    # Create mocks for the cognito and sqs clients
    mock_cognito = MagicMock()
    mock_sqs = MagicMock()
    
    # Set up the return values
    mock_cognito.sign_up.return_value = {
        "UserSub": "mock-user-sub"
    }
    
    # Mock the admin_get_user call
    mock_cognito.admin_get_user.return_value = {
        "UserAttributes": [
            {"Name": "sub", "Value": "mock-user-sub"}
        ]
    }
    
    mock_sqs.send_message.return_value = {
        "MessageId": "mock-message-id"
    }
    
    event = {
        "body": json.dumps({
            "email": "newuser@example.com",
            "password": "ValidPass123",
            "first_name": "New",
            "last_name": "User"
        })
    }
    
    # Patch both clients in the register_cognito module
    with patch('auth.register_cognito.cognito', mock_cognito), \
         patch('auth.register_cognito.sqs', mock_sqs):
        register_response = register_handler(event, None)
        body = json.loads(register_response["body"])
        
        assert register_response["statusCode"] == 200, f"Expected 200, got {register_response['statusCode']}"
        assert "message" in body, f"Missing message in body: {body}"
        
        # Verify the cognito client was called with the correct parameters
        mock_cognito.sign_up.assert_called_once()
        call_args = mock_cognito.sign_up.call_args[1]
        assert call_args["Username"] == "newuser@example.com"
        assert call_args["Password"] == "ValidPass123"
        
        # Verify admin_get_user was called
        mock_cognito.admin_get_user.assert_called_once()
        
        # Verify the SQS client was called with the correct parameters
        mock_sqs.send_message.assert_called_once()
        sqs_call_args = mock_sqs.send_message.call_args[1]
        assert "QueueUrl" in sqs_call_args
        
        # Verify the message body contains the expected data
        message_body = json.loads(sqs_call_args["MessageBody"])
        assert message_body["cognito_sub"] == "mock-user-sub"
        assert message_body["email"] == "newuser@example.com"
        assert message_body["first_name"] == "New"
        assert message_body["last_name"] == "User"


def test_register_cognito_missing_fields(register_handler):
    """Test registration with missing required fields."""
    # Create mocks for the cognito and sqs clients
    mock_cognito = MagicMock()
    mock_sqs = MagicMock()
    
    event = {
        "body": json.dumps({
            "email": "test@example.com"
            # Missing password, first_name, last_name
        })
    }
    
    # Patch both clients in the register_cognito module
    with patch('auth.register_cognito.cognito', mock_cognito), \
         patch('auth.register_cognito.sqs', mock_sqs):
        register_response = register_handler(event, None)
        body = json.loads(register_response["body"])
        
        assert register_response["statusCode"] == 500, f"Expected 500, got {register_response['statusCode']}"
        assert "error" in body


def test_register_cognito_invalid_email(register_handler):
    """Test registration with invalid email format."""
    # Create mocks for the cognito and sqs clients
    mock_cognito = MagicMock()
    mock_sqs = MagicMock()
    
    # Create the exception class
    InvalidParameterException = type("InvalidParameterException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.sign_up.side_effect = InvalidParameterException("Invalid email format")
    
    event = {
        "body": json.dumps({
            "email": "invalid-email",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe"
        })
    }
    
    # Patch both clients in the register_cognito module
    with patch('auth.register_cognito.cognito', mock_cognito), \
         patch('auth.register_cognito.sqs', mock_sqs):
        register_response = register_handler(event, None)
        body = json.loads(register_response["body"])
        
        assert register_response["statusCode"] == 500, f"Expected 500, got {register_response['statusCode']}"
        assert "error" in body


def test_register_cognito_weak_password(register_handler):
    """Test registration with weak password."""
    # Create mocks for the cognito and sqs clients
    mock_cognito = MagicMock()
    mock_sqs = MagicMock()
    
    # Create the exception class
    InvalidPasswordException = type("InvalidPasswordException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.sign_up.side_effect = InvalidPasswordException("Password does not meet requirements")
    
    event = {
        "body": json.dumps({
            "email": "test@example.com",
            "password": "weak",
            "first_name": "John",
            "last_name": "Doe"
        })
    }
    
    # Patch both clients in the register_cognito module
    with patch('auth.register_cognito.cognito', mock_cognito), \
         patch('auth.register_cognito.sqs', mock_sqs):
        register_response = register_handler(event, None)
        body = json.loads(register_response["body"])
        
        assert register_response["statusCode"] == 500, f"Expected 500, got {register_response['statusCode']}"
        assert "error" in body


def test_register_cognito_username_exists(register_handler):
    """Test registration with existing username."""
    # Create mocks for the cognito and sqs clients
    mock_cognito = MagicMock()
    mock_sqs = MagicMock()
    
    # Create the exception class
    UsernameExistsException = type("UsernameExistsException", (Exception,), {})
    
    # Set up the exception
    mock_cognito.sign_up.side_effect = UsernameExistsException("User already exists")
    
    event = {
        "body": json.dumps({
            "email": "existing@example.com",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe"
        })
    }
    
    # Patch both clients in the register_cognito module
    with patch('auth.register_cognito.cognito', mock_cognito), \
         patch('auth.register_cognito.sqs', mock_sqs):
        register_response = register_handler(event, None)
        body = json.loads(register_response["body"])
        
        assert register_response["statusCode"] == 500, f"Expected 500, got {register_response['statusCode']}"
        assert "error" in body


def test_register_cognito_sqs_failure(register_handler):
    """Test registration handles SQS failures gracefully."""
    # Create mocks for the cognito and sqs clients
    mock_cognito = MagicMock()
    mock_sqs = MagicMock()
    
    # Set up the return value for cognito
    mock_cognito.sign_up.return_value = {
        "UserSub": "mock-user-sub"
    }
    
    # Set up the exception for SQS
    mock_sqs.send_message.side_effect = Exception("SQS unavailable")
    
    event = {
        "body": json.dumps({
            "email": "test@example.com",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe"
        })
    }
    
    # Patch both clients in the register_cognito module
    with patch('auth.register_cognito.cognito', mock_cognito), \
         patch('auth.register_cognito.sqs', mock_sqs):
        register_response = register_handler(event, None)
        body = json.loads(register_response["body"])
        
        assert register_response["statusCode"] == 500, f"Expected 500, got {register_response['statusCode']}"
        assert "error" in body


def test_register_cognito_invalid_json(register_handler):
    """Test registration with invalid JSON in request body."""
    # Create mocks for the cognito and sqs clients
    mock_cognito = MagicMock()
    mock_sqs = MagicMock()
    
    event = {
        "body": "{invalid-json"
    }
    
    # Patch both clients in the register_cognito module
    with patch('auth.register_cognito.cognito', mock_cognito), \
         patch('auth.register_cognito.sqs', mock_sqs):
        register_response = register_handler(event, None)
        body = json.loads(register_response["body"])
        
        assert register_response["statusCode"] == 500, f"Expected 500, got {register_response['statusCode']}"
        assert "error" in body
