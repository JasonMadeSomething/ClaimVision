from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from models.file_labels import FileLabel
from models import Label
from utils import response
from utils.lambda_utils import enhanced_lambda_handler

# Configure logging
logger = get_logger(__name__)
@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['file_id', 'label_id'],
    permissions={'resource_type': 'file', 'action': 'write', 'path_param': 'file_id'},
    auto_load_resources={'file_id': 'File', 'label_id': 'Label'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
    """
    Handles label removal from a file.

    - If it's a **user label**, it is **fully removed** from both `Label` and `FileLabel` (hard delete).
    - If it's an **AI label**, it is **soft deleted in `FileLabel` only** (preserves for future processing).
    - If an AI label is globally deleted, all associated `FileLabel` entries are updated.

    Parameters:
        event (dict): API Gateway event containing authentication details, file ID, and label ID.
        context (dict): Lambda execution context.
        db_session (Session): SQLAlchemy session (provided by decorator).
        user (User): Authenticated user object (provided by decorator).
        path_params (dict): Path parameters (provided by decorator).
        resources (dict): Auto-loaded resources (provided by decorator).

    Returns:
        dict: API response confirming deletion or an error message.
    """
    file = resources['file']
    label = resources['label']
    file_id = file.id
    label_id = label.id

    try:
        
        # Check if the file-label relationship exists
        file_label = db_session.query(FileLabel).filter(
            FileLabel.file_id == file_id,
            FileLabel.label_id == label_id
        ).first()
        if not file_label:
            return response.api_response(404, error_details='Label is not associated with this file.')

        # Handle AI vs User Label Deletion
        if label.is_ai_generated:
            # AI Label → Soft delete by setting `deleted = True` in `file_labels`
            file_label.deleted = True
            db_session.commit()
            logger.info("Soft deleted AI label %s from file %s in household %s", label_id, file_id, label.household_id)
            return response.api_response(204, success_message='AI label removed from file.')

        else:
            # User Label → Fully remove from `Label` (global delete)
            db_session.delete(file_label)  # Remove from file_labels first
            db_session.commit()
            remaining_links = db_session.query(FileLabel).filter(FileLabel.label_id == label_id).count()
            if remaining_links == 0:
                db_session.delete(label)  # Only delete globally if no remaining links
                db_session.commit()
            logger.info(f"Deleted user label {label_id} globally from household {label.household_id}")
            return response.api_response(204, success_message='User label deleted globally.')

    except SQLAlchemyError as db_error:
        db_session.rollback()
        logger.error(f"Database error removing label: {str(db_error)}")
        return response.api_response(500, error_details='Database error.')

    except Exception:
        logger.exception("Unexpected error removing label")
        return response.api_response(500, error_details='Internal Server Error')
