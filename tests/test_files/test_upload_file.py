# pylint: disable=unused-argument
"""✅ Test uploading a valid file successfully"""
import json
from unittest.mock import patch
from test_data.files_data import (
    test_upload_payload,
    test_large_file_payload,
    test_invalid_file_payload,
    test_missing_fields_payload,
    duplicate_payload,
)
from files.upload_file import lambda_handler


# ✅ SUCCESS: Basic File Upload
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_file_success(mock_dynamodb, mock_s3, api_gateway_event):
    """✅ Test uploading a valid file successfully"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)
    mock_table = mock_dynamodb.return_value
    mock_table.put_item.return_value = {}
    mock_s3.return_value.put_object.return_value = {}

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 200
    assert len(body["data"]["files_uploaded"]) > 0  # Ensure files exist
    assert any(f["file_name"] == "test.jpg" for f in body["data"]["files_uploaded"])

# ✅ SUCCESS: Upload Multiple Files
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_multiple_files(mock_dynamodb, mock_s3, api_gateway_event):
    """✅ Test uploading multiple valid files"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)
    mock_table = mock_dynamodb.return_value
    mock_table.put_item.return_value = {}
    mock_s3.return_value.put_object.return_value = {}

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 200
    assert len(body["data"]["files_uploaded"]) == 2  # Expecting 2 files in the response


# ✅ SUCCESS: Upload Large File (5MB limit check)
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_large_file(mock_dynamodb, mock_s3, api_gateway_event):
    """✅ Test uploading a large file (should pass if <=5MB)"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_large_file_payload)
    mock_table = mock_dynamodb.return_value
    mock_table.put_item.return_value = {}
    mock_s3.return_value.put_object.return_value = {}

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 200
    assert body["data"]["files_uploaded"][0]["file_name"] == "large_image.jpg"


# ❌ FAILURE: Missing `file_name`
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_missing_filename(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test missing `file_name` field"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_missing_fields_payload)
    ## Act
    response = lambda_handler(event, {})
    ## Assert
    assert response["statusCode"] == 400
    assert "Missing required field(s)" in json.loads(response["body"])["message"]


# ❌ FAILURE: Invalid File Type
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_invalid_file_type(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test uploading an invalid file type (e.g., `.exe`)"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_invalid_file_payload)
    ## Act
    response = lambda_handler(event, {})
    ## Assert
    assert response["statusCode"] == 400
    assert "No valid files uploaded" in json.loads(response["body"])["message"]


# ❌ FAILURE: Empty Payload
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_empty_payload(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test empty payload should return 400"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body="{}")
    ## Act
    response = lambda_handler(event, {})
    ## Assert
    assert response["statusCode"] == 400
    assert "Missing required field(s): files" in json.loads(response["body"])["message"]


# ❌ FAILURE: Unauthorized Upload (No Auth Header)
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_unauthorized(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test uploading without authentication (should return 401)"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)
    event["headers"].pop("Authorization", None)  # Remove auth header
    event["requestContext"].pop("authorizer", None)  # Simulate unauthorized request
    ## Act
    response = lambda_handler(event, {})
    ## Assert
    assert response["statusCode"] == 401
    assert "Unauthorized" in json.loads(response["body"])["message"]


# ❌ FAILURE: Duplicate File Upload
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_duplicate_file_in_batch(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test uploading duplicate files within the same request (should return 400)"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=duplicate_payload)
    ## Act
    response = lambda_handler(event, {})
    ## Assert
    assert response["statusCode"] == 400
    assert "Duplicate file" in json.loads(response["body"])["message"]



# ❌ FAILURE: DynamoDB Write Error
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_dynamodb_error(mock_dynamodb, mock_s3, api_gateway_event):
    """❌ Test stopping all uploads on DynamoDB failure (should return 500)"""
    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)
    mock_s3.return_value.put_object.return_value = None  # S3 works
    mock_table = mock_dynamodb.return_value
    mock_table.put_item.side_effect = Exception("DynamoDB Failure")  # ❌ Simulated DB failure

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 500
    assert "DynamoDB Failure" in body["error_details"]


# ❌ FAILURE: S3 Upload Error
@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_s3_error(mock_dynamodb, mock_s3, api_gateway_event):
    """⚠️ Test case where some files succeed and some fail (should return 500)
        S3 Failures preclude metadata creation and therefore the entire request fails.
    """

    ## Arrange
    event = api_gateway_event(http_method="POST", body=test_upload_payload)
    mock_s3.return_value.put_object.side_effect = [
        None,
        Exception("S3 Failure")
    ]  # First succeeds, second fails

    ## Act
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    ## Assert
    assert response["statusCode"] == 500
    assert "S3 Failure" in body["error_details"]


@patch("files.upload_file.get_s3")
@patch("files.upload_file.get_files_table")
def test_upload_mixed_file_types(mock_dynamodb, mock_s3, api_gateway_event):
    """❌✅ Test uploading mixed valid and invalid file types"""
    ## Arrange
    mixed_payload = {
        "files": [
            {"file_name": "valid.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
            {"file_name": "invalid.exe", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
            {"file_name": "valid2.png", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}
        ]
    }

    event = api_gateway_event(http_method="POST", body=json.dumps(mixed_payload))
    ## Act
    response = lambda_handler(event, {})

    body = json.loads(response["body"])
    ## Assert
    # ✅ Expect only the valid files to be uploaded
    assert response["statusCode"] == 207
    assert len(body["data"]["files_uploaded"]) == 2
    assert len(body["data"]["files_failed"]) == 1
    assert body["data"]["files_failed"][0]["file_name"] == "invalid.exe"
    assert body["data"]["files_failed"][0]["reason"] == "Unsupported file format"
