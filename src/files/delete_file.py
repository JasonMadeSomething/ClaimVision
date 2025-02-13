"""
File Deletion Handler

This module handles deleting a file from both AWS S3 and DynamoDB.
It ensures the authenticated user owns the file before allowing deletion.

Features:
- Authenticates the user and fetches only their files.
- Deletes the file from AWS S3.
- Removes file metadata from DynamoDB.
- Returns standardized API responses.

Example Usage:
    ```
    DELETE /files/{file_id}
    ```
"""

import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from utils import response

def get_files_table():
    """
    Retrieves the DynamoDB table for storing file metadata.

    Returns:
        boto3.Table: DynamoDB table instance.
    """
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))

def get_s3():
    """
    Initializes and returns an S3 client.

    Returns:
        boto3.client: S3 client instance.
    """
    return boto3.client("s3")

def lambda_handler(event, _context):
    """
    Handles deleting a file.

    This function:
    1. Extracts the authenticated user ID from the request.
    2. Retrieves the file metadata from DynamoDB.
    3. Ensures the user owns the file.
    4. Deletes the file from S3.
    5. Removes the file metadata from DynamoDB.

    Path Parameters:
        - `file_id` (str): The unique identifier of the file.

    Args:
        event (dict): The API Gateway event payload.
        _context (dict): The AWS Lambda execution context (unused).

    Returns:
        dict: Standardized API response confirming deletion.
    """
    s3_bucket_name = os.getenv("S3_BUCKET_NAME")

    try:
        s3 = get_s3()
        files_table = get_files_table()

        # ✅ Step 1: Authenticate the user
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        file_id = event["pathParameters"]["id"]

        # ✅ Step 2: Fetch file metadata
        file_response = files_table.get_item(Key={"id": file_id})
        file_data = file_response.get("Item")

        # ✅ Step 3: Ensure the file exists and is owned by the user
        if not file_data or file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")

        # ✅ Step 4: Extract file name and delete from S3
        file_name = file_data["file_name"]
        s3_key = f"uploads/{user_id}/{file_name}"
        s3.delete_object(Bucket=s3_bucket_name, Key=s3_key)

        # ✅ Step 5: Delete metadata from DynamoDB
        files_table.delete_item(Key={"id": file_id})

        return response.api_response(204, message="File deleted successfully", data={"file_id": file_id})

    except (BotoCoreError, ClientError) as e:
        return response.api_response(500, message="Internal Server Error", error_details=str(e))

    except Exception as e: # pylint: disable=broad-except
        return response.api_response(400, message="Bad Request", error_details=str(e))
