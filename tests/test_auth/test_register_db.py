"""Test register_db.py"""
import json
import uuid
import pytest
from auth.register_db import lambda_handler as register_db_handler
from models import User, Household


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set required environment variables for testing."""
    monkeypatch.setenv("COGNITO_UPDATE_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-cognito-update-queue")


def test_register_db_success(test_db, mock_sqs, mocker):
    """Test successful user registration in database and sending message to Cognito update queue."""
    # Mock database session
    mocker.patch("auth.register_db.get_db_session", return_value=test_db)
    
    # Mock SQS send_message
    mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}
    
    # Create a unique user_id for testing
    user_id = str(uuid.uuid4())
    
    # Create SQS event with a single record
    event = {
        "Records": [
            {
                "messageId": "message1",
                "body": json.dumps({
                    "email": "test@example.com",
                    "password": "StrongPass!123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "address": "123 Main St",
                    "phone_number": "+12345678901",
                    "user_id": user_id
                })
            }
        ]
    }
    
    # Call the Lambda handler
    response = register_db_handler(event, None)
    body = json.loads(response["body"])
    
    # Verify response
    assert response["statusCode"] == 200
    assert "message" in body
    assert "Successfully processed" in body["message"]
    
    # Verify user was created in database
    user = test_db.query(User).filter(User.id == user_id).first()
    assert user is not None
    assert user.email == "test@example.com"
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    
    # Verify SQS message was sent to Cognito update queue
    mock_sqs.send_message.assert_called_once()
    message_body = json.loads(mock_sqs.send_message.call_args[1]["MessageBody"])
    assert message_body["user_id"] == user_id
    assert "household_id" in message_body


def test_register_db_invalid_message(test_db, mock_sqs, mocker):
    """Test handling of invalid message format."""
    # Mock database session
    mocker.patch("auth.register_db.get_db_session", return_value=test_db)
    
    # Create SQS event with invalid JSON
    event = {
        "Records": [
            {
                "messageId": "message1",
                "body": "{invalid-json"
            }
        ]
    }
    
    # Call the Lambda handler
    response = register_db_handler(event, None)
    body = json.loads(response["body"])
    
    # Verify response
    assert response["statusCode"] == 207
    assert "message" in body
    assert "failures" in body["message"]
    assert "data" in body
    assert "results" in body["data"]
    
    # Verify no user was created
    assert test_db.query(User).count() == 0
    
    # Verify no SQS message was sent
    mock_sqs.send_message.assert_not_called()


def test_register_db_missing_fields(test_db, mock_sqs, mocker):
    """Test handling of missing required fields."""
    # Mock database session
    mocker.patch("auth.register_db.get_db_session", return_value=test_db)
    
    # Create a unique user_id for testing
    user_id = str(uuid.uuid4())
    
    # Create SQS event with missing fields (no email)
    event = {
        "Records": [
            {
                "messageId": "message1",
                "body": json.dumps({
                    # Missing email
                    "password": "StrongPass!123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "user_id": user_id
                })
            }
        ]
    }
    
    # Call the Lambda handler
    response = register_db_handler(event, None)
    body = json.loads(response["body"])
    
    # Verify response
    assert response["statusCode"] == 207
    assert "message" in body
    assert "failures" in body["message"]
    assert "data" in body
    assert "results" in body["data"]
    
    # Verify no user was created
    assert test_db.query(User).filter(User.id == user_id).first() is None
    
    # Verify no SQS message was sent
    mock_sqs.send_message.assert_not_called()


def test_register_db_duplicate_user(test_db, mock_sqs, mocker):
    """Test handling of duplicate user registration."""
    # Mock database session
    mocker.patch("auth.register_db.get_db_session", return_value=test_db)
    
    # Create a unique user_id for testing
    user_id = str(uuid.uuid4())
    
    # Create a household first
    household = Household(name="Test Household")
    test_db.add(household)
    test_db.commit()
    
    # Create a user first
    existing_user = User(
        id=user_id,
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        household_id=household.id
    )
    test_db.add(existing_user)
    test_db.commit()
    
    # Create SQS event with the same user_id
    event = {
        "Records": [
            {
                "messageId": "message1",
                "body": json.dumps({
                    "email": "test@example.com",
                    "password": "StrongPass!123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "address": "123 Main St",
                    "phone_number": "+12345678901",
                    "user_id": user_id
                })
            }
        ]
    }
    
    # Call the Lambda handler
    response = register_db_handler(event, None)
    body = json.loads(response["body"])
    
    # Verify response
    assert response["statusCode"] == 207
    assert "message" in body
    assert "failures" in body["message"]
    assert "data" in body
    assert "results" in body["data"]
    
    # Verify no additional user was created
    assert test_db.query(User).count() == 1
    
    # Verify no SQS message was sent
    mock_sqs.send_message.assert_not_called()


def test_register_db_sqs_failure(test_db, mock_sqs, mocker):
    """Test handling of SQS failures."""
    # Mock database session
    mocker.patch("auth.register_db.get_db_session", return_value=test_db)
    
    # Mock SQS send_message to raise an exception
    mock_sqs.send_message.side_effect = Exception("SQS service unavailable")
    
    # Create a unique user_id for testing
    user_id = str(uuid.uuid4())
    
    # Create SQS event with a single record
    event = {
        "Records": [
            {
                "messageId": "message1",
                "body": json.dumps({
                    "email": "test@example.com",
                    "password": "StrongPass!123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "address": "123 Main St",
                    "phone_number": "+12345678901",
                    "user_id": user_id
                })
            }
        ]
    }
    
    # Call the Lambda handler
    response = register_db_handler(event, None)
    body = json.loads(response["body"])
    
    # Verify response
    assert response["statusCode"] == 207
    assert "message" in body
    assert "failures" in body["message"]
    
    # Verify user was created in database
    user = test_db.query(User).filter(User.id == user_id).first()
    assert user is not None
    
    # Verify SQS message attempt was made
    mock_sqs.send_message.assert_called_once()


def test_register_db_multiple_records(test_db, mock_sqs, mocker):
    """Test processing of multiple SQS records."""
    # Mock database session
    mocker.patch("auth.register_db.get_db_session", return_value=test_db)
    
    # Mock SQS send_message
    mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}
    
    # Create unique user_ids for testing
    user_id1 = str(uuid.uuid4())
    user_id2 = str(uuid.uuid4())
    
    # Create SQS event with multiple records
    event = {
        "Records": [
            {
                "messageId": "message1",
                "body": json.dumps({
                    "email": "test1@example.com",
                    "password": "StrongPass!123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "address": "123 Main St",
                    "phone_number": "+12345678901",
                    "user_id": user_id1
                })
            },
            {
                "messageId": "message2",
                "body": json.dumps({
                    "email": "test2@example.com",
                    "password": "StrongPass!123",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "address": "456 Oak St",
                    "phone_number": "+12345678902",
                    "user_id": user_id2
                })
            }
        ]
    }
    
    # Call the Lambda handler
    response = register_db_handler(event, None)
    body = json.loads(response["body"])
    
    # Verify response
    assert response["statusCode"] == 200
    assert "message" in body
    assert "Successfully processed" in body["message"]
    
    # Verify users were created in database
    user1 = test_db.query(User).filter(User.id == user_id1).first()
    assert user1 is not None
    assert user1.email == "test1@example.com"
    
    user2 = test_db.query(User).filter(User.id == user_id2).first()
    assert user2 is not None
    assert user2.email == "test2@example.com"
    
    # Verify SQS messages were sent
    assert mock_sqs.send_message.call_count == 2
