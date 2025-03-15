import logging
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from models import File
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, context=None, _context=None, db_session=None, user=None) -> dict:
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
    success, result = extract_uuid_param(event, "id")
    if not success:
        return result  # Return error response
        
    file_id = result
    
    # Retrieve the file, ensuring it belongs to user's household
    file_data = db_session.query(File).filter(
        File.id == file_id,
        File.household_id == user.household_id
    ).first()

    if not file_data:
        return response.api_response(404, error_details="File not found")
    
    # Check if file is attached to a claim
    if file_data.claim_id is None:
        return response.api_response(400, error_details="Files must be attached to a claim")
    
    # Perform soft delete
    try:
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
