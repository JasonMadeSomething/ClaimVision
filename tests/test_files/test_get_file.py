"""✅ Test retrieving a single file"""
import json
from unittest.mock import patch
from test_data.files_data import test_files
from files.get_file import lambda_handler

@patch("files.get_file.get_files_table")
def test_get_file_success(mock_dynamodb, api_gateway_event):
    """✅ Test retrieving a single file successfully"""

    event = api_gateway_event(
        http_method="GET",
        path_params={"id": "file-1"},
        auth_user="user-123",
    )
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {"Item": test_files[0]}

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["id"] == "file-1"

@patch("files.get_file.get_files_table")
def test_get_file_not_found(mock_dynamodb, api_gateway_event):
    """❌ Test retrieving a non-existent file"""

    event = api_gateway_event(
        http_method="GET",
        path_params={"id": "file-99"},
        auth_user="user-123",
    )
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {}

    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
