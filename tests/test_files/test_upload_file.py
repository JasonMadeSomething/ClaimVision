"""
Test the upload_file lambda function
"""
import json
import uuid
import base64
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from models import Household, User, Claim
from files.upload_file import lambda_handler

def test_upload_file_success(test_db, api_gateway_event, mock_sqs):
    """ Test a successful file upload """
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    # Create a test file payload
    upload_payload = {
        "files": [{"file_name": "test.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert "message" in body
    assert body["message"] == "Files queued for processing successfully"
    assert "data" in body
    assert "files_queued" in body["data"]
    assert len(body["data"]["files_queued"]) == 1
    assert body["data"]["files_queued"][0]["file_name"] == "test.jpg"
    
    # Verify SQS was called
    mock_sqs.send_message.assert_called_once()
    
    # Verify the message payload
    call_args = mock_sqs.send_message.call_args[1]
    assert "MessageBody" in call_args
    message_body = json.loads(call_args["MessageBody"])
    assert "file_name" in message_body
    assert message_body["file_name"] == "test.jpg"
    assert "claim_id" in message_body
    assert message_body["claim_id"] == str(test_claim.id)
    assert "household_id" in message_body
    assert message_body["household_id"] == str(household_id)

def test_upload_s3_called(test_db, api_gateway_event, mock_sqs):
    """ Test that SQS is called for file uploads"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()
    
    # Create a test file payload
    upload_payload = {
        "files": [{"file_name": "test.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Verify response is successful
    assert response["statusCode"] == 200
    
    # Verify SQS was called
    mock_sqs.send_message.assert_called_once()
    
    # Verify the message payload
    call_args = mock_sqs.send_message.call_args[1]
    assert "MessageBody" in call_args
    message_body = json.loads(call_args["MessageBody"])
    assert "file_name" in message_body
    assert message_body["file_name"] == "test.jpg"
    assert "claim_id" in message_body
    assert message_body["claim_id"] == str(test_claim.id)
    assert "household_id" in message_body
    assert message_body["household_id"] == str(household_id)

def test_upload_missing_filename(test_db, api_gateway_event):
    """ Test missing `file_name` field (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    # Arrange
    missing_fields_payload = {"files": [{"file_data": base64.b64encode(b"dummydata").decode("utf-8")}], "claim_id": str(test_claim.id)}
    event = api_gateway_event(http_method="POST", body=json.dumps(missing_fields_payload), auth_user=str(user_id))

    # Act
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    # Assert
    assert response["statusCode"] == 400
    assert "Bad Request" in body["status"]

def test_upload_invalid_file_type(test_db, api_gateway_event):
    """ Test uploading an invalid file type (e.g., `.exe`)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    # Arrange
    invalid_file_payload = {
        "files": [{"file_name": "malicious.exe", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(invalid_file_payload), auth_user=str(user_id))

    # Act
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    # Assert
    assert response["statusCode"] == 400
    assert body["data"]["files_failed"][0]["file_name"] == "malicious.exe"
    assert "Invalid file type. Allowed types:" in body["data"]["files_failed"][0]["reason"]

def test_upload_multiple_files(test_db, api_gateway_event):
    """ Test uploading multiple files successfully"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    upload_payload = {
        "files": [
            {"file_name": "test1.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")},
            {"file_name": "test2.jpg", "file_data": base64.b64encode(b"dummydata2").decode("utf-8")}
        ],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 200
    assert len(body["data"]["files_queued"]) == 2

def test_upload_large_file(test_db, api_gateway_event):
    """ Test uploading a large file within allowed size limits"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    large_file_data = "A" * (5 * 1024 * 1024)  # 5MB file
    upload_payload = {
        "files": [{"file_name": "large.jpg", "file_data": large_file_data}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["files_queued"]) == 1
    assert body["data"]["files_queued"][0]["file_name"] == "large.jpg"

def test_upload_empty_payload(test_db, api_gateway_event):
    """ Test uploading with an empty payload (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    event = api_gateway_event(http_method="POST", body=json.dumps({}), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Bad Request" in body["status"]

def test_upload_duplicate_files(test_db, api_gateway_event):
    """ Test uploading duplicate files in a batch"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    upload_payload = {
        "files": [
            {"file_name": "duplicate.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")},
            {"file_name": "duplicate.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}
        ],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 207  # Multi-Status
    assert len(body["data"]["files_failed"]) == 1

def test_upload_unauthorized(api_gateway_event):
    """ Test uploading without authentication (should return 401 Unauthorized)"""
    upload_payload = {
        "files": [{"file_name": "test.jpg", "file_data": "data1"}]
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=None)

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 401
    assert "Unauthorized" in body["message"]

def test_upload_mixed_valid_invalid_files(test_db, api_gateway_event):
    """ Test uploading a mix of valid and invalid files (should return 207 Multi-Status)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    upload_payload = {
        "files": [
            {"file_name": "valid.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")},
            {"file_name": "invalid.exe", "file_data": base64.b64encode(b"dummydata2").decode("utf-8")}
        ],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 207  # Multi-Status
    assert len(body["data"]["files_queued"]) == 1
    assert len(body["data"]["files_failed"]) == 1

def test_upload_file_no_extension(test_db, api_gateway_event):
    """ Test uploading a file with no extension (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    upload_payload = {
        "files": [{"file_name": "noextension", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert len(body["data"]["files_failed"]) == 1
    assert "Missing file extension" in body["data"]["files_failed"][0]["reason"]

def test_upload_empty_file(test_db, api_gateway_event):
    """ Test uploading an empty file (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    upload_payload = {
        "files": [{"file_name": "empty.jpg", "file_data": base64.b64encode(b"").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert any(f["reason"] == "Missing file data." for f in body["data"]["files_failed"])

def test_upload_duplicate_content_different_names(test_db, api_gateway_event):
    """ Test uploading files with duplicate content but different names (should return 409 Conflict)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()
    
    # Same data, different filenames
    same_data = base64.b64encode(b"samedummydata").decode("utf-8")
    
    upload_payload = {
        "files": [
            {"file_name": "original.jpg", "file_data": same_data},
            {"file_name": "duplicate.jpg", "file_data": same_data}
        ],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 207
    assert "message" in body
    assert body["message"] == "Some files queued for processing"
    assert "data" in body
    assert "files_queued" in body["data"]
    assert "files_failed" in body["data"]
    assert len(body["data"]["files_queued"]) == 1
    assert len(body["data"]["files_failed"]) == 1
    assert any("Duplicate content detected" in f["reason"] for f in body["data"]["files_failed"])

def test_upload_non_base64_data(test_db, api_gateway_event):
    """ Test uploading a file with non-base64 encoded data (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    upload_payload = {
        "files": [{"file_name": "nonbase64.jpg", "file_data": "not_base64"}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert any(f["reason"] == "Invalid file data format." for f in body["data"]["files_failed"])

def test_upload_large_file_exceeds_limit(test_db, api_gateway_event):
    """ Test uploading a file that exceeds the allowed size limit (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    large_file_data = base64.b64encode(b"A" * (11 * 1024 * 1024)).decode("utf-8")  # 11MB file (exceeds 10MB limit)
    upload_payload = {
        "files": [{"file_name": "large.jpg", "file_data": large_file_data}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert any("exceeds maximum size" in f["reason"] for f in body["data"]["files_failed"])

def test_upload_mixed_success_failure(test_db, api_gateway_event, mock_sqs):
    """ Test uploading multiple files with some succeeding and some failing (should return 207 Multi-Status)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()
    
    upload_payload = {
        "files": [
            {"file_name": "valid.jpg", "file_data": base64.b64encode(b"validdata").decode("utf-8")},
            {"file_name": "invalid", "file_data": base64.b64encode(b"invaliddata").decode("utf-8")}
        ],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 207
    assert "message" in body
    assert body["message"] == "Some files queued for processing"
    assert "data" in body
    assert "files_queued" in body["data"]
    assert "files_failed" in body["data"]
    assert len(body["data"]["files_queued"]) == 1
    assert len(body["data"]["files_failed"]) == 1

def test_upload_sqs_failure(test_db, api_gateway_event, mock_sqs):
    """ Test handling an SQS failure during file upload (should return 500 Internal Server Error)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    # Configure mock_sqs to raise an exception
    mock_sqs.send_message.side_effect = ValueError("SQS Failure")
    
    upload_payload = {
        "files": [{"file_name": "s3fail.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    
    # Call the handler with our mocked session
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    mock_sqs.send_message.assert_called_once()
    assert response["statusCode"] == 500
    assert "error_details" in body
    assert "Internal Server Error" in body["error_details"]
    
    # This is the key assertion - make sure files_failed exists and contains our failed file
    assert "files_failed" in body["data"], f"Expected 'files_failed' in data, got keys: {list(body['data'].keys())}"
    assert len(body["data"]["files_failed"]) > 0
    assert any("Failed to queue for processing." in f["reason"] for f in body["data"]["files_failed"])

def test_upload_database_failure(test_db, api_gateway_event, mock_sqs):
    """ Test handling database failures gracefully"""
    # Create a real user in the test database
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()
    
    # Create a test payload
    upload_payload = {
        "files": [{"file_name": "dbfail.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    
    # Mock the database session to raise an exception when querying
    with patch("files.upload_file.get_db_session") as mock_get_db, \
         patch("utils.lambda_utils.get_db_session") as mock_lambda_get_db:
        # Configure the mocks to raise an exception
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database Error")
        mock_get_db.return_value = mock_db
        mock_lambda_get_db.return_value = mock_db
        
        # Call the handler with no db_session to force it to use get_db_session
        response = lambda_handler(event, {}, db_session=None)
        body = json.loads(response["body"])
        
        # Assertions
        assert response["statusCode"] == 500
        assert "error_details" in body
        assert "Database error" in body["error_details"]
        
        # Verify SQS was not called
        mock_sqs.send_message.assert_not_called()