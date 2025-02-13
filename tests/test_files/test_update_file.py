"""✅ Test updating a file"""
import json
from unittest.mock import patch
from test_data.files_data import test_update_payload, test_files
from files.update_file_metadata import lambda_handler

@patch("files.update_file_metadata.get_files_table")
def test_update_file_success(mock_dynamodb, api_gateway_event):
    """✅ Test updating file metadata successfully"""

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": "file-1"},
        body=test_update_payload
    )
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {"Item": test_files[0]}  # ✅ Mock file exists
    mock_table.update_item.return_value = {}

    response = lambda_handler(event, {})
    print(response)
    assert response["statusCode"] == 200
    assert response["body"] is not None

@patch("files.update_file_metadata.get_files_table")
def test_update_file_not_found(mock_dynamodb, api_gateway_event):
    """❌ Test updating a non-existent file"""

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": "file-99"},
        body=test_update_payload,
        auth_user="user-123")
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {}  # No file found

    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
    assert "File Not Found" in json.loads(response["body"])["message"]

@patch("files.update_file_metadata.get_files_table")
def test_update_file_unauthorized(mock_dynamodb, api_gateway_event):
    """❌ Test updating another user's file (unauthorized)"""

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": "file-1"},
        body=test_update_payload,
        auth_user="user-999"
    )
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {"Item": test_files[0]}  # File exists but different user

    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
    assert "File Not Found" in json.loads(response["body"])["message"]

@patch("files.update_file_metadata.get_files_table")
def test_update_file_invalid_payload(mock_dynamodb, api_gateway_event):
    """❌ Test updating a file with an invalid payload"""

    invalid_payload = {}  # Missing required fields
    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": "file-1"},
        body=invalid_payload,
        auth_user="user-123")
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {"Item": test_files[0]}

    response = lambda_handler(event, {})
    print(response)
    assert response["statusCode"] == 400
    assert "Missing required field(s)" in response["body"]

@patch("files.update_file_metadata.get_files_table")
def test_update_file_dynamodb_error(mock_dynamodb, api_gateway_event):
    """❌ Test handling of DynamoDB errors during update"""

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": "file-1"},
        body=test_update_payload,
        auth_user="user-123")
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {"Item": test_files[0]}
    mock_table.update_item.side_effect = Exception("DynamoDB error")  # Simulate AWS error

    response = lambda_handler(event, {})
    assert response["statusCode"] == 500
    print(response)
    assert "DynamoDB error" in json.loads(response["body"])["error_details"]
