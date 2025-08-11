"""
Lambda handler for adding a room to a claim.

This module handles the association of a room with a claim in the ClaimVision system,
ensuring proper authorization and data validation.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from utils import response
from utils.lambda_utils import enhanced_lambda_handler
from models.claim_rooms import ClaimRoom
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
        # Extract IDs and loaded resources from decorator
        claim_id = path_params["claim_id"]
        room_id = path_params["room_id"]
        claim = resources.get("claim")
        room = resources.get("room")

        # Ensure room is active
        if not room or not room.is_active:
            logger.info("Room not found or inactive: %s", room_id)
            return response.api_response(404, error_details="Room not found or inactive")

        # Ensure claim is not deleted (match original behavior)
        if hasattr(claim, "deleted") and getattr(claim, "deleted") is True:
            logger.info("Claim is deleted: %s", claim_id)
            return response.api_response(404, error_details="Claim not found")

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
