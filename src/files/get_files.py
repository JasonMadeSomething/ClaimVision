"""
Lambda handler for retrieving files for a user's household.

This module handles the retrieval of file metadata and generates
presigned URLs for file access when needed.
"""
import os
import json
from utils.logging_utils import get_logger
from utils.lambda_utils import standard_lambda_handler, get_s3_client, extract_uuid_param, generate_presigned_url
from utils import response
from models.file import File
from database.database import get_db_session

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
    S3_BUCKET_NAME = "claimvision-dev-bucket"

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Lambda handler to retrieve files for the authenticated user's household.
    
    Args:
        event (dict): API Gateway event
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): Database session for testing
        user (User): Authenticated user object (provided by decorator)
        
    Returns:
        dict: API response with files or error
    """
    # Validate query parameters
    query_params = event.get("queryStringParameters") or {}
    limit = query_params.get("limit", "10")
    offset = query_params.get("offset", "0")
    
    try:
        limit = int(limit)
        offset = int(offset)
        if limit < 1 or limit > 100 or offset < 0:
            return response.api_response(400, error_details="Invalid pagination parameters")
    except ValueError:
        return response.api_response(400, error_details="Invalid pagination parameters")
        
    # Query files for the user's household
    files_query = db_session.query(File).filter(File.household_id == user.household_id)
    
    # Get total count for pagination
    total_count = files_query.count()
    
    # Apply pagination
    files = files_query.order_by(File.created_at.desc()).offset(offset).limit(limit).all()
    
    # Get S3 client
    s3_client = get_s3_client()
    
    # Format response with pre-signed URLs
    file_data = []
    s3_failure = False
    
    for file in files:
        file_info = {
            "id": str(file.id),
            "file_name": file.file_name,
            "status": file.status.value,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None,
            "claim_id": str(file.claim_id) if file.claim_id else None,
            "metadata": file.file_metadata or {},
        }
        
        # Generate pre-signed URL
        if file.s3_key:
            if S3_BUCKET_NAME:
                signed_url = generate_presigned_url(s3_client, S3_BUCKET_NAME, file.s3_key)
                if signed_url is None:
                    s3_failure = True
                file_info["signed_url"] = signed_url
            else:
                logger.warning("S3_BUCKET_NAME is not set, cannot generate presigned URL")
                s3_failure = True
                file_info["signed_url"] = None
        else:
            file_info["signed_url"] = None
            
        file_data.append(file_info)
        
    # Return response with pagination metadata
    response_data = {
        "files": file_data,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
    }
    
    # Add warning if S3 failed
    if s3_failure:
        response_data["warning"] = "Some file URLs could not be generated"
        
    return response.api_response(200, data=response_data)
