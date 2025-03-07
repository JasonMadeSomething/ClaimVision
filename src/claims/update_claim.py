import json
import logging
import uuid
import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from models import Claim, User
from database.database import get_db_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Handles updating a claim for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details, claim ID, and update data
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.

    Returns:
        dict: API response containing the updated claim details or an error message.
    """
    

    try:
        db = db_session if db_session else get_db_session()
        logger.info("Received request for updating a claim")


        claim_id = event.get("pathParameters", {}).get("claim_id")
        if not claim_id:
            return response.api_response(
                400, error_details="Missing required parameter: claim_id"
            )
        # Extract update data
        body = json.loads(event.get("body", "{}"))
        allowed_fields = {"title", "description", "date_of_loss"}
        invalid_fields = set(body.keys()) - allowed_fields
        if invalid_fields:
            return response.api_response(400, error_details="Invalid update fields")

        # Extract user information from JWT claims
        user_id = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
            .get("sub")
        )
        if not user_id:
            return response.api_response(
                401, error_details="Unauthorized"
            )

        try:
            user_uuid = uuid.UUID(user_id)  # Ensure user ID is a UUID
        except ValueError:
            return response.api_response(
                400, error_details="Invalid user ID format. Expected UUID"
            )

        
        user = db.query(User).filter_by(id=user_uuid).first()
        if not user:
            return response.api_response(404, error_details="User not found")

        # Extract claim ID from path parameters
        

        try:
            claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            return response.api_response(
                400, error_details="Invalid claim ID format. Expected UUID"
            )

        claim = db.query(Claim).filter_by(id=claim_uuid).first()
        if not claim or claim.household_id != user.household_id:
            return response.api_response(404, error_details="Claim not found")

        

        # Apply updates
        for field, value in body.items():
            if field == "date_of_loss":
                try:
                    value = datetime.datetime.strptime(value, "%Y-%m-%d").date()
                    if value > datetime.date.today():  # Prevent future dates
                        return response.api_response(400, error_details="Date of loss cannot be in the future")
                except ValueError:
                    return response.api_response(
                        400, error_details="Invalid date format. Expected YYYY-MM-DD"
                    )
            setattr(claim, field, value)

        db.commit()
        db.refresh(claim)
        
        claim_data = {
            "id": str(claim.id),
            "title": claim.title,
            "description": claim.description,
            "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d"),
        }

        return response.api_response(200, data=claim_data, success_message="Claim updated successfully")

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details="Internal Server Error")

    except Exception as e:
        logger.exception("Unexpected error updating claim")
        return response.api_response(500, error_details="Internal Server Error")
