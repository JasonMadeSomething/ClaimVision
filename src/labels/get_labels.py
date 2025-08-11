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
from utils.lambda_utils import enhanced_lambda_handler


logger = get_logger(__name__)


# Configure logging
@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['file_id'],
    permissions={'resource_type': 'file', 'action': 'read', 'path_param': 'file_id'},
    auto_load_resources={'file_id': 'File'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
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
    file = resources['file']
    file_id = file.id

    try:
        # File already loaded and permission checked by decorator

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
