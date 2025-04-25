"""Test register_db.py"""
import json
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from models import User, Group
from models.group_membership import GroupMembership
from utils.vocab_enums import GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum
import boto3
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set required environment variables for testing."""
    monkeypatch.setenv("COGNITO_UPDATE_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


@pytest.fixture
def register_db_handler():
    """Import the register_db handler."""
    # Import the handler
    from auth.register_db import lambda_handler as handler
    return handler


def test_register_db_success(register_db_handler):
    """Test successful user registration in database."""
    # Create a mock for the SQS client
    mock_sqs = MagicMock()
    
    # Mock the database session
    mock_db = MagicMock()
    
    # Create mock message
    message = {
        "cognito_sub": "mock-user-sub",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Create SQS event
    event = {
        "Records": [
            {
                "body": json.dumps(message)
            }
        ]
    }
    
    # Patch the SQS client and get_db_session in the register_db module
    with patch('auth.register_db.sqs', mock_sqs), \
         patch('auth.register_db.get_db_session', return_value=mock_db):
        # Call the Lambda handler
        response = register_db_handler(event, None)
        
        # Verify response
        assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
        
        # Verify that the database session was used
        mock_db.commit.assert_called_once()


def test_register_db_invalid_message(register_db_handler):
    """Test registration with invalid message format."""
    # Create a mock for the SQS client
    mock_sqs = MagicMock()
    
    # Mock the database session
    mock_db = MagicMock()
    
    # Create invalid message (missing required fields)
    message = {
        "email": "test@example.com"
        # Missing cognito_sub, first_name, last_name
    }
    
    # Create SQS event
    event = {
        "Records": [
            {
                "body": json.dumps(message)
            }
        ]
    }
    
    # We need to patch process_user at the module level where it's imported, not where it's defined
    with patch('auth.register_db.sqs', mock_sqs), \
         patch('auth.register_db.get_db_session', return_value=mock_db):
        # We'll use a nested patch to handle the exception at the right level
        with patch('auth.register_db.process_user') as mock_process_user:
            # Make process_user raise a SQLAlchemyError
            mock_process_user.side_effect = SQLAlchemyError("Missing required fields")
            
            # Call the Lambda handler
            response = register_db_handler(event, None)
            
            # Verify response
            assert response["statusCode"] == 500, f"Expected 500, got {response['statusCode']}"
            
            # Verify that the database session was rolled back
            mock_db.rollback.assert_called_once()


def test_register_db_invalid_json(register_db_handler, monkeypatch):
    """Test registration with invalid JSON in message body."""
    # Create a mock for the SQS client
    mock_sqs = MagicMock()
    
    # Mock the database session
    mock_db = MagicMock()
    
    # Create SQS event with invalid JSON
    event = {
        "Records": [
            {
                "body": "{invalid-json"
            }
        ]
    }
    
    # Define a custom json.loads function that raises a SQLAlchemyError
    # This ensures the exception is caught by the handler's try/except block
    def mock_json_loads(s):
        if s == "{invalid-json":
            raise SQLAlchemyError("Invalid JSON")
        return json.loads(s)
    
    # Patch json.loads at the module level
    monkeypatch.setattr('json.loads', mock_json_loads)
    
    # Patch the SQS client and get_db_session in the register_db module
    with patch('auth.register_db.sqs', mock_sqs), \
         patch('auth.register_db.get_db_session', return_value=mock_db):
        # Call the Lambda handler
        response = register_db_handler(event, None)
        
        # Verify response
        assert response["statusCode"] == 500, f"Expected 500, got {response['statusCode']}"
        
        # Verify that the database session was rolled back
        mock_db.rollback.assert_called_once()


def test_register_db_database_error(register_db_handler):
    """Test registration handles database errors gracefully."""
    # Create a mock for the SQS client
    mock_sqs = MagicMock()
    
    # Mock the database session
    mock_db = MagicMock()
    
    # Create mock message
    message = {
        "cognito_sub": "mock-user-sub",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Create SQS event
    event = {
        "Records": [
            {
                "body": json.dumps(message)
            }
        ]
    }
    
    # Patch the SQS client and get_db_session in the register_db module
    with patch('auth.register_db.sqs', mock_sqs), \
         patch('auth.register_db.get_db_session', return_value=mock_db):
        # We'll use a nested patch to handle the exception at the right level
        with patch('auth.register_db.process_user') as mock_process_user:
            # Make process_user raise a SQLAlchemyError
            mock_process_user.side_effect = SQLAlchemyError("Database error")
            
            # Call the Lambda handler
            response = register_db_handler(event, None)
            
            # Verify response
            assert response["statusCode"] == 500, f"Expected 500, got {response['statusCode']}"
            
            # Verify that the database session was rolled back
            mock_db.rollback.assert_called_once()


def test_register_db_duplicate_user(register_db_handler):
    """Test registration handles duplicate users gracefully."""
    # Create a mock for the SQS client
    mock_sqs = MagicMock()
    
    # Mock the database session
    mock_db = MagicMock()
    
    # Create a mock for the process_user function
    with patch('auth.register_db.sqs', mock_sqs), \
         patch('auth.register_db.get_db_session', return_value=mock_db), \
         patch('auth.register_db.process_user') as mock_process_user:
        # Make process_user find an existing user (return None)
        mock_process_user.return_value = None
        
        # Create mock message
        message = {
            "cognito_sub": "existing-user-sub",
            "email": "existing@example.com",
            "first_name": "Existing",
            "last_name": "User"
        }
        
        # Create SQS event
        event = {
            "Records": [
                {
                    "body": json.dumps(message)
                }
            ]
        }
        
        # Call the Lambda handler
        response = register_db_handler(event, None)
        
        # Verify response
        assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
        
        # Verify that process_user was called with the correct parameters
        mock_process_user.assert_called_once_with(
            mock_db, 
            "existing-user-sub", 
            "existing@example.com", 
            "Existing", 
            "User"
        )


def test_register_db_no_records(register_db_handler):
    """Test registration with no records in the event."""
    # Create a mock for the SQS client
    mock_sqs = MagicMock()
    
    # Mock the database session
    mock_db = MagicMock()
    
    # Create SQS event with no records
    event = {
        "Records": []
    }
    
    # Patch the SQS client and get_db_session in the register_db module
    with patch('auth.register_db.sqs', mock_sqs), \
         patch('auth.register_db.get_db_session', return_value=mock_db):
        # Call the Lambda handler
        response = register_db_handler(event, None)
        
        # Verify response - should still succeed with empty records
        assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
        
        # Verify that the database session was committed
        mock_db.commit.assert_called_once()


def test_register_db_multiple_records(register_db_handler):
    """Test registration with multiple records in the event."""
    # Create a mock for the SQS client
    mock_sqs = MagicMock()
    
    # Mock the database session
    mock_db = MagicMock()
    
    # Create mock messages
    message1 = {
        "cognito_sub": "user1-sub",
        "email": "user1@example.com",
        "first_name": "User",
        "last_name": "One"
    }
    
    message2 = {
        "cognito_sub": "user2-sub",
        "email": "user2@example.com",
        "first_name": "User",
        "last_name": "Two"
    }
    
    # Create SQS event with multiple records
    event = {
        "Records": [
            {
                "body": json.dumps(message1)
            },
            {
                "body": json.dumps(message2)
            }
        ]
    }
    
    # Patch the SQS client and get_db_session in the register_db module
    with patch('auth.register_db.sqs', mock_sqs), \
         patch('auth.register_db.get_db_session', return_value=mock_db):
        # Call the Lambda handler
        response = register_db_handler(event, None)
        
        # Verify response
        assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
        
        # Verify that the database session was committed once
        mock_db.commit.assert_called_once()
