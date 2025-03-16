from utils.logging_utils import get_logger
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models.file_labels import FileLabel
from models import Label
from utils import response
from utils import auth_utils

# Configure logging
logger = get_logger(__name__)
def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Handles label removal from a file.

    - If it's a **user label**, it is **fully removed** from both `Label` and `FileLabel` (hard delete).
    - If it's an **AI label**, it is **soft deleted in `FileLabel` only** (preserves for future processing).
    - If an AI label is globally deleted, all associated `FileLabel` entries are updated.

    Parameters:
        event (dict): API Gateway event containing authentication details, file ID, and label ID.
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.

    Returns:
        dict: API response confirming deletion or an error message.
    """
    db = db_session if db_session else get_db_session()

    try:
        # Extract and validate user ID
        success, result = auth_utils.extract_user_id(event)
        if not success:
            return result  # Return error response
        
        user_id = result
        
        # Get authenticated user
        success, result = auth_utils.get_authenticated_user(db, user_id)
        if not success:
            return result  # Return error response
            
        user = result
        
        # Extract and validate file ID
        success, result = auth_utils.extract_resource_id(event, "file_id")
        if not success:
            return result  # Return error response
            
        file_id = result
        
        # Extract and validate label ID
        success, result = auth_utils.extract_resource_id(event, "label_id")
        if not success:
            return result  # Return error response
            
        label_id = result

        # Check if the label exists
        label = db.query(Label).filter(Label.id == label_id).first()
        if not label:
            return response.api_response(404, error_details='Label not found.')
        
        # Check if user has access to the label's household
        success, error_response = auth_utils.check_resource_access(user, label.household_id)
        if not success:
            return error_response
        
        # Check if the file-label relationship exists
        file_label = db.query(FileLabel).filter(
            FileLabel.file_id == file_id,
            FileLabel.label_id == label_id
        ).first()
        if not file_label:
            return response.api_response(404, error_details='Label is not associated with this file.')

        # Handle AI vs User Label Deletion
        if label.is_ai_generated:
            # AI Label → Soft delete by setting `deleted = True` in `file_labels`
            file_label.deleted = True
            db.commit()
            logger.info("Soft deleted AI label %s from file %s in household %s", label_id, file_id, label.household_id)
            return response.api_response(204, success_message='AI label removed from file.')

        else:
            # User Label → Fully remove from `Label` (global delete)
            db.delete(file_label)  # Remove from file_labels first
            db.commit()
            remaining_links = db.query(FileLabel).filter(FileLabel.label_id == label_id).count()
            if remaining_links == 0:
                db.delete(label)  # Only delete globally if no remaining links
                db.commit()
            logger.info(f"Deleted user label {label_id} globally from household {label.household_id}")
            return response.api_response(204, success_message='User label deleted globally.')

    except SQLAlchemyError as db_error:
        db.rollback()
        logger.error(f"Database error removing label: {str(db_error)}")
        return response.api_response(500, error_details='Database error.')

    except Exception:
        logger.exception("Unexpected error removing label")
        return response.api_response(500, error_details='Internal Server Error')

    finally:
        db.close()
