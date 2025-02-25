# pylint: disable=unused-argument
"""✅ Test uploading a valid file successfully"""
import json
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from test_data.files_data import (
    test_upload_payload,
    test_large_file_payload,
    test_missing_fields_payload,
)
from files.upload_file import lambda_handler


@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_db_session")  # ✅ Mock the DB session instead of DynamoDB
def test_upload_file_success(mock_db_session, mock_s3, api_gateway_event):
    """✅ Test uploading a valid file successfully (PostgreSQL version)"""
    
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)
    
    mock_session = MagicMock()
    mock_db_session.return_value = mock_session  # ✅ Mock the database session
    mock_session.commit.return_value = None  # ✅ Simulate successful commit

    mock_s3.return_value.put_object.return_value = {}  # ✅ Simulate S3 success

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 200
    assert len(body["data"]["files_uploaded"]) > 0  # ✅ Ensure files exist
    assert any(f["file_name"] == "test.jpg" for f in body["data"]["files_uploaded"])

    ## ✅ Ensure the database commit was called
    mock_session.commit.assert_called_once()

# ✅ SUCCESS: Upload Multiple Files
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_db_session")  # ✅ Mock DB session instead of DynamoDB
def test_upload_multiple_files(mock_db_session, mock_s3, api_gateway_event):
    """✅ Test uploading multiple valid files (PostgreSQL version)"""

    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)

    mock_session = MagicMock()
    mock_db_session.return_value = mock_session  # ✅ Mock the database session
    mock_session.commit.return_value = None  # ✅ Simulate successful commit

    mock_s3.return_value.put_object.return_value = {}  # ✅ Simulate S3 success

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 200
    assert len(body["data"]["files_uploaded"]) == 2  # ✅ Ensure both files were uploaded
    assert all(
        "file_name" in file for file in body["data"]["files_uploaded"]
    )  # ✅ Ensure valid data
    mock_session.commit.assert_called_once()  # ✅ Ensure commit happens once


# ✅ SUCCESS: Upload Large File (5MB limit check)
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_db_session")  # ✅ Mock DB session
def test_upload_large_file(mock_db_session, mock_s3, api_gateway_event):
    """✅ Test uploading a large file (should pass if <=5MB)"""

    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_large_file_payload)

    mock_session = MagicMock()
    mock_db_session.return_value = mock_session  # ✅ Mock the database session
    mock_session.commit.return_value = None  # ✅ Simulate successful commit

    mock_s3.return_value.put_object.return_value = {}  # ✅ Simulate S3 success

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 200
    assert body["data"]["files_uploaded"][0]["file_name"] == "large_image.jpg"  # ✅ Ensure correct file
    mock_session.commit.assert_called_once()  # ✅ Ensure commit happen


# ❌ FAILURE: Missing `file_name`
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_db_session")  # ✅ Mock DB session
def test_upload_missing_filename(mock_db_session, mock_s3, api_gateway_event):
    """❌ Test missing `file_name` field (should return 400 Bad Request)"""

    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_missing_fields_payload)

    mock_session = MagicMock()
    mock_db_session.return_value = mock_session  # ✅ Mock the database session

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 400
    print(body)
    assert "Bad Request" in json.loads(response["body"])["message"] # ✅ Ensure error message is correct
    mock_session.commit.assert_not_called()  # ✅ Ensure no database writes occurred

# ❌ FAILURE: Invalid File Type
@patch("files.upload_file.get_s3")
def test_upload_invalid_file_type(mock_s3, api_gateway_event, test_db):
    """❌ Test uploading an invalid file type (e.g., `.exe`)"""
    
    # ✅ Arrange
    invalid_file_payload = {
        "files": [
            {"file_name": "malicious.exe", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}
        ]
    }
    
    event = api_gateway_event(http_method="POST", body=json.dumps(invalid_file_payload))

    # ✅ Act
    response = lambda_handler(event, {})

    # ✅ Assert
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 400
    assert "Bad Request" in body["message"]  # ✅ Ensure error message is correct
    assert len(body["data"]["files_failed"]) == 1
    assert body["data"]["files_failed"][0]["file_name"] == "malicious.exe"
    assert body["data"]["files_failed"][0]["reason"] == "Unsupported file format"


# ❌ FAILURE: Empty Payload
@patch("files.upload_file.get_s3")
def test_upload_empty_payload(mock_s3, api_gateway_event, test_db):
    """❌ Test empty payload should return 400"""
    
    # ✅ Arrange
    event = api_gateway_event(http_method="POST", body="{}")

    # ✅ Act
    response = lambda_handler(event, {})

    # ✅ Assert
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Bad Request" in body["message"]  # ✅ Ensure correct error message


