import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models import Label
from models.file_labels import FileLabel
from utils import response
from utils import auth_utils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Handles the deletion of user-created labels globally.
    
    - AI labels **cannot** be deleted globally (handled via `remove_label.py`).
    - User-created labels are **hard deleted** globally.
    
    Parameters:
        event (dict): API Gateway event with label ID and authentication.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.

    Returns:
        dict: API response confirming deletion or error.
    """
    db = db_session if db_session else get_db_session()

    try:
        # Extract and validate user ID
        success, result = auth_utils.extract_user_id(event)
        if not success:
            return result  # Return error response
        
        user_id = result
        
        # Extract and validate label ID
        success, result = auth_utils.extract_resource_id(event, "label_id")
        if not success:
            return result  # Return error response
            
        label_id = result

        # Get authenticated user
        success, result = auth_utils.get_authenticated_user(db, user_id)
        if not success:
            return result  # Return error response
            
        user = result

        # Check if the label exists
        label = db.query(Label).filter(Label.id == label_id).first()
        if not label:
            return response.api_response(404, error_details="Label not found.")
            
        # Check if user has access to the label's household
        success, error_response = auth_utils.check_resource_access(user, label.household_id)
        if not success:
            return error_response

        # Prevent AI labels from being deleted globally
        if label.is_ai_generated:
            db.query(Label).filter(Label.id == label_id).update({"deleted": True})
            db.commit()
            return response.api_response(204, message="Label deleted successfully.")

        # Delete all file associations first
        db.query(FileLabel).filter(FileLabel.label_id == label_id).delete()

        # Delete label globally
        db.delete(label)
        db.commit()

        logger.info("User label %s deleted globally.", label_id)
        return response.api_response(204, message="Label deleted successfully.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting label: {str(e)}")
        return response.api_response(500, error_details="Database error.")

    except Exception as e:
        logger.exception("Unexpected error deleting label")
        return response.api_response(500, error_details="Internal Server Error")

    finally:
        db.close()
