"""
Lambda handler for retrieving a room.

This module handles the retrieval of room details in the ClaimVision system,
ensuring proper authorization and data validation.
"""
import uuid
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from utils import response
from utils.lambda_utils import standard_lambda_handler
from models.room import Room

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles retrieving a room for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and room ID
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)

    Returns:
        dict: API response containing room details or error message
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
            
        # Return the room details
        logger.info("Room retrieved successfully: %s", room_id)
        return response.api_response(
            200, 
            data=room.to_dict()
        )
        
    except IntegrityError as e:
        logger.error("Database integrity error when retrieving room: %s", str(e))
        return response.api_response(500, error_details="Database integrity error when retrieving room")
    except OperationalError as e:
        logger.error("Database operational error when retrieving room: %s", str(e))
        return response.api_response(500, error_details="Database operational error when retrieving room")
    except SQLAlchemyError as e:
        logger.error("Database error when retrieving room: %s", str(e))
        return response.api_response(500, error_details="Database error when retrieving room")
    except Exception as e:
        logger.exception("Unexpected error retrieving room: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
