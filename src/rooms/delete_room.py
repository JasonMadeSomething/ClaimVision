"""
Lambda handler for deleting a room.

This module handles the deletion of rooms in the ClaimVision system,
ensuring proper authorization and data integrity.
"""
import uuid
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler
from models import Room, Item, File
from datetime import datetime, timezone

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles deleting a room for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and room ID
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)

    Returns:
        dict: API response indicating success or error
    """
    try:
        # Extract room ID from path parameters
        try:
            room_id_str = event.get("pathParameters", {}).get("room_id")
            room_id = uuid.UUID(room_id_str) if room_id_str else None
        except (ValueError, TypeError):
            logger.warning("Invalid room ID format: %s", room_id_str if 'room_id_str' in locals() else "None")
            return response.api_response(400, error_details="Invalid room ID format")
            
        if not room_id:
            logger.warning("Missing room ID in request")
            return response.api_response(400, error_details="Invalid room ID format")
            
        # Query the room
        room = db_session.query(Room).filter(
            Room.id == room_id,
            Room.household_id == user.household_id,
            Room.deleted.is_(False)
        ).first()
        
        if not room:
            logger.info("Room not found: %s", room_id)
            return response.api_response(404, error_details="Room not found")
            
        # Soft delete the room
        room.deleted = True
        room.updated_at = datetime.now(timezone.utc)
        
        # Remove room associations from items and files
        items = db_session.query(Item).filter(Item.room_id == room_id).all()
        for item in items:
            item.room_id = None
            
        files = db_session.query(File).filter(File.room_id == room_id).all()
        for file in files:
            file.room_id = None
            
        # Save changes
        db_session.commit()
        
        logger.info("Room %s deleted successfully", room_id)
        
        # Return success response
        return response.api_response(
            200, 
            success_message="Room deleted successfully"
        )
        
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error("Database error when deleting room %s: %s", 
                    room_id if 'room_id' in locals() else "unknown", str(e))
        return response.api_response(500, error_details="Database error when deleting room")
    except Exception as e:
        logger.exception("Unexpected error deleting room: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
