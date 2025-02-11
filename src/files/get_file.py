import json
import boto3
import os

dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))


def lambda_handler(event, context):
    """Retrieve metadata of a single file"""

    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    file_id = event["pathParameters"]["id"]

    response = files_table.get_item(Key={"id": file_id})
    file_data = response.get("Item")

    if not file_data or file_data["user_id"] != user_id:
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized or File Not Found"})}

    return {"statusCode": 200, "body": json.dumps(file_data)}
