"""
Tests for the process_file Lambda handler.

This module tests the functionality of the process_file Lambda handler, which:
1. Processes SQS messages containing file data and metadata
2. Decodes base64 file data
3. Uploads files to S3
4. Stores file metadata in the database
5. Sends a message to the analysis queue
"""
import json
import uuid
import base64
from unittest.mock import patch, MagicMock
import pytest
from files.process_file import lambda_handler, send_to_analysis_queue
from models.file import File, FileStatus
from models.user import User
from models.household import Household
from models.claim import Claim
from models.room import Room


def test_process_file_success(test_db, mock_sqs):
    """Test successful file processing"""
    # Create test data
    file_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    room_id = uuid.uuid4()
    file_hash = "test_hash"
    
    # Create required related records first
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_room = Room(id=room_id, name="Test Room", household_id=household_id, claim_id=claim_id)
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.add(test_room)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "user_id": str(user_id),
                    "household_id": str(household_id),
                    "file_name": "test_image.jpg",
                    "s3_key": f"files/{file_id}.jpg",
                    "claim_id": str(claim_id),
                    "room_id": str(room_id),
                    "file_hash": file_hash,
                    "file_data": base64.b64encode(b"test_image_data").decode("utf-8")
                })
            }
        ]
    }
    
    # Mock S3 client and ensure SQS_ANALYSIS_QUEUE_URL is set
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch("files.process_file.get_sqs_client") as mock_get_sqs, \
         patch("files.process_file.SQS_ANALYSIS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-analysis-queue"):
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        
        # Set up the mock SQS client
        mock_get_sqs.return_value = mock_sqs
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File processing complete"
        
        # Verify S3 was called
        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket", 
            Key=f"files/{file_id}.jpg", 
            Body=b"test_image_data"
        )
        
        # Verify file was stored in database
        file = test_db.query(File).filter_by(id=file_id).first()
        assert file is not None
        assert file.uploaded_by == user_id
        assert file.household_id == household_id
        assert file.file_name == "test_image.jpg"
        assert file.s3_key == f"files/{file_id}.jpg"
        assert file.claim_id == claim_id
        assert file.room_id == room_id
        assert file.status == FileStatus.UPLOADED
        assert file.file_hash == file_hash
        
        # Verify SQS was called to send to analysis queue
        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args[1]
        assert "MessageBody" in call_args
        message_body = json.loads(call_args["MessageBody"])
        assert message_body["file_id"] == str(file_id)
        assert message_body["s3_key"] == f"files/{file_id}.jpg"
        assert message_body["file_name"] == "test_image.jpg"
        assert message_body["household_id"] == str(household_id)
        assert message_body["claim_id"] == str(claim_id)


def test_process_file_no_room_id(test_db, mock_sqs):
    """Test file processing without a room_id"""
    # Create test data
    file_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    file_hash = "test_hash"
    
    # Create required related records first
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.commit()
    
    # Create a mock SQS event without room_id
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "user_id": str(user_id),
                    "household_id": str(household_id),
                    "file_name": "test_image.jpg",
                    "s3_key": f"files/{file_id}.jpg",
                    "claim_id": str(claim_id),
                    "room_id": None,  # No room ID
                    "file_hash": file_hash,
                    "file_data": base64.b64encode(b"test_image_data").decode("utf-8")
                })
            }
        ]
    }
    
    # Mock S3 client and ensure SQS_ANALYSIS_QUEUE_URL is set
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch("files.process_file.get_sqs_client") as mock_get_sqs, \
         patch("files.process_file.SQS_ANALYSIS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-analysis-queue"):
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        
        # Set up the mock SQS client
        mock_get_sqs.return_value = mock_sqs
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File processing complete"
        
        # Verify S3 was called
        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket", 
            Key=f"files/{file_id}.jpg", 
            Body=b"test_image_data"
        )
        
        # Verify file was stored in database
        file = test_db.query(File).filter_by(id=file_id).first()
        assert file is not None
        assert file.uploaded_by == user_id
        assert file.household_id == household_id
        assert file.file_name == "test_image.jpg"
        assert file.s3_key == f"files/{file_id}.jpg"
        assert file.claim_id == claim_id
        assert file.room_id is None  # Room ID should be None
        assert file.status == FileStatus.UPLOADED
        assert file.file_hash == file_hash
        
        # Verify SQS was called to send to analysis queue
        mock_sqs.send_message.assert_called_once()


