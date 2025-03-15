import logging
import os
from models.file import File
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param, generate_presigned_url, get_s3_client

logger = logging.getLogger()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "test-bucket")

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
        
    success, result = extract_uuid_param(event, "id")
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
