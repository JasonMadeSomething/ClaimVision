import json
import boto3
import os
from botocore.exceptions import BotoCoreError, ClientError
from utils import response

def get_files_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))

def get_s3():
    s3 = boto3.client("s3")
    return s3


def lambda_handler(event, context):
    """Delete a file (DELETE)"""

    BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    try:
        s3 = get_s3()
        files_table = get_files_table()

        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        file_id = event["pathParameters"]["id"]

        # Fetch existing file metadata
        file_response = files_table.get_item(Key={"id": file_id})
        file_data = file_response.get("Item")

        if not file_data or file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")

        # Extract file name and S3 key
        file_name = file_data["file_name"]
        s3_key = f"uploads/{user_id}/{file_name}"

        # Delete from S3
        s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)

        # Delete metadata from DynamoDB
        files_table.delete_item(Key={"id": file_id})

        return response.api_response(204, message="File deleted successfully", data={"file_id": file_id})

    except (BotoCoreError, ClientError) as e:
        return response.api_response(500, message="Internal Server Error", error_details=str(e))
    except Exception as e:
        return response.api_response(400, message="Bad Request", error_details=str(e))
