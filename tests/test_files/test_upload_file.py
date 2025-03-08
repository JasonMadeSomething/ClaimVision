"""
Test the upload_file lambda function
"""
import json
import uuid
import base64
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from models import Household, User, Claim
from files.upload_file import lambda_handler

def test_upload_file_success(test_db, api_gateway_event):
    """✅ Test uploading a valid file successfully (PostgreSQL version)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    #Create a household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    with patch("files.upload_file.upload_to_s3") as mock_s3_upload:
        mock_s3_upload.return_value = "s3://bucket-name/test.jpg"

        # ✅ Arrange
        upload_payload = {
            "files": [
                {"file_name": "test.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA==", "file_hash": "test_hash"}
            ],
            "claim_id": str(test_claim.id)
        }
        event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

        # ✅ Act
        response = lambda_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])
        print(body)
        # ✅ Assert
        assert response["statusCode"] == 200
        assert len(body["data"]["files_uploaded"]) == 1
        assert body["data"]["files_uploaded"][0]["file_name"] == "test.jpg"
        mock_s3_upload.assert_called_once()  # ✅ Ensure S3 upload is triggered

def test_upload_s3_called(test_db, api_gateway_event):
    """✅ Test that S3 is called for file uploads"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    with patch("files.upload_file.upload_to_s3") as mock_s3_upload:
        mock_s3_upload.return_value = "s3://bucket-name/test.jpg"

        upload_payload = {
            "files": [{"file_name": "test.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8"), "file_hash": "test_hash"}],
            "claim_id": str(test_claim.id)
        }
        event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

        response = lambda_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body["data"]["files_uploaded"]) == 1
        assert mock_s3_upload.called, "S3 upload function was not called!"

