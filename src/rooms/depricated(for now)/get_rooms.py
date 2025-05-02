#TODO: Detemine if this is redundant with get_claim_rooms
"""
Lambda handler for retrieving all rooms for a claim.

This module handles the retrieval of rooms from the ClaimVision system,
ensuring proper authorization and data access.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models.room import Room
from models.claim import Claim

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles retrieving all rooms for a claim in the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)

    Returns:
        dict: API response containing list of rooms or error message
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
            
        # Query rooms for the claim
        rooms = db_session.query(Room).filter(
            Room.claim_id == claim_id,
            Room.household_id == user.household_id,
            Room.deleted.is_(False)
        ).all()
        
        # Convert rooms to dictionaries
        room_list = [room.to_dict() for room in rooms]
        
        logger.info("Retrieved %s rooms for claim %s", len(room_list), claim_id)
        return response.api_response(200, data={"rooms": room_list})
        
    except SQLAlchemyError as e:
        logger.error(f"Database error when retrieving rooms for claim {claim_id if 'claim_id' in locals() else 'unknown'}: {str(e)}")
        return response.api_response(500, error_details="Database error when retrieving rooms")
    except Exception as e:
        logger.exception(f"Unexpected error retrieving rooms: {str(e)}")
        return response.api_response(500, error_details="Internal server error")