@patch("files.upload_file.get_s3")
def test_upload_unauthorized(mock_s3, api_gateway_event, test_db):
    """❌ Test uploading without authentication (should return 401)"""

    # ✅ Arrange
    event = api_gateway_event(http_method="POST", body=json.dumps(test_upload_payload))
    
    # Remove authentication headers to simulate an unauthorized request
    event["headers"].pop("Authorization", None)
    event["requestContext"].pop("authorizer", None)

    # ✅ Act
    response = lambda_handler(event, {})

    # ✅ Assert
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 401
    assert "Unauthorized" in body["message"]  # ✅ Ensure correct error message



@patch("files.upload_file.get_s3")
def test_upload_duplicate_file_in_batch(mock_s3, api_gateway_event, test_db):
    """❌ Test uploading duplicate files within the same request (should return 207 with failed duplicates)"""

    # ✅ Arrange
    duplicate_payload = {
        "files": [
            {"file_name": "duplicate.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
            {"file_name": "duplicate.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},  # Duplicate
            {"file_name": "unique.png", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}  # ✅ Valid unique file
        ]
    }

    event = api_gateway_event(http_method="POST", body=json.dumps(duplicate_payload))

    # ✅ Act
    response = lambda_handler(event, {})

    # ✅ Assert
    body = json.loads(response["body"])

    assert response["statusCode"] == 207  # ✅ Partial success
    assert len(body["data"]["files_uploaded"]) == 2  # ✅ First instance + unique file
    assert len(body["data"]["files_failed"]) == 1  # ✅ One duplicate rejected
    assert body["data"]["files_failed"][0]["file_name"] == "duplicate.jpg"
    assert body["data"]["files_failed"][0]["reason"] == "Duplicate file in request"


@patch("files.upload_file.get_db_session")
@patch("files.upload_file.get_s3")
def test_upload_database_error(mock_s3, mock_db_session, api_gateway_event):
    """❌ Test stopping all uploads on database failure (should return 500)"""

    # ✅ Arrange
    test_payload = {
        "files": [
            {"file_name": "file_123.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
            {"file_name": "file_456.png", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}
        ]
    }

    event = api_gateway_event(http_method="POST", body=json.dumps(test_payload))
    mock_s3.return_value.put_object.return_value = None  # ✅ S3 works

    # ❌ Simulate database failure
    mock_session = mock_db_session.return_value
    mock_session.commit.side_effect = SQLAlchemyError("PostgreSQL Failure")

    # ✅ Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    # ✅ Assert
    print(f"Response Body: {body}")  # 🔍 Debugging output
    assert response["statusCode"] == 500
    assert "PostgreSQL Failure" in body["error_details"]



@patch("files.upload_file.get_s3")
def test_upload_s3_error(mock_s3, api_gateway_event):
    """⚠️ Test case where some files succeed and some fail (should return 500).
       S3 failures should prevent metadata from being saved.
    """

    # ✅ Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)
    mock_s3.return_value.put_object.side_effect = Exception("S3 Failure")  # Simulate S3 failure

    # ✅ Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    # ✅ Assert: The response should indicate failure
    assert response["statusCode"] == 500
    assert "S3 Failure" in body["error_details"]

@patch("files.upload_file.get_s3")
@patch("database.database.get_db_session")  # ✅ Mocking the DB session
def test_upload_mixed_file_types(mock_db, mock_s3, api_gateway_event, test_db):
    """❌✅ Test uploading mixed valid and invalid file types"""

    # ✅ Arrange
    mixed_payload = {
        "files": [
            {"file_name": "valid.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
            {"file_name": "invalid.exe", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
            {"file_name": "valid2.png", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}
        ]
    }

    event = api_gateway_event(http_method="POST", body=json.dumps(mixed_payload))

    # ✅ Mock DB session
    mock_db.return_value = test_db

    # ✅ Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    # ✅ Assert
    assert response["statusCode"] == 207  # ✅ Partial success
    assert len(body["data"]["files_uploaded"]) == 2  # ✅ Two valid files uploaded
    assert len(body["data"]["files_failed"]) == 1  # ✅ One invalid file rejected
    assert body["data"]["files_failed"][0]["file_name"] == "invalid.exe"
    assert body["data"]["files_failed"][0]["reason"] == "Unsupported file format"
