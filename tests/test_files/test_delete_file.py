import json
import pytest
from unittest.mock import patch
from test_data.files_data import test_files
from files.delete_file import lambda_handler


@patch("files.delete_file.get_s3")
@patch("files.delete_file.get_files_table")
def test_delete_file_success(mock_dynamodb, mock_s3, api_gateway_event):
    """✅ Test deleting a file that belongs to the user"""

    event = api_gateway_event(
        http_method="DELETE",
        path_params={"id": "file-1"},
        auth_user="user-123",
    )

    # ✅ Mock DynamoDB table (return a valid file)
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {"Item": test_files[0]}  # File exists
    mock_table.delete_item.return_value = {}

    # ✅ Mock S3 deletion
    mock_s3.return_value.delete_object.return_value = {}

    # ✅ Invoke Lambda
    response = lambda_handler(event, {})
    # ✅ Assertions

    assert response["statusCode"] == 204  # No Content
    mock_table.get_item.assert_called_once_with(Key={"id": "file-1"})
    mock_table.delete_item.assert_called_once_with(Key={"id": "file-1"})
    mock_s3.return_value.delete_object.assert_called_once()

@patch("files.delete_file.get_s3")
@patch("files.delete_file.get_files_table")
def test_delete_file_not_found(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test deleting a file that does not exist"""

    event = api_gateway_event(
        http_method="DELETE",
        path_params={"id": "file-999"},
        auth_user="user-123",
    )

    # ✅ Mock DynamoDB table (file does NOT exist)
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {}  # Empty response

    # ✅ Invoke Lambda
    response = lambda_handler(event, {})
    print(response["body"])
    # ✅ Assertions
    assert response["statusCode"] == 404  # Not Found
    mock_table.get_item.assert_called_once_with(Key={"id": "file-999"})
    mock_table.delete_item.assert_not_called()
    mock_s3.return_value.delete_object.assert_not_called()

@patch("files.delete_file.get_s3")
@patch("files.delete_file.get_files_table")
def test_delete_file_unauthorized(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test deleting a file that belongs to a different user"""

    event = api_gateway_event(
        http_method="DELETE",
        path_params={"id": "file-1"},
        auth_user="user-999",
    )

    # ✅ Mock DynamoDB table (return a file owned by someone else)
    mock_table = mock_dynamodb.return_value
    mock_table.get_item.return_value = {"Item": test_files[0]}  # File exists, but wrong user

    # ✅ Invoke Lambda
    response = lambda_handler(event, {})

    # ✅ Assertions
    assert response["statusCode"] == 404  # Not Found
    mock_table.get_item.assert_called_once_with(Key={"id": "file-1"})
    mock_table.delete_item.assert_not_called()
    mock_s3.return_value.delete_object.assert_not_called()
