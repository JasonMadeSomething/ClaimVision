"""
Lambda handler for file uploads to the ClaimVision system.

This module handles the initial receipt of file uploads and sends them to an SQS queue
for asynchronous processing. This makes the upload process non-blocking for users.
"""
import os
from utils.logging_utils import get_logger
import uuid
import base64
import json
from datetime import datetime, timezone
from hashlib import sha256
from utils import response as api_response
from utils.lambda_utils import standard_lambda_handler, get_sqs_client
from models.file import File
from models.room import Room
from models.claim import Claim
from database.database import get_db_session as db_get_session
from sqlalchemy.exc import SQLAlchemyError


logger = get_logger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB file size limit
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "test-bucket")

# For backward compatibility with tests
def get_db_session():
    """
    Wrapper function for database session creation to maintain backward compatibility with tests.
    
    Returns:
        Session: SQLAlchemy database session
    """
    return db_get_session()

def queue_file_for_processing(file_name, file_data, claim_id, room_id=None, household_id=None):
    """
    Queue a file for asynchronous processing via SQS.
    
    Args:
        file_name (str): Name of the file to process
        file_data (str): Base64-encoded file data
        claim_id (str): UUID of the claim this file belongs to
        room_id (str, optional): UUID of the room this file belongs to
        household_id (str, optional): UUID of the household this file belongs to
        
    Returns:
        str: Message ID from SQS if successful
        
    Raises:
        ValueError: If SQS queue URL is not set
        ConnectionError: If SQS message sending fails
    """
    # Prepare message payload
    message_body = {
        "file_name": file_name,
        "file_data": file_data,
        "claim_id": claim_id,
        "upload_time": datetime.now(timezone.utc).isoformat(),
        "file_hash": sha256(base64.b64decode(file_data)).hexdigest()
    }
    
    if room_id:
        message_body["room_id"] = room_id
        
    if household_id:
        message_body["household_id"] = household_id
    
    # Get SQS client
    sqs = get_sqs_client()
    sqs_upload_queue_url = os.getenv("SQS_UPLOAD_QUEUE_URL")
    
    if not sqs_upload_queue_url:
        raise ValueError("SQS_UPLOAD_QUEUE_URL environment variable is not set")
    
    sqs_response = sqs.send_message(
        QueueUrl=sqs_upload_queue_url,
        MessageBody=json.dumps(message_body)
    )
    return sqs_response["MessageId"]

