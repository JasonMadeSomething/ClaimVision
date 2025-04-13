"""
Lambda handler for retrieving a room.

This module handles the retrieval of room details in the ClaimVision system,
ensuring proper authorization and data validation.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models.room import Room
from models.claim import Claim

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
        # Extract claim ID from path parameters
        if not event.get("pathParameters") or "claim_id" not in event.get("pathParameters", {}):
            logger.warning("Missing claim ID in path parameters")
            return response.api_response(400, error_details="Claim ID is required in path parameters")
            
        # Extract and validate claim_id from path parameters
        success, result = extract_uuid_param(event, "claim_id")
        if not success:
            return result  # Return error response
            
        claim_id = result
        
        # Verify claim exists and belongs to user's household
        claim = db_session.query(Claim).filter(
            Claim.id == claim_id,
            Claim.household_id == user.household_id
        ).first()
        
        if not claim:
            logger.info("Claim not found or access denied: %s", claim_id)
            return response.api_response(404, error_details="Claim not found or access denied")
        
        # Extract room ID from path parameters
        if not event.get("pathParameters") or "room_id" not in event.get("pathParameters", {}):
            logger.warning("Missing room ID in path parameters")
            return response.api_response(400, error_details="Room ID is required in path parameters")
            
        # Extract and validate room_id from path parameters
        success, result = extract_uuid_param(event, "room_id")
        if not success:
            return result  # Return error response
            
        room_id = result
            
        # Query the room
        room = db_session.query(Room).filter(
            Room.id == room_id,
            Room.claim_id == claim_id,
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
