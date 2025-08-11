import os
from utils.logging_utils import get_logger
from utils.lambda_utils import standard_lambda_handler, get_s3_client, extract_uuid_param, generate_presigned_url, enhanced_lambda_handler
from utils.response import api_response
from models.file import File
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
    S3_BUCKET_NAME = "claimvision-dev-bucket"

@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['file_id'],
    auto_load_resources={'file_id': 'File'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
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
        return api_response(400, error_details="Missing file ID parameter")
        
    success, result = extract_uuid_param(event, "file_id")
    if not success:
        return result  # Return error response
        
    file_id = result
    
    try:
        # First, retrieve the file to check if it's associated with a claim
        file_data = db_session.query(File).filter(
            File.id == file_id,
            ~File.deleted
        ).first()

        if not file_data:
            return api_response(404, error_details="File not found")
        
        # Check permissions based on claim_id if the file is associated with a claim
        if file_data.claim_id:
            # If file is associated with a claim, check permissions on the claim
            if not has_permission(
                user=user,
                action=PermissionAction.READ,
                resource_type=ResourceTypeEnum.CLAIM.value,
                db=db_session,
                resource_id=file_data.claim_id
            ):
                return api_response(403, error_details="You do not have permission to access this file")
        else:
            # If file is not associated with a claim, check if the user is in the same group
            if file_data.group_id and user.group_id == file_data.group_id:
                # User is in the same group as the file, allow access
                pass
            else:
                # As a fallback, check direct file permission (though this is unlikely to be used)
                logger.warning(f"File {file_id} has no claim_id and user is not in the same group, checking direct permissions")
                if not has_permission(
                    user=user,
                    action=PermissionAction.READ,
                    resource_type=ResourceTypeEnum.FILE.value,
                    db=db_session,
                    resource_id=file_id
                ):
                    return api_response(403, error_details="You do not have permission to access this file")
        
        # Generate pre-signed URL for S3 access
        s3_client = get_s3_client()
        
        if not S3_BUCKET_NAME:
            logger.warning("S3_BUCKET_NAME is not set, cannot generate presigned URL")
            return api_response(500, error_details="Failed to generate file link: S3 bucket name not configured")
            
        signed_url = generate_presigned_url(s3_client, S3_BUCKET_NAME, file_data.s3_key)
        
        if not signed_url:
            return api_response(500, error_details="Failed to generate file link")
            
        # Return file details with the pre-signed URL
        return api_response(
            200,
            data={
                "id": str(file_data.id),
                "file_name": file_data.file_name,
                "content_type": file_data.content_type,
                "size_bytes": file_data.file_size,
                "status": file_data.status.value,
                "created_at": file_data.created_at.isoformat() if file_data.created_at else None,
                "updated_at": file_data.updated_at.isoformat() if file_data.updated_at else None,
                "url": signed_url,
                "claim_id": str(file_data.claim_id) if file_data.claim_id else None,
                "room_id": str(file_data.room_id) if file_data.room_id else None,
            },
            success_message="File retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error retrieving file: {str(e)}")
        return api_response(500, error_details=f"Error retrieving file: {str(e)}")
