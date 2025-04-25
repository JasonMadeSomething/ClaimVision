"""
Lambda handler for retrieving files for a user's household.

This module handles the retrieval of file metadata and generates
presigned URLs for file access when needed.
"""
import os
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils.lambda_utils import standard_lambda_handler, get_s3_client, extract_uuid_param, generate_presigned_url
from utils import response
from models.file import File
from models.claim import Claim
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction
import uuid

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning("S3_BUCKET_NAME appears to be an SSM parameter path: %s. Using default bucket for local testing.", S3_BUCKET_NAME)
    S3_BUCKET_NAME = "claimvision-dev-bucket"

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Lambda handler to retrieve files for the authenticated user based on permissions.
    Can optionally filter by claim_id if provided in path parameters.
    
    Args:
        event (dict): API Gateway event
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): Database session for testing
        user (User): Authenticated user object (provided by decorator)
        
    Returns:
        dict: API response with files or error
    """
    try:
        # Validate query parameters
        query_params = event.get("queryStringParameters") or {}
        limit = query_params.get("limit", "10")
        offset = query_params.get("offset", "0")
        
        # Check if specific file IDs were requested
        file_ids = query_params.get("ids")
        
        try:
            limit = int(limit)
            offset = int(offset)
            if limit < 1 or limit > 100 or offset < 0:
                return response.api_response(400, error_details="Invalid pagination parameters")
        except ValueError:
            return response.api_response(400, error_details="Invalid pagination parameters")
        
        # Check if claim_id is provided in path parameters
        claim_id = None
        if event.get("pathParameters") and "claim_id" in event.get("pathParameters", {}):
            # Extract and validate claim_id from path parameters
            success, result = extract_uuid_param(event, "claim_id")
            if not success:
                return result  # Return error response
                
            claim_id = result
            
            # Verify claim exists and user has permission to access it
            claim = db_session.query(Claim).filter(Claim.id == claim_id).first()
            
            if not claim:
                logger.info("Claim not found: %s", claim_id)
                return response.api_response(404, error_details="Claim not found")
                
            # Check if user has permission to access this claim
            if not has_permission(
                user=user,
                resource_type=ResourceTypeEnum.CLAIM,
                resource_id=claim_id,
                action=PermissionAction.READ,
                db=db_session
            ):
                logger.info("User %s does not have permission to access claim %s", user.id, claim_id)
                return response.api_response(403, error_details="You do not have permission to access this claim")
        
        # Query files based on permissions
        if claim_id:
            # If claim_id is provided, we've already checked permissions on the claim
            # Get all files associated with this claim
            files_query = db_session.query(File).filter(File.claim_id == claim_id)
        else:
            # If no claim_id, we need to get all files the user has access to
            # This is more complex as we need to consider:
            # 1. Files with direct permissions
            # 2. Files associated with claims the user has access to
            
            # Get all claims the user has access to
            accessible_claims = []
            claims = db_session.query(Claim.id).all()
            for claim in claims:
                if has_permission(
                    user=user,
                    resource_type=ResourceTypeEnum.CLAIM,
                    resource_id=claim.id,
                    action=PermissionAction.READ,
                    db=db_session
                ):
                    accessible_claims.append(claim.id)
            
            # Get files associated with accessible claims or with direct permissions
            files_query = db_session.query(File)
            
            # Filter to only include files:
            # 1. Associated with claims the user has access to, OR
            # 2. Files the user has direct permission to access
            if accessible_claims:
                files_query = files_query.filter(
                    (File.claim_id.in_(accessible_claims)) | 
                    (File.claim_id.is_(None))  # Files not associated with any claim
                )
            else:
                # If user has no accessible claims, only show files not associated with claims
                files_query = files_query.filter(File.claim_id.is_(None))
                
            # For files not associated with claims, we need to filter further
            # to only include those the user has direct permission to access
            # This will be done after we get the initial results
            
        # Filter by specific file IDs if provided
        if file_ids:
            try:
                id_list = [uuid.UUID(id_str.strip()) for id_str in file_ids.split(',')]
                files_query = files_query.filter(File.id.in_(id_list))
            except ValueError:
                logger.warning("Invalid file ID format in query: %s", file_ids)
                return response.api_response(400, error_details="Invalid file ID format")

        # Get the files
        files = files_query.order_by(File.created_at.desc()).all()
        
        # For files not associated with claims, filter to only include those
        # the user has direct permission to access
        accessible_files = []
        for file in files:
            if file.claim_id:
                # Already checked claim permission above
                accessible_files.append(file)
            else:
                # Check direct file permission
                if has_permission(
                    user=user,
                    resource_type=ResourceTypeEnum.FILE,
                    resource_id=file.id,
                    action=PermissionAction.READ,
                    db=db_session
                ):
                    accessible_files.append(file)
        
        # Get total count for pagination after permission filtering
        total_count = len(accessible_files)
        
        # Apply pagination to the filtered list
        paginated_files = accessible_files[offset:offset+limit]

        # Get S3 client
        s3_client = get_s3_client()

        # Format response with pre-signed URLs
        file_data = []
        s3_failure = False

        for file in paginated_files:
            file_info = {
                "id": str(file.id),
                "file_name": file.file_name,
                "status": file.status.value,
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "updated_at": file.updated_at.isoformat() if file.updated_at else None,
                "claim_id": str(file.claim_id) if file.claim_id else None,
                "metadata": file.file_metadata or {},
                "labels": [label.label_text for label in file.labels] if file.labels else [],
            }
            
            # Generate pre-signed URL
            if file.s3_key:
                if S3_BUCKET_NAME:
                    signed_url = generate_presigned_url(s3_client, S3_BUCKET_NAME, file.s3_key)
                    if signed_url is None:
                        s3_failure = True
                    file_info["url"] = signed_url
                else:
                    logger.warning("S3_BUCKET_NAME is not set, cannot generate presigned URL")
                    s3_failure = True
                    file_info["url"] = None
            else:
                file_info["url"] = None
                
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
            
        logger.info("Retrieved %s files for user %s", len(file_data), user.id)
        return response.api_response(200, data=response_data)
        
    except SQLAlchemyError as e:
        logger.error("Database error when retrieving files: %s", str(e))
        return response.api_response(500, error_details="Database error when retrieving files")
    except Exception as e:
        logger.exception("Unexpected error retrieving files: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
