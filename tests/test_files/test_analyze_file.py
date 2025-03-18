"""
Tests for the analyze_file Lambda handler.

This module tests the functionality of the analyze_file Lambda handler, which:
1. Processes SQS messages containing file metadata
2. Analyzes image files using AWS Rekognition
3. Stores the analysis results in the database
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from files.analyze_file import lambda_handler, detect_labels
from models.file import File, FileStatus
from models.label import Label
from models.file_labels import FileLabel
from models.household import Household
from models.user import User
from models.claim import Claim


def test_analyze_file_success(test_db, mock_sqs):
    """Test successful file analysis for an image file"""
    # Create required related records first
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.commit()
    
    # Create a file in the database
    file_id = uuid.uuid4()
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        file_name="test_image.jpg",
        s3_key=f"files/{file_id}.jpg",
        claim_id=claim_id,
        status=FileStatus.UPLOADED,
        file_hash="test_hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(test_file)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "s3_key": f"files/{file_id}.jpg",
                    "file_name": "test_image.jpg",
                    "household_id": str(household_id),
                    "claim_id": str(claim_id),
                })
            }
        ]
    }
    
    # Mock the Rekognition client
    mock_rekognition_response = {
        "Labels": [
            {"Name": "Car", "Confidence": 98.5},
            {"Name": "Vehicle", "Confidence": 98.5},
            {"Name": "Transportation", "Confidence": 98.5}
        ]
    }
    
    with patch("files.analyze_file.get_rekognition_client") as mock_get_rekognition:
        mock_rekognition = MagicMock()
        mock_rekognition.detect_labels.return_value = mock_rekognition_response
        mock_get_rekognition.return_value = mock_rekognition
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File analysis complete"
        
        # Verify Rekognition was called
        mock_rekognition.detect_labels.assert_called_once()
        
        # Verify file status was updated
        updated_file = test_db.query(File).filter_by(id=file_id).first()
        assert updated_file.status == FileStatus.ANALYZED
        
        # Verify labels were created and associated with the file
        file_labels = test_db.query(FileLabel).filter_by(file_id=file_id).all()
        assert len(file_labels) == 3
        
        # Get the actual labels
        label_ids = [fl.label_id for fl in file_labels]
        labels = test_db.query(Label).filter(Label.id.in_(label_ids)).all()
        label_texts = [label.label_text for label in labels]
        
        assert "Car" in label_texts
        assert "Vehicle" in label_texts
        assert "Transportation" in label_texts


def test_analyze_non_image_file(test_db, mock_sqs):
    """Test handling of non-image files that can't be analyzed with Rekognition"""
    # Create required related records first
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.commit()
    
    # Create a file in the database
    file_id = uuid.uuid4()
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        file_name="test_document.pdf",
        s3_key=f"files/{file_id}.pdf",
        claim_id=claim_id,
        status=FileStatus.UPLOADED,
        file_hash="test_hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(test_file)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "s3_key": f"files/{file_id}.pdf",
                    "file_name": "test_document.pdf",
                    "household_id": str(household_id),
                    "claim_id": str(claim_id),
                })
            }
        ]
    }
    
    with patch("files.analyze_file.get_rekognition_client") as mock_get_rekognition:
        mock_rekognition = MagicMock()
        mock_get_rekognition.return_value = mock_rekognition
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File analysis complete"
        
        # Verify Rekognition was NOT called
        mock_rekognition.detect_labels.assert_not_called()
        
        # Verify file status was updated
        updated_file = test_db.query(File).filter_by(id=file_id).first()
        assert updated_file.status == FileStatus.ANALYZED
        
        # Verify no labels were created
        file_labels = test_db.query(FileLabel).filter_by(file_id=file_id).all()
        assert len(file_labels) == 0


