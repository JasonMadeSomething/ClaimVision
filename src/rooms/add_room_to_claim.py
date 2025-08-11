"""
Lambda handler for adding a room to a claim.

This module handles the association of a room with a claim in the ClaimVision system,
ensuring proper authorization and data validation.
"""
import json
import uuid
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models.room import Room
from models.claim_rooms import ClaimRoom
from models.claim import Claim
from datetime import datetime, timezone
from utils.access_control import has_permission
from utils.vocab_enums import PermissionAction, ResourceTypeEnum

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles adding a room to a claim for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details, claim ID and room ID
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)

    Returns:
        dict: API response indicating success or error
    """
    try:
        # Extract claim ID from path parameters
        if not event.get("pathParameters") or "claim_id" not in event.get("pathParameters", {}):
            logger.warning("Missing claim ID in path parameters")
            return response.api_response(400, error_details="Claim ID is required in path parameters")
        
        # Extract room ID from path parameters
        if not event.get("pathParameters") or "room_id" not in event.get("pathParameters", {}):
            logger.warning("Missing room ID in path parameters")
            return response.api_response(400, error_details="Room ID is required in path parameters")

        # Extract and validate claim_id from path parameters
        success, result = extract_uuid_param(event, "claim_id")
        if not success:
            return result  # Return error response
            
        claim_id = result
        
        # Extract and validate room_id from path parameters
        success, result = extract_uuid_param(event, "room_id")
        if not success:
            return result  # Return error response
            
        room_id = result
        
        # Verify claim exists
        claim = db_session.query(Claim).filter(
            Claim.id == claim_id,
            Claim.deleted.is_(False)
        ).first()
        
        if not claim:
            logger.info("Claim not found: %s", claim_id)
            return response.api_response(404, error_details="Claim not found")
            
        # Verify user has write access to claim
        if not has_permission(user, PermissionAction.WRITE, ResourceTypeEnum.CLAIM.value, db_session, claim_id, user.group_id):
            logger.info("User %s does not have write access to claim %s", user.id, claim_id)
            return response.api_response(403, error_details="User does not have write access to claim")
        
        # Verify room exists and is active
        room = db_session.query(Room).filter(
            Room.id == room_id,
            Room.is_active.is_(True)
        ).first()
        
        if not room:
            logger.info("Room not found or inactive: %s", room_id)
            return response.api_response(404, error_details="Room not found or inactive")
            
        # Check if the room is already associated with the claim
        existing_association = db_session.query(ClaimRoom).filter(
            ClaimRoom.claim_id == claim_id,
            ClaimRoom.room_id == room_id
        ).first()
        
        if existing_association:
            logger.info("Room %s is already associated with claim %s", room_id, claim_id)
            return response.api_response(
                200, 
                success_message="Room is already associated with this claim",
                data={"claim_id": str(claim_id), "room_id": str(room_id)}
            )
            
        # Create new association
        claim_room = ClaimRoom(
            claim_id=claim_id,
            room_id=room_id,
            created_at=datetime.now(timezone.utc)
        )
        
        db_session.add(claim_room)
        db_session.commit()
        
        logger.info("Room %s added to claim %s successfully", room_id, claim_id)
        
        # Return success response
        return response.api_response(
            201, 
            success_message="Room added to claim successfully",
            data={"claim_id": str(claim_id), "room_id": str(room_id)}
        )
        
    except IntegrityError as e:
        db_session.rollback()
        logger.error("Database integrity error when adding room to claim: %s", str(e))
        return response.api_response(500, error_details="Database integrity error when adding room to claim")
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error("Database error when adding room to claim: %s", str(e))
        return response.api_response(500, error_details="Database error when adding room to claim")
    except Exception as e:
        logger.exception("Unexpected error adding room to claim: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