def test_process_file_invalid_base64(test_db, mock_sqs):
    """Test handling of invalid base64 data"""
    # Create test data
    file_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    room_id = uuid.uuid4()
    file_hash = "test_hash"
    
    # Create required related records first
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_room = Room(id=room_id, name="Test Room", household_id=household_id, claim_id=claim_id)
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.add(test_room)
    test_db.commit()
    
    # Create a mock SQS event with invalid base64
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "user_id": str(user_id),
                    "household_id": str(household_id),
                    "file_name": "test_image.jpg",
                    "s3_key": f"files/{file_id}.jpg",
                    "claim_id": str(claim_id),
                    "room_id": str(room_id),
                    "file_hash": file_hash,
                    "file_data": "invalid-base64-data"  # Invalid base64
                })
            }
        ]
    }
    
    # Mock S3 client
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch("files.process_file.get_sqs_client") as mock_get_sqs:
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        
        # Set up the mock SQS client
        mock_get_sqs.return_value = mock_sqs
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 400
        assert "Invalid base64 data" in json.loads(response["body"])["error"]
        
        # Verify file was not stored in database
        file = test_db.query(File).filter_by(id=file_id).first()
        assert file is None


def test_process_file_s3_failure(test_db, mock_sqs):
    """Test handling of S3 upload failures"""
    # Create test data
    file_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    room_id = uuid.uuid4()
    file_hash = "test_hash"
    
    # Create required related records first
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_room = Room(id=room_id, name="Test Room", household_id=household_id, claim_id=claim_id)
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.add(test_room)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "user_id": str(user_id),
                    "household_id": str(household_id),
                    "file_name": "test_image.jpg",
                    "s3_key": f"files/{file_id}.jpg",
                    "claim_id": str(claim_id),
                    "room_id": str(room_id),
                    "file_hash": file_hash,
                    "file_data": base64.b64encode(b"test_image_data").decode("utf-8")
                })
            }
        ]
    }
    
    # Mock S3 client with failure
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch("files.process_file.get_sqs_client") as mock_get_sqs:
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 upload failed")
        mock_get_s3.return_value = mock_s3
        
        # Set up the mock SQS client
        mock_get_sqs.return_value = mock_sqs
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 500
        assert "Error uploading file to S3" in json.loads(response["body"])["error"]
        
        # Verify file was not stored in database
        file = test_db.query(File).filter_by(id=file_id).first()
        assert file is None
        
        # Verify SQS was not called
        mock_sqs.send_message.assert_not_called()


def test_process_file_db_failure(test_db, mock_sqs):
    """Test handling of database failures"""
    # Create test data
    file_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    room_id = uuid.uuid4()
    file_hash = "test_hash"
    
    # Create required related records first
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_room = Room(id=room_id, name="Test Room", household_id=household_id, claim_id=claim_id)
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.add(test_room)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "user_id": str(user_id),
                    "household_id": str(household_id),
                    "file_name": "test_image.jpg",
                    "s3_key": f"files/{file_id}.jpg",
                    "claim_id": str(claim_id),
                    "room_id": str(room_id),
                    "file_hash": file_hash,
                    "file_data": base64.b64encode(b"test_image_data").decode("utf-8")
                })
            }
        ]
    }
    
    # Mock S3 client and DB session with failure
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch("files.process_file.get_sqs_client") as mock_get_sqs, \
         patch("files.process_file.get_db_session") as mock_get_db:
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        
        # Set up the mock SQS client
        mock_get_sqs.return_value = mock_sqs
        
        # Set up mock DB session that raises an exception on commit
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("Database error")
        mock_get_db.return_value = mock_session
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 500
        assert "Error storing file metadata in database" in json.loads(response["body"])["error"]
        
        # Verify S3 was called
        mock_s3.put_object.assert_called_once()
        
        # Verify SQS was not called
        mock_sqs.send_message.assert_not_called()


def test_process_file_analysis_queue_failure(test_db, mock_sqs):
    """Test handling of failures when sending to analysis queue"""
    # Create test data
    file_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    file_hash = "test_hash"
    
    # Create required related records first
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "user_id": str(user_id),
                    "household_id": str(household_id),
                    "file_name": "test_image.jpg",
                    "s3_key": f"files/{file_id}.jpg",
                    "claim_id": str(claim_id),
                    "file_hash": file_hash,
                    "file_data": base64.b64encode(b"test_image_data").decode("utf-8")
                })
            }
        ]
    }
    
    # Mock S3 client
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch("files.process_file.get_sqs_client") as mock_get_sqs:
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        
        # Set up the mock SQS client to raise an exception
        mock_get_sqs.return_value = mock_sqs
        mock_sqs.send_message.side_effect = Exception("SQS error")
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File processing complete"
        
        # Verify file was stored in database
        file = test_db.query(File).filter_by(id=file_id).first()
        assert file is not None
        assert file.status == FileStatus.UPLOADED  # Status should still be UPLOADED


