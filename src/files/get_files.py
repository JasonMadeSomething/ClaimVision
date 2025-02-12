import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))

def decimal_to_int(obj):
    """Convert Decimal types to int for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj)
    return obj

def lambda_handler(event, context):
    """Retrieve paginated list of files for the authenticated user"""
    try:
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
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid pagination key format"})
                }

        response = files_table.query(**query_kwargs)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "files": response.get("Items", []),
                "last_key": response.get("LastEvaluatedKey") if "LastEvaluatedKey" in response else None
            }, default=decimal_to_int)
        }

    except (BotoCoreError, ClientError) as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "AWS error", "details": str(e)})
        }

    except Exception as e:
        return response.api_response(
            400,
            message="Bad request",
            error_details=str(e)
        )
