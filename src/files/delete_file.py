from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from models import File
from utils import response
from utils.lambda_utils import extract_uuid_param, enhanced_lambda_handler
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction


logger = get_logger(__name__)


# Configure logging
@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['file_id'],
    auto_load_resources={'file_id': 'File'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
    """
    Handles deleting a file from both AWS S3 and PostgreSQL.

    This function:
    1. Ensures the file exists and belongs to the user's household.
    2. Performs a soft delete by updating the file status rather than removing the record.
    3. Returns a success response with the deleted file's details.

    Args:
        event (dict): API Gateway event containing authentication details and file ID.
        context/_context (dict): Lambda execution context (unused).
        db_session (Session, optional): Database session for testing.
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response with deleted file details or error.
    """
    # Extract and validate file ID
    success, result = extract_uuid_param(event, "file_id")
    if not success:
        return result  # Return error response

    file_id = result

    # Retrieve the file
    file_data = db_session.query(File).filter(
        File.id == file_id
    ).first()

    if not file_data:
        return response.api_response(404, error_details="File not found")

    # Check if user has edit permission on the claim
    if not has_permission(
        user=user,
        action=PermissionAction.WRITE,
        resource_type=ResourceTypeEnum.CLAIM.value,
        db=db_session,
        resource_id=file_data.claim_id
    ):
        return response.api_response(403, error_details="You do not have permission to delete files in this claim")

    # Check if file is attached to a claim
    if file_data.claim_id is None:
        return response.api_response(400, error_details="Files must be attached to a claim")

    # Perform soft delete
    try:
        # Check for an existing deleted file with the same hash
        existing_deleted_file = db_session.query(File).filter(
            File.file_hash == file_data.file_hash,
            File.deleted,
            File.id != file_data.id
        ).first()

        if existing_deleted_file:
            # If there's already a deleted file with the same hash, hard delete it
            logger.info(f"Found existing deleted file with same hash. Hard deleting file: {existing_deleted_file.id}")
            db_session.delete(existing_deleted_file)

        # Soft delete the current file - only set these values if it's not already deleted
        if not file_data.deleted:
            file_data.deleted = True
            file_data.deleted_at = datetime.now(timezone.utc)
            file_data.updated_at = datetime.now(timezone.utc)
        db_session.commit()

        # Return a 204 No Content response for successful deletion
        return response.api_response(204)

    except SQLAlchemyError as e:
        logger.error(f"Database error deleting file: {str(e)}")
        db_session.rollback()
        return response.api_response(500, error_details="Failed to delete file")
