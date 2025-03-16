from utils.logging_utils import get_logger
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import Label
from models.file_labels import FileLabel
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param

# Configure logging
logger = get_logger(__name__)
@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, context=None, _context=None, db_session: Session = None, user=None) -> dict:
    """
    Handles the deletion of user-created labels globally.
    
    - AI labels **cannot** be deleted globally (handled via `remove_label.py`).
    - User-created labels are **hard deleted** globally.
    
    Parameters:
        event (dict): API Gateway event with label ID and authentication.
        context/_context (dict): Lambda execution context (unused).
        db_session (Session): SQLAlchemy session (provided by decorator).
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response confirming deletion or error.
    """
    # Extract and validate label ID
    success, result = extract_uuid_param(event, "label_id")
    if not success:
        return result  # Return error response
        
    label_id = result

    try:
        # Check if the label exists
        label = db_session.query(Label).filter(Label.id == label_id).first()
        if not label:
            return response.api_response(404, error_details="Label not found.")
            
        # Check if user has access to the label's household
        if label.household_id != user.household_id:
            # Return 404 for security - don't reveal that the label exists
            return response.api_response(404, error_details="Label not found.")

        # Prevent AI labels from being deleted globally
        if label.is_ai_generated:
            db_session.query(Label).filter(Label.id == label_id).update({"deleted": True})
            db_session.commit()
            return response.api_response(204, success_message='Label deleted successfully.')

        # Delete all file associations first
        db_session.query(FileLabel).filter(FileLabel.label_id == label_id).delete()

        # Delete label globally
        db_session.delete(label)
        db_session.commit()

        logger.info("User label %s deleted globally.", label_id)
        return response.api_response(204, success_message='Label deleted successfully.')

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error("Database error deleting label: %s", str(e))
        return response.api_response(500, error_details=f"Database error: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error deleting label: {str(e)}")
        return response.api_response(500, error_details=f'Internal Server Error: {str(e)}')

    finally:
        db_session.close()
