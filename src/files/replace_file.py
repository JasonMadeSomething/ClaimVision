import json
import logging
import base64
import uuid
from datetime import datetime, timezone
from hashlib import sha256
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models import User
from models.file import File, FileStatus
from utils import response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def upload_to_s3(s3_key, file_data):
    s3 = boto3.client("s3")
    bucket_name = "your-s3-bucket-name"
    try:
        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=file_data)
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise

def lambda_handler(event, _context, db_session: Session = None):
    """
    Handles requests to replace an existing file with a new version.

    This function authenticates the user, validates the file data and permissions,
    uploads the new file to S3 using the same key as the original file,
    and updates the file metadata in the database.

    :param event: API Gateway event containing request data
                  - pathParameters.id: UUID of the file to replace
                  - body.file_name: New name for the file
                  - body.file_data: Base64-encoded file content
    :type event: dict
    :param _context: AWS Lambda context (unused)
    :type _context: dict
    :param db_session: SQLAlchemy session for database operations,
                       primarily used for testing
    :type db_session: Session, optional

    :return: Standardized API response with status code and body
    :rtype: dict

    :statuscode 200: File replaced successfully with updated file data
    :statuscode 400: Invalid request (missing fields, invalid format, etc.)
    :statuscode 401: Unauthorized request
    :statuscode 404: File or user not found
    :statuscode 500: Server error (database or S3 operations failed)
    """
    try:
        db = db_session or get_db_session()
    except SQLAlchemyError as e:
        return response.api_response(500, error_details=str(e))

    try:
        # Authenticate user
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(401, error_details="Unauthorized")

        # Parse and validate payload
        file_id = event.get("pathParameters", {}).get("id")
        body = json.loads(event.get("body") or "{}")
        if "files" in body:
            return response.api_response(400, error_details="Only one file can be replaced at a time")
        required_fields = {"file_name", "file_data"}
        if not all(field in body for field in required_fields):
            missing = required_fields - body.keys()
            return response.api_response(400, error_details=f"Missing required fields: {', '.join(missing)}")

        file_name = body["file_name"]
        if not file_name:
            return response.api_response(400, error_details="File name is required")
        if not file_name.lower().endswith((".jpg", ".jpeg", ".png", ".pdf")):
            return response.api_response(400, error_details="Invalid file format")

        if not body["file_data"]:
            return response.api_response(400, error_details="File data is empty")

        try:
            base64.b64decode(body["file_data"])
        except ValueError:
            return response.api_response(400, error_details="Invalid base64 encoding")
        # Validate file size
        file_size = len(base64.b64decode(body["file_data"]))
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            return response.api_response(400, error_details="File size exceeds the allowed limit")

        # Fetch user and file
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            return response.api_response(404, error_details="User not found")

        try:
            uuid.UUID(file_id)
        except ValueError:
            return response.api_response(400, error_details="Invalid file ID")

        file_record = db.query(File).filter(
            File.id == uuid.UUID(file_id),
            File.household_id == user.household_id
        ).first()

        if not file_record:
            return response.api_response(404, error_details="File Not Found")

        decoded_data = base64.b64decode(body["file_data"])
        try:
            upload_to_s3(file_record.s3_key, decoded_data)
        except (BotoCoreError, ClientError) as e:
            logger.error("S3 upload failed for file %s: %s", file_id, str(e))
            return response.api_response(500, error_details="Failed to upload file to storage")

        new_file_hash = sha256(decoded_data).hexdigest()
        # Upload new file to S3
        if file_record.file_hash == new_file_hash:
            return response.api_response(409, message="File already exists with the same content.")

        # Update file metadata
        file_record.file_name = file_name
        file_record.file_hash = new_file_hash
        file_record.status = FileStatus.UPLOADED
        file_record.updated_at = datetime.now(timezone.utc)
        db.commit()

        return response.api_response(200, message="File replaced successfully", data=file_record.to_dict())

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error: %s", str(e))
        return response.api_response(500, error_details=str(e))

    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error")
        return response.api_response(500, error_details=str(e))

    finally:
        if db_session is None:
            db.close()
