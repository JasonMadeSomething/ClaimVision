import json
import boto3
import os
from botocore.exceptions import BotoCoreError, ClientError
from utils import response

def get_s3():
    return boto3.client("s3")

def get_files_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))


def lambda_handler(event, context):
    """Replace an existing file"""

    try:
        s3 = get_s3()
        files_table = get_files_table()

        if "requestContext" not in event or "authorizer" not in event["requestContext"]:
            return response.api_response(401, message="Unauthorized: Missing authentication")
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(401, message="Unauthorized: Missing user ID")
        file_id = event["pathParameters"]["id"]

        try:
            body = json.loads(event["body"]) if event.get("body") else {}
            print(type(body))
        except Exception as e:
            return response.api_response(400, message="Invalid JSON format in request body")

        # Build a list of missing fields dynamically
        missing_fields = []
        if "file_name" not in body:
            missing_fields.append("file_name")
        if "file_data" not in body:
            missing_fields.append("file_data")

        # If any fields are missing, return a 400 response
        if missing_fields:
            return response.api_response(400, missing_fields=missing_fields)
        
        ALLOWED_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

        if not any(body["file_name"].lower().endswith(ext) for ext in ALLOWED_FILE_EXTENSIONS):
            return response.api_response(400, message="Invalid file format")  # ✅ Should happen first!

        # ✅ Get existing file metadata
        file_data = files_table.get_item(Key={"id": file_id}).get("Item")
        if not file_data:
            return response.api_response(404, message="File Not Found")

        # ✅ Ensure user owns the file
        if file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")  # Security through obscurity

        # ✅ Parse and validate request body
        try:
            body = json.loads(event["body"])
            file_name = body.get("file_name")
            file_data_encoded = body.get("file_data")
        except (TypeError, json.JSONDecodeError):
            return response.api_response(400, message="Invalid request payload format")

        if not file_name or not file_data_encoded:
            return response.api_response(400, message="Missing required field(s): file_name, file_data")

        if not file_name.lower().endswith((".jpg", ".jpeg", ".png")):
            return response.api_response(400, message="Unsupported file format")

        # ✅ Upload to S3
        s3_key = file_data["s3_key"]
        file_binary = bytes(file_data_encoded, "utf-8")  # Decode from base64
        s3.put_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=s3_key, Body=file_binary)

        # ✅ Update file metadata
        files_table.update_item(
            Key={"id": file_id},
            UpdateExpression="SET file_name = :name",
            ExpressionAttributeValues={":name": file_name},
        )

        return response.api_response(200, message="File replaced successfully")

    except (BotoCoreError, ClientError) as e:
        return response.api_response(500, message="AWS error", error_details=str(e))

    except Exception as e:
        print(f"Exception: {e}")
        return response.api_response(500, message="Internal Server Error", error_details=str(e))
