import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import BotoCoreError, ClientError
from ..utils import response as response

dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))

def decimal_to_int(obj):
    """Convert Decimal types to int for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj)
    return obj

def lambda_handler(event, context):
    """Retrieve metadata of a single file"""
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id = event["pathParameters"]["id"]

        file_response = files_table.get_item(Key={"id": file_id})
        file_data = file_response.get("Item")

        if not file_data:
            return response.api_response(404, message="File not found", missing_fields=["id"])

        if file_data["user_id"] != user_id:
            return response.api_response(404, message="File not found")

        return response.api_response(200, message="File found", data=file_data)

    except (BotoCoreError, ClientError) as e:
        return response.api_response(
            500,
            message="AWS error",
            details=str(e)
        )

    except Exception as e:
        return response.api_response(
            400,
            message="Bad request",
            error_details=str(e)
        )
