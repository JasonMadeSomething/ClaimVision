import json
import boto3
import os
import base64
from botocore.exceptions import BotoCoreError, ClientError

s3 = boto3.client("s3")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def lambda_handler(event, context):
    """Handle file uploads to S3"""
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]  # Extract user ID from token
        body = json.loads(event["body"])
        
        file_name = body["file_name"]
        file_data = body["file_data"]  # Expecting base64-encoded string

        # Decode file
        decoded_file = base64.b64decode(file_data)

        # Generate S3 key (folder per user)
        s3_key = f"uploads/{user_id}/{file_name}"

        # Upload to S3
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=decoded_file)

        # Generate S3 URL (Pre-signed URL recommended for real use cases)
        file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "File uploaded successfully", "file_url": file_url}),
        }

    except (BotoCoreError, ClientError) as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
