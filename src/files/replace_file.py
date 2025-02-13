"""✅ Replace File"""
import os
import json
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from utils import response

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

def lambda_handler(event, _context):
    """Replace an existing file"""
    response_data = None  # ✅ Unified return point

    try:
        s3 = get_s3()
        files_table = get_files_table()

        user_id = get_authenticated_user(event)
        if not user_id:
            response_data = response.api_response(401)
            return response_data  # ✅ Early return for authentication failure

        extracted = extract_request_data(event)
        if not isinstance(extracted, tuple):
            response_data = response.api_response(400, message="Invalid request payload")
        else:
            file_id, body = extracted

            # If body contains an error message, return it
            if "message" in body:
                response_data = response.api_response(400, message=body["message"])
            else:
                # ✅ Retrieve file metadata
                file_data = files_table.get_item(Key={"id": file_id}).get("Item")
                if not file_data or file_data["user_id"] != user_id:
                    response_data = response.api_response(404, message="File Not Found")
                else:
                    try:
                        upload_file_to_s3(s3, file_data["s3_key"], body["file_data"])
                        files_table.update_item(
                            Key={"id": file_id},
                            UpdateExpression="SET file_name = :name",
                            ExpressionAttributeValues={":name": body["file_name"]},
                        )
                        response_data = response.api_response(
                            200,
                            message="File replaced successfully"
                        )
                    except (BotoCoreError, ClientError) as e:
                        response_data = response.api_response(
                            500,
                            message="AWS error",
                            error_details=str(e)
                        )

    except (BotoCoreError, ClientError) as e:
        response_data = response.api_response(
            500,
            message="AWS error",
            error_details=str(e)
        )
    except Exception as e: #pylint: disable=broad-except
        logger.error("Unhandled exception: %s", str(e), exc_info=True)  # ✅ Linter-friendly
        response_data = response.api_response(
            500,
            message="Internal Server Error",
            error_details=str(e)
        )

    return response_data  # ✅ Single return point at the end
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

def get_s3():
    """✅ Get S3 client"""
    return boto3.client("s3")

def get_files_table():
    """✅ Get DynamoDB table"""
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.getenv("FILES_TABLE"))


def upload_file_to_s3(s3, s3_key, file_data_encoded):
    """Upload a file to S3."""
    file_binary = bytes(file_data_encoded, "utf-8")  # Decode from base64
    s3.put_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=s3_key, Body=file_binary)