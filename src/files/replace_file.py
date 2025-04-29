
##TODO: Delete this file once I confirm it's not used
from utils.logging_utils import get_logger
import base64
import os
import json
from datetime import datetime, timezone
from hashlib import sha256
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError
from models.file import File
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from database.database import get_db_session

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning("S3_BUCKET_NAME appears to be an SSM parameter path: %s. Using default bucket for local testing.", S3_BUCKET_NAME)
    S3_BUCKET_NAME = "claimvision-dev-bucket"

def upload_to_s3(s3_key, file_data):
    """
    Upload file data to S3 bucket.
    
    Args:
        s3_key (str): S3 object key
        file_data (bytes): Binary file data to upload
        
    Raises:
        BotoCoreError, ClientError: If S3 upload fails
    """
    s3 = boto3.client("s3")
    try:
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=file_data)
    except (BotoCoreError, ClientError) as e:
        logger.error("S3 upload failed: %s", str(e))
        raise

@standard_lambda_handler(requires_auth=True, requires_body=True)
def lambda_handler(event, context=None, _context=None, db_session=None, user=None, body=None):
    """
    Handles requests to replace an existing file with a new version.

    This function authenticates the user, validates the file data and permissions,
    uploads the new file to S3 using the same key as the original file,
    and updates the file metadata in the database.

    Args:
        event (dict): API Gateway event containing request data
                  - pathParameters.file_id: UUID of the file to replace
                  - body.file_name: New name for the file
                  - body.file_data: Base64-encoded file content
        context/_context (dict): Lambda execution context (unused)
        db_session (Session, optional): Database session for testing
        user (User): Authenticated user object (provided by decorator)
        body (dict): Request body containing file data (provided by decorator)

    Returns:
        dict: API response with updated file details or error
    """
    # Extract and validate file ID
    success, result = extract_uuid_param(event, "file_id")
    if not success:
        return result  # Return error response
        
    file_id = result
    
    # Validate request body
    if not body:
        return response.api_response(400, error_details="Request body is empty")
    
    # Check for multiple files attempt
    if "files" in body:
        return response.api_response(400, error_details="Only one file can be replaced at a time")
        
    file_name = body.get("file_name")
    file_data_b64 = body.get("file_data")
    
    if not file_name:
        return response.api_response(400, error_details="File name is required")
        
    if not file_data_b64:
        return response.api_response(400, error_details="File data is empty")
    
    # Decode base64 file data
    try:
        file_data = base64.b64decode(file_data_b64)
    except Exception:
        return response.api_response(400, error_details="Invalid base64 encoding")
    
    # Check if file is empty
    if len(file_data) == 0:
        return response.api_response(400, error_details="File data is empty")
        
    # Check file size (10MB limit)
    if len(file_data) > 10 * 1024 * 1024:  # 10MB in bytes
        return response.api_response(400, error_details="File size exceeds the allowed limit")
        
    # Validate file extension
    if "." not in file_name:
        return response.api_response(400, error_details="Invalid file format")
        
    # Check for invalid file extensions
    file_extension = file_name.split(".")[-1].lower()
    allowed_extensions = ["jpg", "jpeg", "png"]
    if file_extension not in allowed_extensions:
        return response.api_response(400, error_details="Invalid file format. Allowed formats: jpg, jpeg, png")
    
    # Retrieve the file, ensuring it belongs to user's household
    file_record = db_session.query(File).filter(
        File.id == file_id,
        File.household_id == user.household_id
    ).first()

    if not file_record:
        return response.api_response(404, error_details="File not found")
    
    # Calculate file hash
    file_hash = sha256(file_data).hexdigest()
    
    try:
        # Upload file to S3 using the existing S3 key
        upload_to_s3(file_record.s3_key, file_data)
        
        # Update file record in database
        file_record.file_name = file_name
        file_record.file_size = len(file_data)
        file_record.file_hash = file_hash
        file_record.updated_at = datetime.now(timezone.utc)
        
        db_session.commit()
        
        # Format the response
        file_response = {
            "id": str(file_record.id),
            "file_name": file_record.file_name,
            "status": file_record.status.value,
            "created_at": file_record.created_at.isoformat() if file_record.created_at else None,
            "updated_at": file_record.updated_at.isoformat() if file_record.updated_at else None,
            "claim_id": str(file_record.claim_id) if file_record.claim_id else None,
            "file_size": len(file_data),
            "file_hash": file_record.file_hash,
            "metadata": file_record.file_metadata or {}
        }
        
        return response.api_response(200, data=file_response)
        
    except (BotoCoreError, ClientError) as s3_error:
        logger.error("S3 error replacing file: %s", str(s3_error))
        return response.api_response(500, error_details="Failed to upload file to storage")
        
    except SQLAlchemyError as db_error:
        logger.error("Database error replacing file: %s", str(db_error))
        db_session.rollback()
        return response.api_response(500, error_details="Database error occurred")
