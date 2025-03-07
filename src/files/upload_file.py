import os
import json
import logging
import uuid
import base64
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from models import User
from models.file import FileStatus, File
from database.database import get_db_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB file size limit

def upload_to_s3(file_name: str, file_data: bytes) -> str:
    """Uploads file to S3 and returns the S3 URL."""
    s3 = boto3.client("s3")
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set")
    s3_key = f"uploads/{file_name}"
    
    try:
        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=file_data)
        return f"s3://{bucket_name}/{s3_key}"
    except (BotoCoreError, NoCredentialsError) as e:
        logger.error("S3 upload failed: %s", str(e))
        raise

def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Handles uploading files and storing metadata in PostgreSQL.
    """
    try:
        db = db_session if db_session else get_db_session()
        logger.info("Received request for uploading files")

        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(401, message="Unauthorized request. JWT missing or malformed.")

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return response.api_response(400, message="Invalid user ID format. Expected UUID.")

        user = db.query(User).filter_by(id=user_uuid).first()
        if not user:
            return response.api_response(404, message="User not found.")

        body = json.loads(event.get("body", "{}"))
        files = body.get("files", [])
        if not files:
            return response.api_response(400, message="No files provided in request.")

        allowed_extensions = {"jpg", "jpeg", "png", "gif", "pdf"}
        uploaded_files = []
        failed_files = []
        seen_files = set()
        seen_contents = set()

        for file in files:
            file_name = file.get("file_name")
            file_data = file.get("file_data")

            if not file_data.strip():  # Check if the base64 string is empty
                failed_files.append({"file_name": file_name, "reason": "File data is empty."})
                continue

            if not file_name or not file_data:
                failed_files.append({"file_name": file_name, "reason": "Missing file name or data."})
                continue

            file_extension = file_name.split(".")[-1].lower()
            if file_extension not in allowed_extensions or not file_extension:
                failed_files.append({"file_name": file_name, "reason": "Unsupported file format."})
                continue

            try:
                decoded_data = base64.b64decode(file_data, validate=True)
            except (ValueError, base64.binascii.Error):
                failed_files.append({"file_name": file_name, "reason": "Invalid base64 encoding."})
                continue

            if len(decoded_data) > MAX_FILE_SIZE:
                failed_files.append({"file_name": file_name, "reason": "File exceeds size limit."})
                continue

            file_hash = hash(decoded_data)
            if file_hash in seen_contents:
                failed_files.append({"file_name": file_name, "reason": "Duplicate file."})
                continue
            seen_contents.add(file_hash)
            if (file_name, file_extension) in seen_files:
                failed_files.append({"file_name": file_name, "reason": "Duplicate file."})
                continue
            seen_files.add((file_name, file_extension))
            file_id = uuid.uuid4()
            s3_key = f"files/{file_id}.{file_extension}"

            new_file = File(
                id=file_id,
                uploaded_by=user.id,
                household_id=user.household_id,
                file_name=file_name,
                s3_key=s3_key,
                status=FileStatus.UPLOADED
            )
            db.add(new_file)
            db.commit()
            # Upload file to S3 after DB commit
            try:
                s3_url = upload_to_s3(s3_key, decoded_data)
                uploaded_files.append({"file_name": file_name, "file_id": str(file_id), "s3_url": s3_url})
            except (BotoCoreError, NoCredentialsError, ValueError) as e:
                logger.error(f"S3 upload failed: {str(e)}")
                db.rollback()  # Rollback DB entry if S3 upload fails
                failed_files.append({"file_name": file_name, "reason": "Failed to upload to S3."})

        db.close()
        if not uploaded_files and failed_files:
            # Return 500 if S3 failures caused all uploads to fail
            if any(f["reason"] == "Failed to upload to S3." for f in failed_files):
                return response.api_response(500, message="Internal Server Error", data={"files_failed": failed_files})
            primary_reason = failed_files[0]["reason"] if failed_files else "All file uploads failed."
            return response.api_response(400, message=primary_reason, data={"files_failed": failed_files})
        
        return response.api_response(207 if failed_files else 200, message="Files uploaded successfully" if not failed_files else "Some files failed to upload", data={"files_uploaded": uploaded_files, "files_failed": failed_files})

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, message="Internal Server Error", error_details="Database error occurred.")

    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
        # Handle specific programming or data structure errors
        logger.exception(f"Data handling error during file upload: {str(e)}")
        return response.api_response(500, message="Internal Server Error", 
                                     error_details=f"Error processing request: {str(e)}")
                                     
    except (BotoCoreError, NoCredentialsError) as e:
        # Handle AWS-specific errors that might have escaped the inner try/except
        logger.exception(f"AWS service error during file upload: {str(e)}")
        return response.api_response(500, message="Internal Server Error", 
                                     error_details=f"AWS service error: {str(e)}")