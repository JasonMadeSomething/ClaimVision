import json
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from models import Claim, User
from database.database import get_db_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def lambda_handler(event: dict, _context: dict, db_session=None) -> dict:
    """
    Handles retrieving all claims for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details.
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.

    Returns:
        dict: API response containing the list of claims or an error message.
    """
    try:
        db = db_session if db_session else get_db_session()
    except Exception as e:  # Catch DB connection failure early
        logger.error("Database connection failed: %s", str(e))
        return response.api_response(500, error_details="Database error: " + str(e))

    try:
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(401, error_details="Unauthorized") 

        try:
            user_uuid = uuid.UUID(user_id)  # Ensure user ID is a UUID
        except ValueError:
            return response.api_response(400, error_details="Invalid user ID format. Expected UUID")

        user = db.query(User).filter_by(id=user_uuid).first()
        if not user:
            return response.api_response(401, error_details="Unauthorized")

        claims = db.query(Claim).filter_by(household_id=user.household_id).all()

        claims_data = [
            {
                "id": str(claim.id),
                "title": claim.title,
                "description": claim.description,
                "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d"),
            }
            for claim in claims
        ]

        return response.api_response(200, data={"results": claims_data}, success_message="Claims retrieved successfully")

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details="Database error: " + str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return response.api_response(500, error_details="An unexpected error occurred")

    finally:
        if db_session is None:
            db.close()
