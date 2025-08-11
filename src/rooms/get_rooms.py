"""
Lambda handler for retrieving all available rooms.

This module handles retrieving all rooms from the database,
with an optional claim ID parameter to indicate which rooms are associated with a specific claim.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import enhanced_lambda_handler, extract_uuid_param
from models.room import Room
from models.claim_rooms import ClaimRoom
from models.claim import Claim
from utils.access_control import has_permission
from utils.vocab_enums import PermissionAction, ResourceTypeEnum
from sqlalchemy import select

logger = get_logger(__name__)

@enhanced_lambda_handler(requires_auth=True)
def lambda_handler(event, context, db_session, user) -> dict:
    """
    Handles retrieving all available rooms, with an optional claim ID parameter
    to indicate which rooms are associated with a specific claim.

    Args:
        event (dict): API Gateway event containing authentication details and optional claim ID
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)

    Returns:
        dict: API response containing list of rooms or error message
    """
    try:
        claim_id = None
        
        # Check if claim_id is provided in path parameters
        if event.get("pathParameters") and "claim_id" in event.get("pathParameters", {}):
            # Extract and validate claim_id from path parameters
            success, result = extract_uuid_param(event, "claim_id")
            if not success:
                return result  # Return error response
                
            claim_id = result
                
            # Verify claim exists
            claim = db_session.query(Claim).filter(
                Claim.id == claim_id,
                Claim.deleted.is_(False)
            ).first()
            
            if not claim:
                logger.info("Claim not found: %s", claim_id)
                return response.api_response(404, error_details="Claim not found")
                
            # Verify user has access to claim
            if not has_permission(user, PermissionAction.READ, ResourceTypeEnum.CLAIM.value, db_session, claim_id, user.group_id):
                logger.info("User %s does not have access to claim %s", user.id, claim_id)
                return response.api_response(403, error_details="User does not have access to claim")

        # Query all active rooms
        rooms = db_session.query(Room).filter(
            Room.is_active.is_(True)
        ).order_by(Room.sort_order, Room.name).all()
        
        # If claim_id is provided, get rooms associated with the claim
        claim_room_ids = set()
        if claim_id:
            claim_rooms = db_session.query(ClaimRoom.room_id).filter(
                ClaimRoom.claim_id == claim_id
            ).all()
            claim_room_ids = {str(cr.room_id) for cr in claim_rooms}
        
        # Convert rooms to dictionaries with additional claim association info if claim_id provided
        room_list = []
        for room in rooms:
            room_dict = room.to_dict()
            if claim_id:
                room_dict["is_associated_with_claim"] = str(room.id) in claim_room_ids
            room_list.append(room_dict)
        
        logger.info("Retrieved %s rooms", len(room_list))
        return response.api_response(200, data={"rooms": room_list})
        
    except SQLAlchemyError as e:
        logger.error("Database error when retrieving rooms: %s", str(e))
        return response.api_response(500, error_details="Database error when retrieving rooms")
    except Exception as e:
        logger.exception("Unexpected error retrieving rooms: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
