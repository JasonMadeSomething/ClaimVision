"""
File Metadata Update Handler

This module provides functionality for updating metadata fields of a file in the system.
It ensures user authentication, validates request payloads, and updates allowed metadata
fields in the database.

Features:
- Supports PATCH updates for specific metadata fields.
- Ensures only allowed fields can be modified.
- Handles authentication and authorization checks.
- Returns standardized API responses.

Example Usage:
    ```
    PATCH /files/{file_id}
    Body: {
        "description": "Updated description",
        "labels": ["label1", "label2"],
        "associated_claim_id": "claim-123"
    }
    ```
"""
import os
import json
import boto3
from utils import response

def get_s3():
    """
    Initialize and return an S3 client.

    Returns:
        boto3.client: S3 client instance.
    """
    return boto3.client("s3")

def get_files_table():
    """
    Retrieve the DynamoDB table used for storing file metadata.

    Returns:
        boto3.Table: DynamoDB table instance.
    """
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))

def lambda_handler(event, _context):
    """
    Handles PATCH requests to update metadata fields of a file.

    This function performs the following steps:
    1. Ensures the user is authenticated.
    2. Parses and validates the request body.
    3. Fetches the existing file metadata from DynamoDB.
    4. Ensures the user owns the file before making modifications.
    5. Updates allowed metadata fields.

    Allowed fields for update:
    - `description`: A text description of the file.
    - `labels`: A list of labels/tags associated with the file.
    - `associated_claim_id`: A reference to an insurance claim ID.

    Args:
        event (dict): The API Gateway event payload.
        _context (dict): The AWS Lambda execution context. (unused)

    Returns:
        dict: Standardized API response.
    """

    try:
        # ✅ Step 1: Authenticate the user
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id = event["pathParameters"]["id"]

        # ✅ Step 2: Validate request body
        try:
            if not event.get("body"):
                return response.api_response(400, message="Missing required field(s)", missing_fields=["body"])
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return response.api_response(400, message="Invalid JSON format")

        if not body:
            return response.api_response(400, message="Missing required field(s)")

        files_table = get_files_table()

        # ✅ Step 3: Fetch the existing file metadata
        file_response = files_table.get_item(Key={"id": file_id})
        file_data = file_response.get("Item")

        if not file_data or file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")

        # ✅ Step 4: Prepare update expression
        update_expression = "SET "
        expression_attribute_values = {}

        allowed_fields = ["description", "labels", "associated_claim_id"]

        for key in allowed_fields:
            if key in body:
                update_expression += f"{key} = :{key}, "
                expression_attribute_values[f":{key}"] = body[key]

        if not expression_attribute_values:
            return response.api_response(400, message="No valid fields to update")

        update_expression = update_expression.rstrip(", ")

        # ✅ Step 5: Perform the update in DynamoDB
        files_table.update_item(
            Key={"id": file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

        return response.api_response(200, message="File metadata updated successfully", data={"file_id": file_id})

    except Exception as e: # pylint: disable=broad-except
        return response.api_response(500, message="Internal Server Error", error_details=str(e))
