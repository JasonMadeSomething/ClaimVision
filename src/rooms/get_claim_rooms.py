"""
Lambda handler for retrieving all rooms associated with a claim.

This module handles retrieving rooms for a claim in the ClaimVision
system, ensuring proper authorization and data validation.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import enhanced_lambda_handler
from models.room import Room
from models.claim_rooms import ClaimRoom
logger = get_logger(__name__)

@enhanced_lambda_handler(
    requires_auth=True,
    path_params=["claim_id"],
    auto_load_resources={"claim_id": "Claim"},
    permissions={"resource_type": "CLAIM", "action": "READ", "path_param": "claim_id"}
)
def lambda_handler(event, context, db_session, user, path_params, resources) -> dict:
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
        # Use decorator-provided params and resources
        claim_id = path_params["claim_id"]
        claim = resources.get("claim")
        if hasattr(claim, "deleted") and getattr(claim, "deleted") is True:
            logger.info("Claim not found or access denied: %s", claim_id)
            return response.api_response(404, error_details="Claim not found or access denied")

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
