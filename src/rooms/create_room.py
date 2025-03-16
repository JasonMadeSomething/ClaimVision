"""
Lambda handler for creating a new room.

This module handles the creation of rooms in the ClaimVision system,
ensuring proper authorization and data validation.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler
from models.room import Room
from models import Claim
from uuid import UUID

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True, requires_body=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None, body=None) -> dict:
    """
    Handles creating a new room for a claim in the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)
        body (dict): Request body containing room data (provided by decorator)

    Returns:
        dict: API response containing created room details or error message
    """
    try:
        # Extract required fields from the request body
        name = body.get("name")
        description = body.get("description", "")
        claim_id = body.get("claim_id")

        # Validate required fields
        if not name:
            return response.api_response(400, error_details="Room name is required")
        
        if not claim_id:
            return response.api_response(400, error_details="Claim ID is required")
            
        try:
            claim_uuid = UUID(claim_id)
        except ValueError:
            return response.api_response(400, error_details="Invalid claim ID format")
            
        # Verify claim exists and belongs to user's household
        claim = db_session.query(Claim).filter(
            Claim.id == claim_uuid,
            Claim.household_id == user.household_id
        ).first()
        
        if not claim:
            return response.api_response(404, error_details="Claim not found or access denied")
            
        # Create the room
        new_room = Room(
            name=name,
            description=description,
            household_id=user.household_id,
            claim_id=claim_uuid
        )
        
        db_session.add(new_room)
        db_session.commit()
        
        logger.info("Room created successfully: %s", new_room.id)
        
        # Return success response with room data
        return response.api_response(
            201,
            success_message="Room created successfully",
            data=new_room.to_dict()
        )
        
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error("Database error creating room: %s", str(e))
        return response.api_response(500, error_details="Database error: {}".format(str(e)))
    except Exception as e:
        logger.error("Unexpected error creating room: %s", str(e))
        return response.api_response(500, error_details="Unexpected error: {}".format(str(e)))
