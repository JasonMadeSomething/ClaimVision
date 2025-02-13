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


def lambda_handler(event, _context):
    """Replace an existing file"""

    try:
        s3 = get_s3()
        files_table = get_files_table()

        user_id = get_authenticated_user(event)
        if not user_id:
            return response.api_response(401)

        extracted = extract_request_data(event)
        
        if not isinstance(extracted, tuple):
            return response.api_response(400, message="Invalid request payload")

        file_id, body = extracted

        # If body contains an error message, return it
        if "message" in body:
            return response.api_response(400, message=body["message"])
        
        file_id, body = extracted

        # ✅ Retrieve file metadata
        file_data = files_table.get_item(Key={"id": file_id}).get("Item")
        if not file_data:
            return response.api_response(404, message="File Not Found")

        # ✅ Ensure user owns the file
        if file_data["user_id"] != user_id:
            return response.api_response(404, message="File Not Found")  # Security through obscurity

        print(body)
        # ✅ Upload to S3
        try:
            upload_file_to_s3(s3, file_data["s3_key"], body["file_data"])
        except (BotoCoreError, ClientError) as e:
            return response.api_response(500, message="AWS error", error_details=str(e))

        # ✅ Update file metadata
        files_table.update_item(
            Key={"id": file_id},
            UpdateExpression="SET file_name = :name",
            ExpressionAttributeValues={":name": body["file_name"]},
        )

        return response.api_response(200, message="File replaced successfully")

    except (BotoCoreError, ClientError) as e:
        return response.api_response(500, message="AWS error", error_details=str(e))

    except Exception as e:
        print(f"Exception: {e}")
        return response.api_response(500, message="Internal Server Error", error_details=str(e))

def get_authenticated_user(event):
    """Extract and return the user ID from the event if authentication is valid."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    return claims.get("sub")

def extract_request_data(event):
    """Extract and validate request data from the event."""
    if "pathParameters" not in event or "id" not in event["pathParameters"]:
        return None

    file_id = event["pathParameters"]["id"]

    try:
        body = json.loads(event["body"]) if "body" in event and event["body"] else {}
    except (json.JSONDecodeError, KeyError):
        return None

    file_name = body.get("file_name")

    # ✅ Prioritize file format validation first
    if file_name and not file_name.lower().endswith((".jpg", ".jpeg", ".png")): 
        return None, {"message": "Invalid file format"}
    required_fields = {"file_name", "file_data", "s3_key"}
    missing_fields = required_fields - body.keys()
    if missing_fields:  
        return None, {"message": f"Missing required fields: {', '.join(missing_fields)}"}
    return file_id, body

def upload_file_to_s3(s3, s3_key, file_data_encoded):
    """Upload a file to S3."""
    file_binary = bytes(file_data_encoded, "utf-8")  # Decode from base64
    s3.put_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=s3_key, Body=file_binary)