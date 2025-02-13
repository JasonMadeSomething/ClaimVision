import json
import boto3
import os
from boto3.dynamodb.conditions import Key
from utils import response

def get_s3():
    s3 = boto3.client("s3")
    return s3

def get_files_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))

def lambda_handler(event, context):
    """Update metadata fields of a file (PATCH)"""

    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id = event["pathParameters"]["id"]
        try:
            if not event.get("body"):
                return response.api_response(400, message="Missing required field(s)", missing_fields=["body"])
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return response.api_response(400, message="Invalid JSON format")

        files_table = get_files_table()
        
        # Fetch existing file
        file_response = files_table.get_item(Key={"id": file_id})
        file_data = file_response.get("Item")

        if not file_data or file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")

        # Prepare update expression
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

        # Perform update
        files_table.update_item(
            Key={"id": file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

        return response.api_response(200, message="File metadata updated successfully", data={"file_id": file_id})

    except Exception as e:
        return response.api_response(500, message="Internal Server Error", error_details=str(e))