def test_upload_missing_filename(test_db, api_gateway_event):
    """❌ Test missing `file_name` field (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # ✅ Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    # ✅ Arrange
    missing_fields_payload = {"files": [{"file_data": base64.b64encode(b"dummydata").decode("utf-8")}], "claim_id": str(test_claim.id)}
    event = api_gateway_event(http_method="POST", body=json.dumps(missing_fields_payload), auth_user=str(user_id))

    # ✅ Act
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    # ✅ Assert
    assert response["statusCode"] == 400
    assert "Bad Request" in body["status"]

def test_upload_invalid_file_type(test_db, api_gateway_event):
    """❌ Test uploading an invalid file type (e.g., `.exe`)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # ✅ Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    # ✅ Arrange
    invalid_file_payload = {
        "files": [{"file_name": "malicious.exe", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(invalid_file_payload), auth_user=str(user_id))

    # ✅ Act
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    # ✅ Assert
    assert response["statusCode"] == 400
    assert body["data"]["files_failed"][0]["file_name"] == "malicious.exe"
    assert body["data"]["files_failed"][0]["reason"] == "Unsupported file format."

def test_upload_multiple_files(test_db, api_gateway_event):
    """✅ Test uploading multiple files successfully"""
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
    print(body)
    assert response["statusCode"] == 200
    assert len(body["data"]["files_uploaded"]) == 2

def test_upload_large_file(test_db, api_gateway_event):
    """✅ Test uploading a large file within allowed size limits"""
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
    assert len(body["data"]["files_uploaded"]) == 1
    assert body["data"]["files_uploaded"][0]["file_name"] == "large.jpg"

def test_upload_empty_payload(test_db, api_gateway_event):
    """❌ Test uploading with an empty payload (should return 400 Bad Request)"""
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
    """❌ Test uploading duplicate files in a batch"""
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
    print(body)
    assert response["statusCode"] == 207  # Multi-Status
    assert len(body["data"]["files_failed"]) == 1

def test_upload_unauthorized(api_gateway_event):
    """❌ Test uploading without authentication (should return 401 Unauthorized)"""
    upload_payload = {
        "files": [{"file_name": "test.jpg", "file_data": "data1"}]
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=None)

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 401
    assert "Unauthorized" in body["message"]

def test_upload_mixed_valid_invalid_files(test_db, api_gateway_event):
    """❌✅ Test uploading a mix of valid and invalid files (should return 207 Multi-Status)"""
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
    print(body)
    assert response["statusCode"] == 207  # Multi-Status
    assert len(body["data"]["files_uploaded"]) == 1
    assert len(body["data"]["files_failed"]) == 1

def test_upload_s3_failure(test_db, api_gateway_event):
    """❌ Test handling an S3 failure during file upload (should return 500 Internal Server Error)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    # Create a spy on the test_db.rollback method to track if it's called
    with patch.object(test_db, 'rollback', wraps=test_db.rollback) as mock_rollback:
        with patch("files.upload_file.upload_to_s3", side_effect=ValueError("S3 Failure")) as mock_s3_upload:
            upload_payload = {
                "files": [{"file_name": "s3fail.jpg", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
                "claim_id": str(test_claim.id)
            }
            event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

            response = lambda_handler(event, {}, db_session=test_db)
            
            # Debug output
            print("Full response:", response)
            body = json.loads(response["body"])
            print("Response body:", body)
            
            # Assertions
            mock_s3_upload.assert_called_once()
            assert response["statusCode"] == 500
            assert "message" in body
            assert body["message"] == "Internal Server Error"
            
            # Check if files_failed is in the data
            assert "data" in body
            assert isinstance(body["data"], dict)
            
            # This is the key assertion - make sure files_failed exists and contains our failed file
            assert "files_failed" in body["data"], f"Expected 'files_failed' in data, got keys: {list(body['data'].keys())}"
            assert len(body["data"]["files_failed"]) > 0
            assert any(f["reason"] == "Failed to upload to S3." for f in body["data"]["files_failed"])
            
            # Verify rollback was called
            mock_rollback.assert_called_once()

def test_upload_database_failure(test_db, api_gateway_event):
    """❌ Test handling a database failure during file metadata storage"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    with patch("files.upload_file.get_db_session", side_effect=SQLAlchemyError("DB Failure")) as mock_db:
        valid_base64_data = base64.b64encode(b"dummydata").decode("utf-8")
        upload_payload = {"files": [{"file_name": "dbfail.jpg", "file_data": valid_base64_data}], "claim_id": str(test_claim.id)}
        event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))    

        response = lambda_handler(event, {})
        body = json.loads(response["body"])

        mock_db.assert_called_once()

        assert response["statusCode"] == 500
        assert "Internal Server Error" in body["message"]

def test_upload_file_no_extension(test_db, api_gateway_event):
    """❌ Test uploading a file with no extension (should return 400 Bad Request)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    upload_payload = {
        "files": [{"file_name": "no_extension", "file_data": base64.b64encode(b"dummydata").decode("utf-8")}],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Unsupported file format" in body["message"]

def test_upload_empty_file(test_db, api_gateway_event):
    """❌ Test uploading an empty file (should return 400 Bad Request)"""
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
    assert any(f["reason"] == "File data is empty." for f in body["data"]["files_failed"])

def test_upload_duplicate_content_different_names(test_db, api_gateway_event):
    """✅ Test uploading duplicate file contents but with different names (should return 207 Multi-Status)"""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Test Claim")
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    file_content = base64.b64encode(b"same_content").decode("utf-8")
    upload_payload = {
        "files": [
            {"file_name": "file1.jpg", "file_data": file_content},
            {"file_name": "file2.jpg", "file_data": file_content}
        ],
        "claim_id": str(test_claim.id)
    }
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 207
    assert len(body["data"]["files_uploaded"]) == 1
    assert len(body["data"]["files_failed"]) == 1

def test_upload_non_base64_data(test_db, api_gateway_event):
    """❌ Test uploading a file with non-base64 encoded data (should return 400 Bad Request)"""
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
    assert any(f["reason"] == "Invalid base64 encoding." for f in body["data"]["files_failed"])

def test_upload_large_file_exceeds_limit(test_db, api_gateway_event):
    """❌ Test uploading a file that exceeds the allowed size limit (should return 400 Bad Request)"""
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
    assert any(f["reason"] == "File exceeds size limit." for f in body["data"]["files_failed"])