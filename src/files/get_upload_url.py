"""
Lambda handler for generating pre-signed S3 URLs for file uploads.

This module handles permission checks and generates pre-signed URLs for direct uploads to S3.
Files uploaded using these URLs will trigger a separate Lambda function for processing.
"""
import os
import uuid
import json
import mimetypes
from datetime import datetime, timezone

from utils.logging_utils import get_logger
from utils.lambda_utils import standard_lambda_handler, get_s3_client, extract_uuid_param, generate_presigned_upload_url
from utils.response import api_response
from models.claim import Claim
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction
from batch.batch_tracker import generate_batch_id, file_uploaded

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
    S3_BUCKET_NAME = "claimvision-dev-bucket"

def generate_s3_key(claim_id, file_name, user_id=None):
    """
    Generate a unique S3 key for the file.
    
    Args:
        claim_id (str): UUID of the claim this file belongs to
        file_name (str): Name of the file
        user_id (str, optional): UUID of the user uploading the file
        
    Returns:
        str: S3 key for the file
    """
    # Generate a unique file ID
    file_id = str(uuid.uuid4())
    
    # Sanitize file name to prevent path traversal
    safe_file_name = os.path.basename(file_name)
    
    # Generate S3 key using claim_id, user_id, and file_id
    if user_id:
        return f"pending/{claim_id}/{user_id}/{file_id}/{safe_file_name}"
    else:
        return f"pending/{claim_id}/{file_id}/{safe_file_name}"

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles generating pre-signed URLs for direct file uploads to S3.
    
    Args:
        event (dict): API Gateway event containing authentication details and file data
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)
        
    Returns:
        dict: API response containing pre-signed URLs for upload
    """
    logger.info("Starting pre-signed URL generation for file upload")
    
    # Extract claim_id from path parameters (required)
    success, claim_id_or_error = extract_uuid_param(event, 'claim_id')
    if not success:
        logger.warning("Missing or invalid claim_id in path parameters")
        return claim_id_or_error  # This will be the error response from extract_uuid_param
    
    claim_id = claim_id_or_error
    logger.info(f"Found claim_id in path parameters: {claim_id}")
    
    # Parse the request body
    body = None
    if 'body' in event:
        try:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        except json.JSONDecodeError:
            logger.error("Failed to parse request body as JSON")
            return api_response(400, error_details="Invalid JSON in request body")
    
    if not body:
        logger.error("No request body provided")
        return api_response(400, error_details="Request body is required")
    
    # Extract file information from the request
    files_info = body.get('files', [])
    if not files_info:
        logger.error("No files specified in request")
        return api_response(400, error_details="No files specified in request")
    
    # Extract room_id if provided
    room_id = body.get('room_id')
    
    # Generate a batch ID for this upload session
    batch_id = generate_batch_id()
    logger.info(f"Generated batch ID for upload session: {batch_id}")
    
    # Check if the claim exists
    try:
        claim = db_session.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            logger.warning(f"Claim not found: {claim_id}")
            return api_response(404, error_details="Claim not found")
            
        # Check if the user has permission to upload files to this claim
        if not has_permission(
            db=db_session,
            user=user,
            resource_type=ResourceTypeEnum.CLAIM.value,
            resource_id=claim_id,
            action=PermissionAction.WRITE
        ):
            logger.warning(f"User {user.id} does not have permission to upload files to claim {claim_id}")
            return api_response(403, error_details="You do not have permission to upload files to this claim")
        
        # Get S3 client
        s3_client = get_s3_client()
        
        # Generate pre-signed URLs for each file
        response_files = []
        for file_info in files_info:
            file_name = file_info.get('name')
            content_type = file_info.get('content_type')
            
            if not file_name:
                logger.warning("File name not provided")
                response_files.append({
                    "name": file_name,
                    "status": "error",
                    "error": "File name is required"
                })
                continue
            
            # If content_type is not provided, try to guess it from the file name
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_name)
            
            # Generate S3 key
            s3_key = generate_s3_key(claim_id, file_name, user_id=user.id)
            
            # Generate pre-signed URL
            presigned_data = generate_presigned_upload_url(
                s3_client=s3_client,
                bucket_name=S3_BUCKET_NAME,
                s3_key=s3_key,
                content_type=content_type
            )
            
            if not presigned_data:
                logger.error(f"Failed to generate pre-signed URL for {file_name}")
                response_files.append({
                    "name": file_name,
                    "status": "error",
                    "error": "Failed to generate pre-signed URL"
                })
                continue
            
            # Generate a unique file ID for tracking
            file_id = str(uuid.uuid4())
            
            # Send batch tracking event for file upload URL generation
            try:
                file_uploaded(
                    batch_id=batch_id,
                    file_id=file_id,
                    file_name=file_name,
                    user_id=str(user.id),
                    claim_id=str(claim_id)
                )
                logger.info(f"Sent batch tracking event for file upload URL generation: {file_id}")
            except Exception as e:
                logger.warning(f"Failed to send batch tracking event: {str(e)}")
            
            # Add file metadata to response
            response_files.append({
                "name": file_name,
                "status": "ready",
                "upload_url": presigned_data['url'],
                "s3_key": presigned_data['s3_key'],
                "method": presigned_data['method'],
                "content_type": content_type,
                "expires_in": presigned_data['expires_in'],
                "claim_id": str(claim_id),
                "room_id": str(room_id) if room_id else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "file_id": file_id,
                "batch_id": batch_id
            })
        
        # Determine the appropriate status code based on the results
        has_success = any(file.get('status') == 'ready' for file in response_files)
        has_error = any(file.get('status') == 'error' for file in response_files)
        
        if has_success and has_error:
            # Mixed results - use 207 Multi-Status
            status_code = 207
        elif has_error and not has_success:
            # All files failed - use 500 Server Error
            status_code = 500
        else:
            # All files succeeded - use 200 OK
            status_code = 200
            
        # Return response with pre-signed URLs
        return api_response(status_code, data={"files": response_files, "batch_id": batch_id})
        
    except Exception as e:
        logger.exception(f"Error generating pre-signed URLs: {str(e)}")
        return api_response(500, error_details=f"Error generating pre-signed URLs: {str(e)}")
