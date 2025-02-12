import json
import boto3
import os
from botocore.exceptions import BotoCoreError, ClientError

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def lambda_handler(event, context):
    """Delete a file (DELETE)"""

    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id = event["pathParameters"]["id"]

        # Fetch existing file metadata
        response = files_table.get_item(Key={"id": file_id})
        file_data = response.get("Item")

        if not file_data or file_data["user_id"] != user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized or File Not Found"})}

        # Extract file name and S3 key
        file_name = file_data["file_name"]
        s3_key = f"uploads/{user_id}/{file_name}"

        # Delete from S3
        s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)

        # Delete metadata from DynamoDB
        files_table.delete_item(Key={"id": file_id})

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "File deleted successfully", "file_id": file_id})
        }

    except (BotoCoreError, ClientError) as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
