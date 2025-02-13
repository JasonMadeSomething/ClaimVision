"""✅ Upload File"""
import json
import os
import base64
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from utils import response, dynamodb_utils

# ✅ Helper functions to get AWS resources
def get_s3():
    """Get the S3 client"""
    return boto3.client("s3")

def get_files_table():
    """Get the DynamoDB table for files"""
    return dynamodb_utils.get_dynamodb_table("FILES_TABLE")

def lambda_handler(event, _context):
    """Handles file uploads"""
    
    # ✅ Step 1: Ensure Authenticated Request
    user_id = get_authenticated_user(event)
    if not user_id:
        return response.api_response(401, message="Unauthorized: Missing authentication")

    # ✅ Step 2: Parse JSON Body Safely
    try:
        body = json.loads(event.get("body") or "{}")  # Ensure body is a dict
        if not isinstance(body, dict):
            return response.api_response(400, message="Invalid request body format")
    except json.JSONDecodeError:
        return response.api_response(400, message="Invalid JSON format in request body")

    # ✅ Step 3: Ensure "files" is Present & Always a List
    files = body.get("files")
    if not files:
        return response.api_response(400, missing_fields=["files"])

    if isinstance(files, dict):  # Convert single file dict to list
        files = [files]

    

    # ✅ Step 4: Validate Each File
    for file in files:
        missing_fields = []
        if "file_name" not in file:
            missing_fields.append("file_name")
        if "file_data" not in file:
            missing_fields.append("file_data")

        if missing_fields:
            return response.api_response(400, missing_fields=missing_fields)

    # ✅ Step 4: Prevent duplicate file names within the batch
    file_names = set()
    for file in files:
        if file["file_name"] in file_names:
            return response.api_response(
                400,
                message=f"Duplicate file '{file['file_name']}' in request",
                error_details=f"File '{file['file_name']}' is a duplicate"
            )
        file_names.add(file["file_name"])

    # ✅ Step 5: Initialize AWS Clients **(Only if Files Are Valid)**
    files_table = get_files_table()
    s3 = get_s3()
    uploaded_files = []
    failed_files = []

    for file in files:

        if "file_name" not in file:
            failed_files.append(
                {
                    "file_name": file.get("file_name", "UNKNOWN"),
                    "reason": "Missing 'file_name' field"
                }
            )
            continue

        if not file["file_name"].lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            print(f"❌ Unsupported format detected: {file['file_name']}")  # 🔍 Debug log
            failed_files.append(
                {
                    "file_name": file["file_name"],
                    "reason": "Unsupported file format"
                }
            )
            continue  # ⬅️ **Skip this file, but continue with others**

        # ✅ Step 5: Decode Base64 Data
        try:
            file_bytes = base64.b64decode(file["file_data"])
        except Exception: # pylint: disable=broad-except
            failed_files.append(
                {
                    "file_name": file["file_name"],
                    "reason": "Invalid base64 encoding"
                }
            )
            continue

        # ✅ Step 6: Upload to S3
        s3_key = f"uploads/{user_id}/{file['file_name']}"
        try:
            s3.put_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=s3_key, Body=file_bytes)
        except (BotoCoreError, ClientError) as e:
            return response.api_response(500, message="AWS S3 error", error_details=str(e))  # ❌ STOP ALL PROCESSING HERE
        except Exception as e:   # pylint: disable=broad-except
            return response.api_response(500, message="Unexpected AWS S3 error", error_details=str(e))  # ❌ STOP ALL PROCESSING HERE
        # ✅ Step 7: Save File Metadata in DynamoDB
        file_item = {
            "id": s3_key,
            "user_id": user_id,
            "file_name": file["file_name"],
            "s3_key": s3_key,
            "status": "uploaded"
        }

        try:
            files_table.put_item(Item=file_item)
            uploaded_files.append(file_item)  # ✅ Add successful upload to list
        except (BotoCoreError, ClientError) as e:
            print(f"🔥 DynamoDB Exception Caught: {e}")
            return response.api_response(500, message="AWS DynamoDB error", error_details=str(e))  # ❌ STOP ALL PROCESSING HERE
        except Exception as e:   # pylint: disable=broad-except
            print(f"🚨 Unexpected Error: {e}")  # Debugging
            return response.api_response(500, message="Unexpected internal error", error_details=str(e))

    # ✅ If all files are invalid
    if not uploaded_files and failed_files:
        return response.api_response(400, message="No valid files uploaded", data={"files_failed": failed_files})

    # ✅ If some files succeeded, some failed (due to user error)
    if uploaded_files and failed_files:
        return response.api_response(
            207,  # Multi-Status (Partial Success)
            message="Some files uploaded successfully, others failed",
            data={"files_uploaded": uploaded_files, "files_failed": failed_files}
        )

    # ✅ If all files uploaded successfully
    return response.api_response(200, message="File(s) uploaded successfully", data={"files_uploaded": uploaded_files})

def get_authenticated_user(event):
    """Extract and return user ID if authentication is valid."""
    auth = event.get("requestContext", {}).get("authorizer", {})
    return auth.get("claims", {}).get("sub")