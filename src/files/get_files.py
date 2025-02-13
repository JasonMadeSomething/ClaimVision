import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key
from utils import response

def decimal_to_int(obj):
    """Convert Decimal types to int for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj)
    return obj

def get_files_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))

def lambda_handler(event, context):
    """Retrieve paginated list of files for the authenticated user"""
    try:
        files_table = get_files_table()
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        query_params = event.get("queryStringParameters", {}) or {}

        limit = int(query_params.get("limit", 10))
        last_evaluated_key = query_params.get("last_key")

        query_kwargs = {
            "IndexName": "UserIdIndex",
            "KeyConditionExpression": Key("user_id").eq(user_id),
            "Limit": limit,
        }

        if last_evaluated_key:
            try:
                query_kwargs["ExclusiveStartKey"] = json.loads(last_evaluated_key)
            except json.JSONDecodeError:
                return response.api_response(
                    400,
                    message="Invalid pagination key format"
                )

        files_response = files_table.query(**query_kwargs)

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

    except Exception as e:
        return response.api_response(
            400,
            message="Bad request",
            error_details=str(e)
        )
