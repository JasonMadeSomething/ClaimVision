import json
import pytest
from unittest.mock import patch
from test_data.files_data import test_files, expected_files_response
from files.get_files import lambda_handler

@patch("files.get_files.get_files_table")
def test_get_files(mock_dynamodb, api_gateway_event):
    """✅ Test retrieving files for a user"""

    event = api_gateway_event(http_method="GET", query_params={"limit": "10"})
    mock_table = mock_dynamodb.return_value
    mock_table.query.return_value = {"Items": test_files}

    response = lambda_handler(event, {})

    assert response["statusCode"] == 200
    expected_body = expected_files_response["body"]
    if isinstance(expected_body, str):  # Ensure we only parse if it's a string
        expected_body = json.loads(expected_body)

    assert json.loads(response["body"]) == expected_body


@patch("files.get_files.get_files_table")
def test_get_files_pagination(mock_dynamodb, api_gateway_event):
    """✅ Test retrieving files with pagination"""
    
    event = api_gateway_event(http_method="GET", query_params={"limit": "1", "last_key": '{"id": "file-1"}'})
    mock_table = mock_dynamodb.return_value
    mock_table.query.return_value = {"Items": test_files[:1], "LastEvaluatedKey": "file-2"}

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    print(body)

    assert response["statusCode"] == 200
    assert body["data"]["files"][0]["id"] == "file-1"
    assert body["data"]["last_key"] == "file-2"

@patch("files.get_files.get_files_table")
def test_get_files_empty(mock_dynamodb, api_gateway_event):
    """❌ Test retrieving files when none exist"""

    event = api_gateway_event(http_method="GET", query_params={"limit": "10"})
    mock_table = mock_dynamodb.return_value
    mock_table.query.return_value = {"Items": []}

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["files"] == []