def test_analyze_file_rekognition_error(test_db, mock_sqs):
    """Test handling of Rekognition errors during file analysis"""
    # Create required related records first
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    
    test_db.add(test_household)
    test_db.add(test_user)
    test_db.add(test_claim)
    test_db.commit()
    
    # Create a file in the database
    file_id = uuid.uuid4()
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        file_name="test_image.jpg",
        s3_key=f"files/{file_id}.jpg",
        claim_id=claim_id,
        status=FileStatus.UPLOADED,
        file_hash="test_hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(test_file)
    test_db.commit()
    
    # Create a mock SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(file_id),
                    "s3_key": f"files/{file_id}.jpg",
                    "file_name": "test_image.jpg",
                    "household_id": str(household_id),
                    "claim_id": str(claim_id),
                })
            }
        ]
    }
    
    with patch("files.analyze_file.get_rekognition_client") as mock_get_rekognition:
        mock_rekognition = MagicMock()
        mock_rekognition.detect_labels.side_effect = Exception("Rekognition error")
        mock_get_rekognition.return_value = mock_rekognition
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File analysis complete"
        
        # Verify Rekognition was called
        mock_rekognition.detect_labels.assert_called_once()
        
        # Verify file status was updated to ERROR
        updated_file = test_db.query(File).filter_by(id=file_id).first()
        assert updated_file.status == FileStatus.ERROR
        
        # Verify no labels were created
        file_labels = test_db.query(FileLabel).filter_by(file_id=file_id).all()
        assert len(file_labels) == 0


def test_analyze_file_invalid_message(test_db, mock_sqs):
    """Test handling of invalid SQS messages"""
    # Create a mock SQS event with invalid JSON
    sqs_event = {
        "Records": [
            {
                "body": "invalid-json"
            }
        ]
    }
    
    # Call the lambda handler
    response = lambda_handler(sqs_event, {})
    
    # Assertions
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["message"] == "File analysis complete"
    
    # The function should handle the error gracefully and continue


def test_analyze_file_missing_file_id(test_db, mock_sqs):
    """Test handling of SQS messages with missing file_id"""
    # Create a mock SQS event with missing file_id
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "s3_key": "files/test.jpg",
                    "file_name": "test_image.jpg",
                    "household_id": str(uuid.uuid4()),
                    "claim_id": str(uuid.uuid4()),
                })
            }
        ]
    }
    
    # Call the lambda handler
    response = lambda_handler(sqs_event, {})
    
    # Assertions
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["message"] == "File analysis complete"
    
    # The function should handle the error gracefully and continue


def test_analyze_file_nonexistent_file(test_db, mock_sqs):
    """Test handling of SQS messages referencing nonexistent files"""
    # Create a mock SQS event with a non-existent file_id
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "file_id": str(uuid.uuid4()),  # Random UUID that doesn't exist in DB
                    "s3_key": "files/test.jpg",
                    "file_name": "test_image.jpg",
                    "household_id": str(uuid.uuid4()),
                    "claim_id": str(uuid.uuid4()),
                })
            }
        ]
    }
    
    with patch("files.analyze_file.get_rekognition_client") as mock_get_rekognition:
        mock_rekognition = MagicMock()
        mock_rekognition.detect_labels.return_value = {"Labels": []}
        mock_get_rekognition.return_value = mock_rekognition
        
        # Call the lambda handler
        response = lambda_handler(sqs_event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["message"] == "File analysis complete"
        
        # Verify Rekognition was NOT called because the file doesn't exist in the database
        mock_rekognition.detect_labels.assert_not_called()
        
        # The function should handle the error gracefully and continue


def test_detect_labels_function():
    """Test the detect_labels function directly"""
    # Mock the Rekognition client
    mock_rekognition_response = {
        "Labels": [
            {"Name": "Car", "Confidence": 98.5},
            {"Name": "Vehicle", "Confidence": 98.5}
        ]
    }
    
    with patch("files.analyze_file.get_rekognition_client") as mock_get_rekognition:
        mock_rekognition = MagicMock()
        mock_rekognition.detect_labels.return_value = mock_rekognition_response
        mock_get_rekognition.return_value = mock_rekognition
        
        # Call the function
        labels = detect_labels("test/s3/key.jpg")
        
        # Assertions
        assert len(labels) == 2
        assert labels[0]["Name"] == "Car"
        assert labels[1]["Name"] == "Vehicle"
        
        # Verify Rekognition was called with correct parameters
        mock_rekognition.detect_labels.assert_called_once_with(
            Image={
                'S3Object': {
                    'Bucket': 'test-bucket',
                    'Name': 'test/s3/key.jpg'
                }
            },
            MinConfidence=70.0
        )


def test_detect_labels_missing_env_var():
    """Test detect_labels handling of missing environment variables"""
    with patch("files.analyze_file.S3_BUCKET_NAME", None):
        with pytest.raises(ValueError, match="S3_BUCKET_NAME environment variable is not set"):
            detect_labels("test/s3/key.jpg")