@standard_lambda_handler(requires_auth=True, requires_body=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None, body=None) -> dict:
    """
    Handles receiving file uploads and sending them to SQS for processing.
    
    Args:
        event (dict): API Gateway event containing authentication details and file data (unused)
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)
        body (dict): Parsed request body (provided by decorator)
        
    Returns:
        dict: API response containing upload request status
    """
    # Extract household ID from authenticated user
    household_id = user.household_id
    
    # Get required parameters from the request body
    files = body.get("files", [])
    claim_id = body.get("claim_id")
    room_id = body.get("room_id")
    
    # Validate required parameters
    if not files:
        return api_response.api_response(400, error_details='No files provided.')
    
    if not claim_id:
        return api_response.api_response(400, error_details='Claim ID is required.')
        
    # Check for the claim
    try:
        claim_uuid = uuid.UUID(claim_id)
        claim = db_session.query(Claim).filter_by(id=claim_uuid, household_id=household_id).first()
        if not claim:
            return api_response.api_response(404, error_details='Claim not found.')
    except (ValueError, SQLAlchemyError) as e:
        if isinstance(e, ValueError):
            return api_response.api_response(400, error_details='Invalid claim ID format. Expected UUID.')
        else:
            logger.error("Database error when checking claim: %s", str(e))
            return api_response.api_response(500, error_details=f'Database Error: {str(e)}')
    
    # Check for the room if provided
    if room_id:
        try:
            room_uuid = uuid.UUID(room_id)
            room = db_session.query(Room).filter_by(id=room_uuid, claim_id=claim_uuid).first()
            if not room:
                return api_response.api_response(404, error_details='Room not found.')
        except (ValueError, SQLAlchemyError) as e:
            if isinstance(e, ValueError):
                return api_response.api_response(400, error_details='Invalid room ID format. Expected UUID.')
            else:
                logger.error("Database error when checking room: %s", str(e))
                return api_response.api_response(500, error_details=f'Database Error: {str(e)}')
    
    # Check for duplicate content
    uploaded_files = []
    failed_files = []
    
    # Process each file in the request
    for file_obj in files:
        file_name = file_obj.get("file_name", "")
        file_data = file_obj.get("file_data", "")
        
        # Validate file name
        if not file_name:
            failed_files.append({"file_name": "unknown", "reason": "Missing file name."})
            continue
        
        # Validate file data
        if not file_data:
            failed_files.append({"file_name": file_name, "reason": "Missing file data."})
            continue
            
        # Check file extension
        file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
        if not file_extension:
            failed_files.append({"file_name": file_name, "reason": "Missing file extension."})
            continue
            
        # Validate file type (basic check)
        allowed_extensions = ["jpg", "jpeg", "png", "pdf"]
        if file_extension not in allowed_extensions:
            failed_files.append({
                "file_name": file_name, 
                "reason": f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            })
            continue
        
        # Validate base64 data
        try:
            decoded_data = base64.b64decode(file_data)
            if not decoded_data:
                failed_files.append({"file_name": file_name, "reason": "Empty file content."})
                continue
                
            # Check file size
            if len(decoded_data) > MAX_FILE_SIZE:
                failed_files.append({
                    "file_name": file_name, 
                    "reason": f"File exceeds maximum size of {MAX_FILE_SIZE/1024/1024}MB."
                })
                continue
                
            # Generate content hash for duplicate detection
            file_hash = sha256(decoded_data).hexdigest()
            
            # Check for duplicate content in this batch
            if any(f.get("file_hash") == file_hash for f in uploaded_files):
                failed_files.append({"file_name": file_name, "reason": "Duplicate content detected."})
                continue
                
            # Check for existing files with the same content
            existing_file = db_session.query(File).filter_by(
                file_hash=file_hash, 
                claim_id=claim_uuid
            ).first()
            
            if existing_file:
                failed_files.append({"file_name": file_name, "reason": "Duplicate content detected."})
                continue
                
        except (ValueError, TypeError, base64.binascii.Error) as e:
            logger.error("Error processing file %s: %s", file_name, str(e))
            failed_files.append({"file_name": file_name, "reason": "Invalid file data format."})
            continue
            
        # Queue the file for processing
        try:
            # Generate a unique ID for this file
            file_id = str(uuid.uuid4())
            
            # Queue the file for processing via SQS
            message_id = queue_file_for_processing(
                file_name=file_name,
                file_data=file_data,
                claim_id=claim_id,
                room_id=room_id,
                household_id=str(household_id)
            )
            
            logger.info("File %s queued for processing with message ID %s", file_name, message_id)
            
            # Create a response object for this file
            file_response = {
                "file_id": file_id,
                "file_name": file_name,
                "status": "QUEUED",
                "file_hash": file_hash
            }
                
            uploaded_files.append(file_response)
        except (ValueError, ConnectionError) as e:
            logger.error("Failed to queue file %s for processing: %s", file_name, str(e))
            failed_files.append({"file_name": file_name, "reason": "Failed to queue for processing."})
        
    if not uploaded_files and failed_files:
        # Return 500 if SQS failures caused all uploads to fail
        if any(f["reason"] == "Failed to queue for processing." for f in failed_files):
            return api_response.api_response(500, error_details='Internal Server Error', data={"files_failed": failed_files})
        elif any(f["reason"] == "Duplicate content detected." for f in failed_files):
            return api_response.api_response(409, error_details='Duplicate content detected', data={"files_failed": failed_files})
        primary_reason = failed_files[0]["reason"] if failed_files else "All file uploads failed."
        return api_response.api_response(400, error_details=primary_reason, data={"files_failed": failed_files})
    
    return api_response.api_response(
        207 if failed_files else 200, 
        success_message="Files queued for processing successfully" if not failed_files else "Some files queued for processing", 
        data={"files_queued": uploaded_files, "files_failed": failed_files} if failed_files else {"files_queued": uploaded_files}
    )