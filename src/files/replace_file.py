import json
import boto3
import os
import base64
from botocore.exceptions import BotoCoreError, ClientError
from ..utils import response as response

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
            return response.api_response(400, message="Missing file_data")

        # Fetch existing file metadata
        response = files_table.get_item(Key={"id": file_id})
        file_data_record = response.get("Item")

        if not file_data_record or file_data_record["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")

        # Decode file content
        decoded_file = base64.b64decode(file_data)
        s3_key = f"uploads/{user_id}/{file_data_record['file_name']}"

        # Replace file in S3
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=decoded_file)

        return response.api_response(200, message="File replaced successfully", data={"file_url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"})

    except (BotoCoreError, ClientError) as e:
        return response.api_response(500, message="Internal Server Error", error_details=str(e))
    except Exception as e:
        return response.api_response(400, message="Bad Request", error_details=str(e))
