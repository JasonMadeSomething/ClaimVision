"""
Lambda handler for retrieving all rooms associated with a claim.

This module handles retrieving rooms for a claim in the ClaimVision
system, ensuring proper authorization and data validation.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models.room import Room
from models.claim_rooms import ClaimRoom
from models.claim import Claim
from utils.access_control import has_permission
from utils.vocab_enums import PermissionAction, ResourceTypeEnum
logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles retrieving all rooms associated with a claim for the authenticated user's household.

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

        # Verify claim exists
        claim = db_session.query(Claim).filter(
            Claim.id == claim_id,
            Claim.deleted.is_(False)
        ).first()

        if not claim:
            logger.info("Claim not found or access denied: %s", claim_id)
            return response.api_response(404, error_details="Claim not found or access denied")

        # Verify user has access to claim
        if not has_permission(user, PermissionAction.READ, ResourceTypeEnum.CLAIM.value, db_session, claim_id, user.group_id):
            logger.info("User %s does not have access to claim %s", user.id, claim_id)
            return response.api_response(403, error_details="User does not have access to claim")

        # Query rooms associated with the claim through the join table
        rooms = db_session.query(Room).join(
            ClaimRoom, Room.id == ClaimRoom.room_id
        ).filter(
            ClaimRoom.claim_id == claim_id
        ).all()

        # Convert rooms to dictionaries
        room_list = [room.to_dict() for room in rooms]

        logger.info("Retrieved %s rooms for claim %s", len(room_list), claim_id)
        return response.api_response(200, data={"rooms": room_list})

    except SQLAlchemyError as e:
        logger.error("Database error when retrieving rooms for claim %s: %s",
                    claim_id if 'claim_id' in locals() else "unknown", str(e))
        return response.api_response(500, error_details="Database error when retrieving rooms")
