"""
File Replacement Handler

This module handles replacing an existing file in the system. It verifies authentication,
validates request payloads, checks ownership, and updates the file in S3 and DynamoDB.

Features:
- Ensures only authorized users can replace their files.
- Validates the request body structure and required fields.
- Uploads the new file to S3 and updates metadata in DynamoDB.
- Standardizes error handling with structured API responses.

Example Usage:
    ```
    PUT /files/{file_id}
    Body: {
        "file_name": "new_image.jpg",
        "file_data": "base64_encoded_string",
        "s3_key": "uploads/user-123/old_file.jpg"
    }
    ```
"""

import os
import json
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from utils import response, dynamodb_utils

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

def lambda_handler(event, _context):
    """
    Handles requests to replace an existing file.

    This function performs the following steps:
    1. Ensures the user is authenticated.
    2. Parses and validates the request body.
    3. Retrieves file metadata from DynamoDB.
    4. Verifies that the user owns the file.
    5. Uploads the new file to S3.
    6. Updates metadata in DynamoDB.

    Args:
        event (dict): The API Gateway event payload.
        _context (dict): The AWS Lambda execution context (unused).

    Returns:
        dict: Standardized API response.
    """

    response_data = None  # ✅ Unified return point

    try:
        s3 = get_s3()
        files_table = get_files_table()

        # ✅ Step 1: Authenticate the user
        user_id = get_authenticated_user(event)
        if not user_id:
            return response.api_response(401)

        # ✅ Step 2: Extract and validate request data
        extracted = extract_request_data(event)
        if not isinstance(extracted, tuple):
            return response.api_response(400, message="Invalid request payload")

        file_id, body = extracted

        # ✅ If body contains an error message, return it
        if "message" in body:
            return response.api_response(400, message=body["message"])

        # ✅ Step 3: Retrieve file metadata
        file_data = files_table.get_item(Key={"id": file_id}).get("Item")
        if not file_data or file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")

        try:
            # ✅ Step 4: Upload new file to S3
            upload_file_to_s3(s3, file_data["s3_key"], body["file_data"])

            # ✅ Step 5: Update metadata in DynamoDB
            files_table.update_item(
                Key={"id": file_id},
                UpdateExpression="SET file_name = :name",
                ExpressionAttributeValues={":name": body["file_name"]},
            )

            return response.api_response(200, message="File replaced successfully")

        except (BotoCoreError, ClientError) as e:
            return response.api_response(500, message="AWS error", error_details=str(e))

    except (BotoCoreError, ClientError) as e:
        return response.api_response(500, message="AWS error", error_details=str(e))
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Unhandled exception: %s", str(e), exc_info=True)
        return response.api_response(500, message="Internal Server Error", error_details=str(e))

    return response_data  # ✅ Single return point at the end

# --- ✅ Helper Functions ---

def get_authenticated_user(event):
    """
    Extracts and returns the user ID if authentication is valid.

    Args:
        event (dict): The API Gateway event payload.

    Returns:
        str | None: The authenticated user ID, or None if missing.
    """
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    return claims.get("sub")

def extract_request_data(event):
    """
    Extracts and validates request data from the event.

    This function ensures the payload:
    - Contains a valid JSON body.
    - Includes all required fields: `file_name`, `file_data`, `s3_key`.
    - Uses a supported file format (.jpg, .jpeg, .png).

    Args:
        event (dict): The API Gateway event payload.

    Returns:
        tuple | dict | None:
            - (file_id, body) if valid.
            - {"message": error_message} if invalid.
            - None if critical fields are missing.
    """
    if "pathParameters" not in event or "id" not in event["pathParameters"]:
        return None

    file_id = event["pathParameters"]["id"]

    try:
        body = json.loads(event["body"]) if "body" in event and event["body"] else {}
    except (json.JSONDecodeError, KeyError):
        return None

    file_name = body.get("file_name")

    # ✅ Prioritize file format validation first
    if file_name and not file_name.lower().endswith((".jpg", ".jpeg", ".png")):
        return None, {"message": "Invalid file format"}

    required_fields = {"file_name", "file_data", "s3_key"}
    missing_fields = required_fields - body.keys()
    if missing_fields:
        return None, {"message": f"Missing required fields: {', '.join(missing_fields)}"}

    return file_id, body

def get_s3():
    """
    Initializes and returns an S3 client.

    Returns:
        boto3.client: S3 client instance.
    """
    return boto3.client("s3")

def get_files_table():
    """
    Retrieves the DynamoDB table used for file storage.

    Returns:
        boto3.Table: DynamoDB table instance.
    """
    return dynamodb_utils.get_dynamodb_table("FILES_TABLE")

def upload_file_to_s3(s3, s3_key, file_data_encoded):
    """
    Uploads a file to S3.

    Args:
        s3 (boto3.client): S3 client instance.
        s3_key (str): The S3 key where the file will be stored.
        file_data_encoded (str): Base64-encoded file content.

    Raises:
        BotoCoreError: If there is an issue with AWS SDK.
        ClientError: If there is an AWS S3-specific error.
    """
    file_binary = bytes(file_data_encoded, "utf-8")  # Decode from base64
    s3.put_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=s3_key, Body=file_binary)
