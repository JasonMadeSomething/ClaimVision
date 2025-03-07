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
    Handles retrieving a single claim by ID for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID.
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.

    Returns:
        dict: API response containing the claim details or an error message.
    """
    try:
        db = db_session if db_session else get_db_session()
    except Exception as e:  # Catch DB connection failure immediately
        logger.error("Database connection failed: %s", str(e))
        return response.api_response(500, error_details=f"Database error: {str(e)}")

    try:
        logger.info("Received request for retrieving a single claim")

        # Extract and validate claim ID before querying the database
        claim_id = event.get("pathParameters", {}).get("claim_id")
        if not claim_id:
            return response.api_response(400, error_details="Missing claim ID in request")

        try:
            claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            return response.api_response(400, error_details="Invalid claim ID format. Expected UUID")

        # Extract and validate user ID
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(400, error_details="Invalid authentication. JWT missing or malformed")

        try:
            user_uuid = uuid.UUID(user_id)  # Ensure user ID is a UUID
        except ValueError:
            return response.api_response(400, error_details="Invalid user ID format. Expected UUID")

        user = db.query(User).filter_by(id=user_uuid).first()
        if not user:
            return response.api_response(404, error_details="User not found")

        claim = db.query(Claim).filter_by(id=claim_uuid).first()
        if not claim or claim.household_id != user.household_id:
            return response.api_response(404, error_details="Claim not found")

        claim_data = {
            "id": str(claim.id),
            "title": claim.title,
            "description": claim.description,
            "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d"),
        }

        return response.api_response(200, data=claim_data, success_message="Claim retrieved successfully")

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details=f"Database error: {str(e)}")

    except Exception as e:
        logger.exception("Unexpected error retrieving claim")
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")

    finally:
        if db_session is None:
            db.close()
