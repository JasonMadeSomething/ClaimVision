import os
import json
import boto3
from utils.logging_utils import get_logger
from utils.lambda_utils import standard_lambda_handler, get_s3_client, extract_uuid_param, generate_presigned_url
from utils import response
from models.file import File

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
    S3_BUCKET_NAME = "claimvision-dev-bucket"

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, context=None, _context=None, db_session=None, user=None) -> dict:
    """
    Lambda handler to retrieve a specific file by ID.
    
    Args:
        event (dict): API Gateway event
        context/context (dict): Lambda execution context (unused)
        db_session (Session, optional): Database session for testing
        user (User): Authenticated user object (provided by decorator)
        
    Returns:
        dict: API response with file details or error
    """
    # Extract and validate file ID
    if event.get("pathParameters") is None:
        return response.api_response(400, error_details="Missing file ID parameter")
        
    success, result = extract_uuid_param(event, "file_id")
    if not success:
        return result  # Return error response
        
    file_id = result
    
    try:
        # Retrieve the file, ensuring it belongs to user's household
        file_data = db_session.query(File).filter(
            File.id == file_id,
            File.household_id == user.household_id
        ).first()

        if not file_data:
            return response.api_response(404, error_details="File not found")
        
        # Generate pre-signed URL for S3 access
        s3_client = get_s3_client()
        
        if not S3_BUCKET_NAME:
            logger.warning("S3_BUCKET_NAME is not set, cannot generate presigned URL")
            return response.api_response(500, error_details="Failed to generate file link: S3 bucket name not configured")
            
        signed_url = generate_presigned_url(s3_client, S3_BUCKET_NAME, file_data.s3_key)
        
        if not signed_url:
            return response.api_response(500, error_details="Failed to generate file link")

        # Format the response
        file_response = {
            "id": str(file_data.id),
            "file_name": file_data.file_name,
            "status": file_data.status.value,
            "created_at": file_data.created_at.isoformat() if file_data.created_at else None,
            "updated_at": file_data.updated_at.isoformat() if file_data.updated_at else None,
            "claim_id": str(file_data.claim_id) if file_data.claim_id else None,
            "metadata": file_data.file_metadata or {},
            "signed_url": signed_url
        }
        
        return response.api_response(200, data=file_response)
    except Exception as e:
        logger.error(f"Error retrieving file: {str(e)}")
        return response.api_response(500, error_details=f"Database error: {str(e)}")