def test_process_file_sqs_failure(test_db, mock_sqs):
    """Test handling of SQS failures"""
    # Create test data
    file_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    room_id = uuid.uuid4()
    file_hash = "test_hash"
    
    # Create required related records first
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_room = Room(id=room_id, name="Test Room", household_id=household_id, claim_id=claim_id)
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.add(test_room)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "user_id": str(user_id),
                    "household_id": str(household_id),
                    "file_name": "test_image.jpg",
                    "s3_key": f"files/{file_id}.jpg",
                    "claim_id": str(claim_id),
                    "room_id": str(room_id),
                    "file_hash": file_hash,
                    "file_data": base64.b64encode(b"test_image_data").decode("utf-8")
                })
            }
        ]
    }
    
    # Mock S3 client and SQS client with failure
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch("files.process_file.get_sqs_client") as mock_get_sqs, \
         patch("files.process_file.SQS_ANALYSIS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-analysis-queue"):
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        
        # Set up the mock SQS client to raise an exception
        mock_sqs.send_message.side_effect = Exception("SQS error")
        mock_get_sqs.return_value = mock_sqs
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions - we should still get a success response even if SQS fails
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File processing complete"
        
        # Check that there's a warning about the SQS failure
        response_body = json.loads(response["body"])
        assert "warnings" in response_body
        assert len(response_body["warnings"]) > 0
        assert any("Failed to queue file" in warning for warning in response_body["warnings"])
        
        # Verify S3 was called
        mock_s3.put_object.assert_called_once()
        
        # Verify file was stored in database
        file = test_db.query(File).filter_by(id=file_id).first()
        assert file is not None
        assert file.uploaded_by == user_id
        assert file.household_id == household_id
        assert file.file_name == "test_image.jpg"
        assert file.s3_key == f"files/{file_id}.jpg"
        assert file.claim_id == claim_id
        assert file.room_id == room_id
        assert file.status == FileStatus.UPLOADED
        assert file.file_hash == file_hash


def test_upload_to_s3_function():
    """Test the upload_to_s3 function directly"""
    # Mock S3 client
    with patch("files.process_file.get_s3_client") as mock_get_s3, \
         patch.dict("os.environ", {"S3_BUCKET_NAME": "test-bucket"}):
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        
        # Call the function
        s3_url = upload_to_s3("test_key.jpg", b"test_data")
        
        # Assertions
        assert s3_url == "s3://test-bucket/test_key.jpg"
        
        # Verify S3 was called with correct parameters
        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test_key.jpg",
            Body=b"test_data"
        )


def test_upload_to_s3_missing_env_var():
    """Test upload_to_s3 handling of missing environment variables"""
    # Patch environment variable to be None
    with patch("files.process_file.S3_BUCKET_NAME", None):
        with pytest.raises(ValueError, match="S3_BUCKET_NAME environment variable is not set"):
            upload_to_s3("test_key.jpg", b"test_data")


def test_send_to_analysis_queue_function():
    """Test the send_to_analysis_queue function directly"""
    # Mock SQS client
    with patch("files.process_file.get_sqs_client") as mock_get_sqs, \
         patch("files.process_file.SQS_ANALYSIS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789012/test-analysis-queue"):
        mock_sqs_client = MagicMock()
        mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}
        mock_get_sqs.return_value = mock_sqs_client
        
        # Call the function
        file_id = uuid.uuid4()
        s3_key = f"files/{file_id}.jpg"
        file_name = "test_image.jpg"
        household_id = uuid.uuid4()
        claim_id = uuid.uuid4()
        
        result = send_to_analysis_queue(file_id, s3_key, file_name, household_id, claim_id)
        
        # Assertions
        assert result == "test-message-id"
        mock_sqs_client.send_message.assert_called_once()
        
        # Verify the message body
        call_args = mock_sqs_client.send_message.call_args[1]
        assert "MessageBody" in call_args
        message_body = json.loads(call_args["MessageBody"])
        assert message_body["file_id"] == str(file_id)
        assert message_body["s3_key"] == s3_key
        assert message_body["file_name"] == file_name
        assert message_body["household_id"] == str(household_id)
        assert message_body["claim_id"] == str(claim_id)


def test_send_to_analysis_queue_function_no_queue_url():
    """Test the send_to_analysis_queue function with no queue URL"""
    # Mock SQS client with no queue URL
    with patch("files.process_file.get_sqs_client") as mock_get_sqs, \
         patch("files.process_file.SQS_ANALYSIS_QUEUE_URL", None):
        mock_sqs_client = MagicMock()
        mock_get_sqs.return_value = mock_sqs_client
        
        # Call the function
        file_id = uuid.uuid4()
        s3_key = f"files/{file_id}.jpg"
        file_name = "test_image.jpg"
        household_id = uuid.uuid4()
        claim_id = uuid.uuid4()
        
        result = send_to_analysis_queue(file_id, s3_key, file_name, household_id, claim_id)
        
        # Assertions
        assert result == "dummy-message-id-for-testing"
        mock_sqs_client.send_message.assert_not_called()
