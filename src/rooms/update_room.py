"""
Lambda handler for updating a room.

This module handles updating room details in the ClaimVision system,
ensuring proper authorization and data validation.
"""
import uuid
import json
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler
from models.room import Room
from datetime import datetime, timezone

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles updating a room for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and room data
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
            
        # Parse request body
        body_str = event.get("body", "{}")
        try:
            body = json.loads(body_str) if isinstance(body_str, str) else body_str
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in request body")
            return response.api_response(400, error_details="Invalid request body format")
            
        if not body:
            logger.warning("Missing request body")
            return response.api_response(400, error_details="Missing request body")
            
        # Query the room
        room = db_session.query(Room).filter(
            Room.id == room_id,
            Room.household_id == user.household_id,
            Room.deleted.is_(False)
        ).first()
        
        if not room:
            logger.info("Room not found: %s", room_id)
            return response.api_response(404, error_details="Room not found")
            
        # Update room fields
        if "name" in body:
            room.name = body["name"]
            
        if "description" in body:
            room.description = body["description"]
            
        room.updated_at = datetime.now(timezone.utc)
        
        # Save changes
        db_session.commit()
        
        logger.info("Room %s updated successfully", room_id)
        
        # Return success response with updated room data
        return response.api_response(
            200, 
            success_message="Room updated successfully",
            data=room.to_dict()
        )
        
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error("Database error when updating room %s: %s", 
                    room_id if 'room_id' in locals() else "unknown", str(e))
        return response.api_response(500, error_details="Database error when updating room")
    except Exception as e:
        logger.exception("Unexpected error updating room: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
