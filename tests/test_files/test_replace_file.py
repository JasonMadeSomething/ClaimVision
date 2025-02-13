# pylint: disable=unused-argument
"""✅ Test replacing an existing file"""
import json
from unittest.mock import patch
from test_data.files_data import test_replace_payload
from files.replace_file import lambda_handler

@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_success(mock_dynamodb, mock_s3, api_gateway_event):
    """✅ Test replacing an existing file"""
    
    event = api_gateway_event(http_method="PUT", path_params={"id": "file-1"}, body=test_replace_payload, auth_user="user-123")
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {
        "Item": {
            "id": "file-1",
            "user_id": "user-123",
            "file_name": "test.jpg",
            "s3_key": "uploads/user-123/file-1.jpg"
        }
    }  # Simulate file exists
    mock_table.update_item.return_value = {}
    mock_s3.return_value.put_object.return_value = {}

    response = lambda_handler(event, {})
    assert response["statusCode"] == 200

@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_not_found(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test replacing a non-existent file (should return 404)"""

    event = api_gateway_event(
        http_method="PUT", 
        path_params={"id": "file-99"}, 
        body=test_replace_payload, 
        auth_user="user-123")
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {}  # No file found

    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
    assert "File Not Found" in json.loads(response["body"])["message"]

@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_unauthorized(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test replacing a file owned by another user (should return 404 for security)"""

    event = api_gateway_event(
        http_method="PUT", 
        path_params={"id": "file-1"}, 
        auth_user="user-999", 
        body=test_replace_payload)
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {
        "Item": {
            "id": "file-1",
            "user_id": "user-123",
            "file_name": "test.jpg",
            "s3_key": "uploads/user-123/file-1.jpg"
        }
    }  # File exists, but wrong user

    response = lambda_handler(event, {})
    assert response["statusCode"] == 404

@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_invalid_format(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test replacing a file with an invalid format (should return 400)"""

    invalid_payload = test_replace_payload.copy()  # ✅ This correctly creates a copy of the dict
    invalid_payload["file_name"] = "test.exe"  # Unsupported format
    event = api_gateway_event(
        http_method="PUT",
        path_params={"id": "file-1"},
        body=invalid_payload,
        auth_user="user-123"
    )

    response = lambda_handler(event, {})
    assert response["statusCode"] == 400
    assert "Invalid file format" in json.loads(response["body"])["message"]

@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_empty_payload(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test replacing a file with an empty payload (should return 400)"""

    event = api_gateway_event(
        http_method="PUT", 
        path_params={"id": "file-1"}, 
        body="{}", 
        auth_user="user-123")

    response = lambda_handler(event, {})
    assert response["statusCode"] == 400
    assert "Missing required field(s)" in json.loads(response["body"])["message"]

@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_dynamodb_error(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test handling a DynamoDB failure (should return 500)"""

    event = api_gateway_event(
        http_method="PUT", 
        path_params={"id": "file-1"}, 
        body=test_replace_payload, 
        auth_user="user-123")
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {
        "Item": {
            "id": "file-1",
            "user_id": "user-123",
            "s3_key": "uploads/user-123/file-1.jpg"  # ✅ Add missing s3_key
        }
    }
    mock_table.update_item.side_effect = Exception("DynamoDB Failure")  # Simulated DB failure

    response = lambda_handler(event, {})
    assert response["statusCode"] == 500
    assert "DynamoDB Failure" in json.loads(response["body"])["error_details"]


@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_s3_failure(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test handling an S3 upload failure (should return 500)"""

    event = api_gateway_event(
        http_method="PUT", 
        path_params={"id": "file-1"}, 
        body=test_replace_payload, 
        auth_user="user-123")
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {
        "Item": {
            "id": "file-1",
            "user_id": "user-123",
            "s3_key": "uploads/user-123/file-1.jpg"  # ✅ Add missing s3_key
        }
    }
    mock_s3.return_value.put_object.side_effect = Exception("S3 Failure")  # Simulated S3 failure

    response = lambda_handler(event, {})
    assert response["statusCode"] == 500
    assert "S3 Failure" in json.loads(response["body"])["error_details"]

@patch("files.replace_file.get_s3")
@patch("files.replace_file.get_files_table")
def test_replace_file_no_auth(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test replacing a file with no authentication (should return 401)"""

    event = api_gateway_event(
        http_method="PUT", 
        path_params={"id": "file-1"}, 
        auth_user=None, 
        body=test_replace_payload)

    response = lambda_handler(event, {})
    assert response["statusCode"] == 401
    assert "Unauthorized" in json.loads(response["body"])["message"]
