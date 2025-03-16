"""
Retrieve Labels for a File

This module handles fetching all labels associated with a given file.
Ensures the user has access to the file's labels and filters appropriately.

Example Usage:
    GET /files/{file_id}/labels
"""

from utils.logging_utils import get_logger
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import Label, File
from models.file_labels import FileLabel
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param


logger = get_logger(__name__)


# Configure logging
@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, context=None, _context=None, db_session: Session = None, user=None) -> dict:
    """
    Retrieves all labels associated with a given file.

    Ensures:
    - The file exists.
    - The requesting user has access to the file's household.
    - Both AI-generated and user-created labels are returned.
    - Soft-deleted AI labels are included.

    Parameters
    ----------
    event : dict
        The API Gateway event payload.
    context/_context : dict
        The AWS Lambda execution context (unused).
    db_session : Session
        SQLAlchemy session (provided by decorator).
    user : User
        Authenticated user object (provided by decorator).

    Returns
    -------
    dict
        Standardized API response containing the list of labels.
    """
    # Extract and validate file ID
    success, result = extract_uuid_param(event, "file_id")
    if not success:
        return result  # Return error response
        
    file_id = result

    try:
        # Step 1: Retrieve file
        file = db_session.query(File).filter(File.id == file_id).first()
        if not file:
            return response.api_response(404, error_details='File not found.')
        
        # Check if user has access to the file's household
        if file.household_id != user.household_id:
            return response.api_response(403, error_details='Access denied to this file.')

        # Step 2: Retrieve labels (including soft-deleted AI ones)
        labels = (
            db_session.query(Label)
            .join(FileLabel, FileLabel.label_id == Label.id)
            .filter(FileLabel.file_id == file_id)
            .filter(Label.household_id == user.household_id)
            .filter(
                (Label.is_ai_generated.is_(False))  # User-created labels always appear
                | (Label.deleted.is_(False))        # AI labels must NOT be soft deleted
            )
            .all()
        )

        return response.api_response(200, success_message='Labels retrieved successfully.',
            data={"labels": [label.to_dict() for label in labels]}
        )

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details=f'Database error occurred: {str(e)}')
