"""
File Metadata Retrieval Handler

This module handles retrieving metadata for a single file. It ensures the authenticated
user has access to the file before returning its metadata.

Features:
- Authenticates the user and fetches only their file.
- Converts DynamoDB `Decimal` values into integers for JSON serialization.
- Handles potential AWS errors gracefully.
- Returns standardized API responses.

Example Usage:
    ```
    GET /files/{file_id}
    ```
"""

import os
from decimal import Decimal
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from utils import response

def decimal_to_int(obj):
    """
    Converts Decimal values to integers for JSON serialization.

    Args:
        obj (Any): The object to check and convert.

    Returns:
        int | Any: The converted integer if `obj` is a Decimal, otherwise the original object.
    """
    if isinstance(obj, Decimal):
        return int(obj)
    return obj

def get_files_table():
    """
    Retrieves the DynamoDB table for storing file metadata.

    Returns:
        boto3.Table: DynamoDB table instance.
    """
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))

def lambda_handler(event, _context):
    """
    Retrieves metadata for a single file.

    This function:
    1. Extracts the authenticated user ID from the request.
    2. Retrieves the file from DynamoDB using the file ID.
    3. Ensures that the requesting user owns the file.
    4. Returns the file metadata if the user has access.

    Path Parameters:
        - `file_id` (str): The unique identifier of the file.

    Args:
        event (dict): The API Gateway event payload.
        _context (dict): The AWS Lambda execution context (unused).

    Returns:
        dict: Standardized API response containing the file metadata.
    """
    try:
        files_table = get_files_table()
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id = event["pathParameters"]["id"]

        # ✅ Step 1: Retrieve file from DynamoDB
        file_response = files_table.get_item(Key={"id": file_id})
        file_data = file_response.get("Item")

        # ✅ Step 2: Ensure file exists
        if not file_data:
            return response.api_response(404, message="File Not Found")

        # ✅ Step 3: Ensure user owns the file
        if file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")

        return response.api_response(200, message="File found", data=file_data)

    except (BotoCoreError, ClientError) as e:
        return response.api_response(
            500,
            message="AWS error",
            error_details=str(e)
        )

    except Exception as e:  # pylint: disable=broad-except
        return response.api_response(
            400,
            message="Bad request",
            error_details=str(e)
        )
