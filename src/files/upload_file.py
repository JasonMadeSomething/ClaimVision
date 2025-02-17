"""✅ Upload File - Now Uses PostgreSQL"""
import json
import os
import base64
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models.file import File
from utils import response


def get_s3():
    """Get the S3 client"""
    return boto3.client("s3")


def lambda_handler(event: dict, _context: dict) -> dict:
    """
    Handles file uploads, stores metadata in PostgreSQL, and uploads to S3.

    Parameters
    ----------
    event : dict
        The API Gateway event payload.
    _context : dict
        The AWS Lambda execution context (unused).

    Returns
    -------
    dict
        A standardized API response.
    """
    session = get_db_session()

    # ✅ Step 1: Ensure Authenticated Request
    user_id = get_authenticated_user(event)
    if not user_id:
        return response.api_response(401, message="Unauthorized: Missing authentication")

    # ✅ Step 2: Parse JSON Body
    try:
        body = json.loads(event.get("body") or "{}")
        if not isinstance(body, dict):
            return response.api_response(400, message="Invalid request body format")
    except json.JSONDecodeError:
        return response.api_response(400, message="Invalid JSON format in request body")

    files = body.get("files")
    if not files:
        return response.api_response(400, missing_fields=["files"])

    if isinstance(files, dict):
        files = [files]  # Convert single object to list

    file_names = set()
    uploaded_files = []
    failed_files = []
    s3 = get_s3()

    try:
        for file in files:
            # ✅ Validate Required Fields
            missing_fields = []
            if "file_name" not in file:
                missing_fields.append("file_name")
            if "file_data" not in file:
                missing_fields.append("file_data")

            if missing_fields:
                failed_files.append(
                    {
                        "file_name": file.get("file_name", "UNKNOWN"),
                        "reason": f"Missing required fields: {', '.join(missing_fields)}",
                    }
                )
                continue

            # ✅ Prevent Duplicate File Names in Same Batch
            if file["file_name"] in file_names:
                failed_files.append({"file_name": file["file_name"], "reason": "Duplicate file in request"})
                continue  # ✅ Prevent the duplicate from being uploaded
            file_names.add(file["file_name"])

            # ✅ Validate File Format
            if not file["file_name"].lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                failed_files.append({"file_name": file["file_name"], "reason": "Unsupported file format"})
                continue

            # ✅ Decode Base64 Data
            try:
                file_bytes = base64.b64decode(file["file_data"])
            except Exception:
                failed_files.append({"file_name": file["file_name"], "reason": "Invalid base64 encoding"})
                continue

            # ✅ Upload to S3
            s3_key = f"uploads/{user_id}/{file['file_name']}"
            try:
                s3.put_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=s3_key, Body=file_bytes)
            except (BotoCoreError, ClientError) as e:
                session.rollback()  # ✅ Ensure rollback on S3 failure
                return response.api_response(500, message="S3 Upload Failed", error_details=str(e))
            except Exception as e:
                session.rollback()  # ✅ Ensure rollback on unexpected S3 errors
                return response.api_response(500, message="Unexpected S3 error", error_details=str(e))


            # ✅ Save Metadata in PostgreSQL
            new_file = File(
                user_id=user_id,
                file_name=file["file_name"],
                s3_key=s3_key,
                file_url=f"https://s3.amazonaws.com/{os.getenv('S3_BUCKET_NAME')}/{s3_key}",
                mime_type="image/jpeg",
                size=len(file_bytes),
                status="uploaded",
                labels=[],
                detected_objects=[],
            )
            session.add(new_file)
            uploaded_files.append(new_file)

        # ✅ Commit transaction after processing all files
        if uploaded_files:
            session.commit()
            for file in uploaded_files:
                session.refresh(file)
        else:
            session.rollback()

    except SQLAlchemyError as e:
        session.rollback()
        return response.api_response(500, message="Database error", error_details=str(e))

    finally:
        session.close()

    # ✅ Generate API Response Based on Results
    if not uploaded_files and failed_files:
        return response.api_response(400, data={"files_failed": failed_files}, missing_fields=missing_fields)

    if uploaded_files and failed_files:
        return response.api_response(
            207,
            data={"files_uploaded": [file.to_dict() for file in uploaded_files], "files_failed": failed_files},
        )

    return response.api_response(200, data={"files_uploaded": [file.to_dict() for file in uploaded_files]})


def get_authenticated_user(event: dict) -> str:
    """
    Extracts and returns user ID if authentication is valid.

    Parameters
    ----------
    event : dict
        The API Gateway event payload.

    Returns
    -------
    str
        The user ID from authentication claims, or None if unauthenticated.
    """
    auth = event.get("requestContext", {}).get("authorizer", {})
    return auth.get("claims", {}).get("sub")
