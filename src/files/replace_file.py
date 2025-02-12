import json
import boto3
import os
import base64
from botocore.exceptions import BotoCoreError, ClientError

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def lambda_handler(event, context):
    """Replace an existing file (PUT)"""

    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id = event["pathParameters"]["id"]
        body = json.loads(event["body"])

        file_data = body.get("file_data")  # Base64-encoded file content
        if not file_data:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing file_data"})}

        # Fetch existing file metadata
        response = files_table.get_item(Key={"id": file_id})
        file_data_record = response.get("Item")

        if not file_data_record or file_data_record["user_id"] != user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized or File Not Found"})}

        # Decode file content
        decoded_file = base64.b64decode(file_data)
        s3_key = f"uploads/{user_id}/{file_data_record['file_name']}"

        # Replace file in S3
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=decoded_file)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "File replaced successfully", "file_url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"})
        }

    except (BotoCoreError, ClientError) as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
