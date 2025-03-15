import json
import uuid
import pytest
import base64
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from models import File, Household, User
from files.replace_file import lambda_handler

def test_replace_file_success(test_db, api_gateway_event, seed_file):
    """ Test successful replacement of an existing file."""
    file_id, user_id, _ = seed_file
    replace_payload = {"file_name": "new.jpg", "file_data": base64.b64encode(b"newcontent").decode("utf-8")}

    with patch("files.replace_file.upload_to_s3") as mock_s3_upload:
        event = api_gateway_event(http_method="PUT", path_params={"id": str(file_id)}, body=json.dumps(replace_payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 200
        mock_s3_upload.assert_called_once()

def test_replace_file_not_found(test_db, api_gateway_event, seed_file):
    """ Test replacing a non-existent file (should return 404)"""
    _, user_id, _ = seed_file

    with patch("files.replace_file.upload_to_s3") as mock_s3_upload:
        event = api_gateway_event(http_method="PUT", path_params={"id": str(uuid.uuid4())}, body=json.dumps({"file_name": "new.jpg", "file_data": base64.b64encode(b"newcontent").decode("utf-8")}), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)
        print(response)
        assert response["statusCode"] == 404
        mock_s3_upload.assert_not_called()

def test_replace_file_invalid_format(api_gateway_event, test_db, seed_file):
    """ Test replacing a file with an invalid format (should return 400)"""
    file_id, user_id, _ = seed_file
    payload = {"file_name": "invalid.exe", "file_data": base64.b64encode(b"invalid").decode("utf-8")}

    with patch("files.replace_file.upload_to_s3") as mock_s3_upload:
        event = api_gateway_event(http_method="PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 400
        assert "error_details" in json.loads(response["body"])
        assert "Invalid file format" in json.loads(response["body"])["error_details"]
        mock_s3_upload.assert_not_called()

def test_replace_file_empty_payload(api_gateway_event, test_db, seed_file):
    """ Test replacing a file with an empty payload (should return 400)"""
    file_id, user_id, _ = seed_file

    with patch("files.replace_file.upload_to_s3") as mock_s3_upload:
        event = api_gateway_event(http_method="PUT", path_params={"id": str(file_id)}, body="{}", auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 400
        mock_s3_upload.assert_not_called()

def test_replace_file_s3_failure(api_gateway_event, test_db, seed_file):
    """ Test handling an S3 upload failure (should return 500)"""
    file_id, user_id, _ = seed_file
    payload = {"file_name": "valid.jpg", "file_data": base64.b64encode(b"valid").decode("utf-8")}

    with patch("files.replace_file.upload_to_s3", side_effect=Exception("S3 Failure")) as mock_s3_upload:
        event = api_gateway_event(http_method="PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 500
        mock_s3_upload.assert_called_once()

def test_replace_file_no_auth(api_gateway_event, test_db, seed_file):
    """ Test replacing a file with no authentication provided (should return 401)"""
    file_id, _, _ = seed_file
    payload = {
        "file_name": "new.jpg",
        "file_data": base64.b64encode(b"newcontent").decode("utf-8")
    }

    event = api_gateway_event(
        http_method="PUT",
        path_params={"id": str(file_id)},
        body=json.dumps(payload),
        auth_user=None  # No authentication provided
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    assert response["statusCode"] == 401
    assert "Unauthorized" in body["message"]
    assert "error_details" in body
    assert "Unauthorized" in body["error_details"]

def test_replace_file_database_failure(api_gateway_event, seed_file):
    """ Test handling a database error during file replacement (should return 500)"""
    file_id, user_id, _ = seed_file
    payload = {
        "file_name": "new.jpg",
        "file_data": base64.b64encode(b"newcontent").decode("utf-8")
    }

    with patch("utils.lambda_utils.get_db_session", side_effect=SQLAlchemyError("DB Failure")):
        event = api_gateway_event(
            http_method="PUT",
            path_params={"id": str(file_id)},
            body=json.dumps(payload),
            auth_user=str(user_id)
        )

        response = lambda_handler(event, {})
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error_details" in body
        assert "Failed to establish database connection" in body["error_details"]

def test_replace_file_invalid_uuid(api_gateway_event, test_db, seed_file):
    """ Test handling invalid UUID format (should return 400)"""
    _, user_id, _ = seed_file
    payload = {"file_name": "valid.jpg", "file_data": base64.b64encode(b"valid").decode("utf-8")}

    with patch("files.replace_file.upload_to_s3") as mock_s3_upload:
        event = api_gateway_event(http_method="PUT", path_params={"id": "invalid-uuid"}, body=json.dumps(payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])

        assert response["statusCode"] == 400
        assert "error_details" in body
        assert "Invalid file ID" in body["error_details"]
        mock_s3_upload.assert_not_called()

def test_replace_file_too_large(api_gateway_event, test_db, seed_file):
    """ Test replacing a file with a file that exceeds the allowed size limit."""
    file_id, user_id, _ = seed_file
    large_file_data = base64.b64encode(b"a" * (10 * 1024 * 1024 + 1)).decode("utf-8")  # 10MB + 1 byte
    payload = {"file_name": "large.jpg", "file_data": large_file_data}

    event = api_gateway_event("PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error_details" in body
    assert "File size exceeds the allowed limit" in body["error_details"]

def test_replace_file_empty_file(api_gateway_event, test_db, seed_file):
    """ Test replacing a file with an empty file."""
    file_id, user_id, _ = seed_file
    payload = {"file_name": "empty.jpg", "file_data": base64.b64encode(b"").decode("utf-8")}

    event = api_gateway_event("PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error_details" in body
    assert "File data is empty" in body["error_details"]

def test_replace_file_no_name(api_gateway_event, test_db, seed_file):
    """ Test replacing a file with no file name."""
    file_id, user_id, _ = seed_file
    payload = {"file_name": "", "file_data": base64.b64encode(b"valid").decode("utf-8")}

    event = api_gateway_event("PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error_details" in body
    assert "File name is required" in body["error_details"]

def test_replace_file_invalid_extension(api_gateway_event, test_db, seed_file):
    """ Test replacing a file with an invalid extension."""
    file_id, user_id, _ = seed_file
    payload = {"file_name": "invalid.txt", "file_data": base64.b64encode(b"valid").decode("utf-8")}

    event = api_gateway_event("PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error_details" in body
    assert "Invalid file format" in body["error_details"]

def test_replace_file_single_upload(api_gateway_event, test_db, seed_file):
    """ Test that file replacements are 1:1 and do not allow multiple uploads."""
    file_id, user_id, _ = seed_file
    payload = {
        "files": [
            {"file_name": "valid1.jpg", "file_data": base64.b64encode(b"valid1").decode("utf-8")},
            {"file_name": "valid2.jpg", "file_data": base64.b64encode(b"valid2").decode("utf-8")}
        ]
    }

    event = api_gateway_event("PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    assert response["statusCode"] == 400
    assert "error_details" in body
    assert "Only one file can be replaced at a time" in body["error_details"]


def test_replace_file_invalid_base64(api_gateway_event, test_db, seed_file):
    """Test replacing a file with non-base64 encoded data (should return 400 Bad Request)"""
    file_id, user_id, _ = seed_file
    payload = {"file_name": "invalid.png", "file_data": "cheese"}

    event = api_gateway_event("PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error_details" in body
    assert "Invalid base64 encoding" in body["error_details"]

def test_replace_file_no_extension(api_gateway_event, test_db, seed_file):
    """Test replacing a file with no extension (should return 400 Bad Request)"""
    file_id, user_id, _ = seed_file
    payload = {"file_name": "invalid", "file_data": base64.b64encode(b"valid").decode("utf-8")}

    event = api_gateway_event("PUT", path_params={"id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error_details" in body
    assert "Invalid file format" in body["error_details"]