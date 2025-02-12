import json
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))

def lambda_handler(event, context):
    """Update metadata fields of a file (PATCH)"""

    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id = event["pathParameters"]["id"]
        body = json.loads(event["body"])

        # Fetch existing file
        response = files_table.get_item(Key={"id": file_id})
        file_data = response.get("Item")

        if not file_data or file_data["user_id"] != user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized or File Not Found"})}

        # Prepare update expression
        update_expression = "SET "
        expression_attribute_values = {}

        allowed_fields = ["description", "labels", "associated_claim_id"]

        for key in allowed_fields:
            if key in body:
                update_expression += f"{key} = :{key}, "
                expression_attribute_values[f":{key}"] = body[key]

        if not expression_attribute_values:
            return {"statusCode": 400, "body": json.dumps({"error": "No valid fields to update"})}

        update_expression = update_expression.rstrip(", ")

        # Perform update
        files_table.update_item(
            Key={"id": file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "File metadata updated successfully"})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
