import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from models import File, User
from database.database import get_db_session
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Handles updating metadata for a file, excluding labels.

    Args:
        event (dict): API Gateway event containing authentication details, file ID, and update data.
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.

    Returns:
        dict: API response containing the updated file metadata or an error message.
    """
    try:
        db = db_session if db_session else get_db_session()
    except SQLAlchemyError as e:
        logger.error("Failed to get database session: %s", str(e))
        return response.api_response(500, message="Failed to get database session.")
    
    try:
        file_id = event.get("pathParameters", {}).get("id")
        if not file_id:
            return response.api_response(400, message="Missing file ID in request.")
        
        # Extract update data
        body = json.loads(event.get("body", "{}"))
        allowed_fields = {"room_name", "file_metadata"}
        invalid_fields = set(body.keys()) - allowed_fields
        if invalid_fields:
            return response.api_response(400, message=f"Invalid field(s): {', '.join(invalid_fields)}")
        
        # Check for empty payload
        if not body:
            return response.api_response(400, message="Empty request body.")
        
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(401, message="Unauthorized: Missing authentication.")
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return response.api_response(404, message="User not found.")
        # Fetch file and validate ownership
        file = db.query(File).filter_by(id=file_id).first()
        if not file or file.household_id != user.household_id:
            return response.api_response(404, message="File not found.")
        
        # Apply updates
        for field, value in body.items():
            setattr(file, field, value)
        file.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(file)
        db.close()
        
        return response.api_response(200, data=file.to_dict())
    
    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, message="Database error occurred.")
    
    except Exception as e:
        logger.exception("Unexpected error updating file metadata")
        return response.api_response(500, message=str(e))
