import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models.file_labels import FileLabel
from models import Label, File, User
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Handles restoring an AI-generated label for a file.
    
    - If the label is AI-generated and was soft deleted, it is reactivated.
    - User-created labels **cannot** be restored (must be recreated manually).
    
    Parameters:
        event (dict): API Gateway event with file ID and label ID.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing.

    Returns:
        dict: API response confirming restoration or error.
    """
    db = db_session if db_session else get_db_session()

    try:
        # ✅ Extract user ID from JWT claims
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user_id:
            return response.api_response(400, message="Invalid authentication.")
        if not user:
            return response.api_response(400, message="Invalid authentication.")
        file_id = event.get("pathParameters", {}).get("file_id")
        label_id = event.get("pathParameters", {}).get("label_id")

        if not file_id or not label_id:
            return response.api_response(400, message="File ID and Label ID are required.")

        try:
            file_uuid = uuid.UUID(file_id)
            label_uuid = uuid.UUID(label_id)
        except ValueError:
            return response.api_response(400, message="Invalid UUID format.")

        # ✅ Check if the user owns the file
        file = db.query(File).filter(File.id == file_uuid).first()
        if not file:
            return response.api_response(404, message="File not found.")
        if file.household_id != user.household_id:
            return response.api_response(404)

        # Check if the user owns the label
        label = db.query(Label).filter(Label.id == label_uuid).first()
        if not label:
            return response.api_response(404, message="Label not found.")
        if label.household_id != user.household_id:
            return response.api_response(404)

        # 🚨 Prevent restoring user-created labels (must be recreated)
        if not label.is_ai_generated:
            return response.api_response(403, message="User labels cannot be restored.")

        # ✅ Check if the file-label relationship exists
        file_label = db.query(FileLabel).filter(
            FileLabel.file_id == file_uuid,
            FileLabel.label_id == label_uuid
        ).first()
        if not file_label:
            return response.api_response(404, message="Label was never associated with this file.")

        # ✅ If already active, return 200 (no change)
        if not file_label.deleted:
            return response.api_response(200, message="Label is already active.")

        # ✅ Restore label by setting `deleted = False`
        file_label.deleted = False
        db.commit()

        logger.info(f"Restored AI label {label_id} for file {file_id}")
        return response.api_response(200, message="Label restored successfully.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error restoring label: {str(e)}")
        return response.api_response(500, message="Database error.")

    except Exception as e:
        logger.exception("Unexpected error restoring label")
        return response.api_response(500, message="Internal Server Error")

    finally:
        db.close()
