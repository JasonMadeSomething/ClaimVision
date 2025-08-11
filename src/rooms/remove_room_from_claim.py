"""
Lambda handler for removing a room from a claim.

This module handles removing the association between a room and a claim in the ClaimVision system,
ensuring proper authorization and data validation.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import enhanced_lambda_handler
from models.claim_rooms import ClaimRoom
from models.item import Item
from models.file import File
from datetime import datetime, timezone

logger = get_logger(__name__)

@enhanced_lambda_handler(
    requires_auth=True,
    path_params=["claim_id", "room_id"],
    auto_load_resources={"claim_id": "Claim", "room_id": "Room"},
    permissions={"resource_type": "CLAIM", "action": "WRITE", "path_param": "claim_id"}
)
def lambda_handler(event, context, db_session, user, path_params, resources) -> dict:
    """
    Handles removing a room from a claim for the authenticated user's household.
    Also removes room associations from any items and files in that claim.

    Args:
        event (dict): API Gateway event containing authentication details, claim ID and room ID
        _context (dict): Lambda execution context (unused)
        db_session (Session, optional): SQLAlchemy session for testing
        user (User): Authenticated user object (provided by decorator)

    Returns:
        dict: API response indicating success or error
    """
    try:
        # Extract IDs and loaded resources from decorator
        claim_id = path_params["claim_id"]
        room_id = path_params["room_id"]
        claim = resources.get("claim")

        # If claim is deleted, preserve original 404 behavior
        if hasattr(claim, "deleted") and getattr(claim, "deleted") is True:
            logger.info("Claim is deleted: %s", claim_id)
            return response.api_response(404, error_details="Claim not found")

        # Check if the room is associated with the claim
        claim_room = db_session.query(ClaimRoom).filter(
            ClaimRoom.claim_id == claim_id,
            ClaimRoom.room_id == room_id
        ).first()

        if not claim_room:
            logger.info("Room %s is not associated with claim %s", room_id, claim_id)
            return response.api_response(404, error_details="Room is not associated with this claim")

        # Remove room association from items in this claim
        items_updated = db_session.query(Item).filter(
            Item.claim_id == claim_id,
            Item.room_id == room_id
        ).update({"room_id": None, "updated_at": datetime.now(timezone.utc)})

        # Remove room association from files in this claim
        files_updated = db_session.query(File).filter(
            File.claim_id == claim_id,
            File.room_id == room_id
        ).update({"room_id": None, "updated_at": datetime.now(timezone.utc)})

        # Delete the claim-room association
        db_session.delete(claim_room)
        db_session.commit()

        logger.info("Room %s removed from claim %s successfully. Updated %s items and %s files.",
                   room_id, claim_id, items_updated, files_updated)

        # Return success response
        return response.api_response(
            200,
            success_message="Room removed from claim successfully",
            data={
                "claim_id": str(claim_id),
                "room_id": str(room_id),
                "items_updated": items_updated,
                "files_updated": files_updated
            }
        )

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error("Database error when removing room from claim: %s", str(e))
        return response.api_response(500, error_details="Database error when removing room from claim")
    except Exception as e:
        logger.exception("Unexpected error removing room from claim: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
