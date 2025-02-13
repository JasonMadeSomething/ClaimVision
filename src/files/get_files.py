"""
File Retrieval Handler

This module handles retrieving a paginated list of files for the authenticated user.
It queries the DynamoDB `FilesTable` using an index on `user_id`, supports pagination,
and returns the user's files in a standardized API response.

Features:
- Authenticates the user and fetches only their files.
- Supports pagination via `limit` and `last_key` query parameters.
- Converts DynamoDB `Decimal` values into integers for JSON serialization.
- Handles potential AWS or user input errors gracefully.

Example Usage:
    ```
    GET /files?limit=10&last_key=<encoded_key>
    ```
"""

import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key
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
    Handles retrieving a paginated list of files for the authenticated user.

    This function:
    1. Extracts the authenticated user ID from the request.
    2. Parses pagination parameters (`limit`, `last_key`).
    3. Queries DynamoDB for files belonging to the user.
    4. Returns paginated results, ensuring only the user's files are included.

    Query Parameters:
        - `limit` (int, optional): Maximum number of files per page (default: 10).
        - `last_key` (str, optional): Pagination key for retrieving the next page.

    Args:
        event (dict): The API Gateway event payload.
        _context (dict): The AWS Lambda execution context (unused).

    Returns:
        dict: Standardized API response containing the list of files and pagination key.
    """
    try:
        files_table = get_files_table()
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        query_params = event.get("queryStringParameters", {}) or {}

        # ✅ Step 1: Parse query parameters
        limit = int(query_params.get("limit", 10))
        last_evaluated_key = query_params.get("last_key")

        query_kwargs = {
            "IndexName": "UserIdIndex",
            "KeyConditionExpression": Key("user_id").eq(user_id),
            "Limit": limit,
        }

        # ✅ Step 2: Handle pagination
        if last_evaluated_key:
            try:
                query_kwargs["ExclusiveStartKey"] = json.loads(last_evaluated_key)
            except json.JSONDecodeError:
                return response.api_response(400, message="Invalid pagination key format")

        # ✅ Step 3: Query DynamoDB
        files_response = files_table.query(**query_kwargs)

        # ✅ Step 4: Ensure only files belonging to the user are returned
        filtered_files = [file for file in files_response.get("Items", []) if file["user_id"] == user_id]

        return response.api_response(
            200,
            message="Files retrieved successfully",
            data={
                "files": filtered_files,
                "last_key": files_response.get("LastEvaluatedKey") if "LastEvaluatedKey" in files_response else None
            }
        )

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
