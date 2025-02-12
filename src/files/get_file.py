import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import BotoCoreError, ClientError

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

        response = files_table.get_item(Key={"id": file_id})
        file_data = response.get("Item")

        if not file_data:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "File not found"})
            }

        if file_data["user_id"] != user_id:
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Unauthorized access to file"})
            }

        return {
            "statusCode": 200,
            "body": json.dumps(file_data, default=decimal_to_int)
        }

    except (BotoCoreError, ClientError) as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "AWS error", "details": str(e)})
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Bad request", "details": str(e)})
        }
