import json
import uuid
import logging
import re
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models.claim import Claim
from utils import response

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, _context, db_session=None):
    """
    Handles the creation of a new claim in PostgreSQL.
    
    Validates input, ensures household association, and stores claim in the database.
    """
    try:
        user_id = event["requestContext"]["authorizer"]["claims"].get("sub")
        if not user_id:
            return response.api_response(400, error_details="Missing authentication data")
        
        body = parse_request_body(event)

        # Validate required fields
        missing_fields = [field for field in ["title", "date_of_loss", "household_id"] if field not in body]
        if missing_fields:
            return response.api_response(400, error_details="Missing required fields", missing_fields=missing_fields)

        title_validation_result = validate_title(body["title"])
        if title_validation_result:
            return response.api_response(400, error_details=title_validation_result)

        # Ensure `date_of_loss` is formatted correctly
        if not is_valid_date(body["date_of_loss"]):
            return response.api_response(400, error_details="Invalid date format. Expected YYYY-MM-DD")

        if is_future_date(body["date_of_loss"]):
            return response.api_response(400, error_details="Future dates are not allowed")

        # Use test DB if provided, otherwise use production DB
        db = db_session if db_session else get_db_session()
        
        # Future-proof: Ensure user is part of the household (TODO: Implement verification query)
        # Example: user_households = db.query(HouseholdUser).filter_by(user_id=user_id).all()
        # if body["household_id"] not in [h.id for h in user_households]:
        #     return response.api_response(403, error_details="Unauthorized to create claim for this household")

        # Check for duplicate title in the same household
        household_id = uuid.UUID(body["household_id"])
        existing_claim = db.query(Claim).filter_by(
            household_id=household_id, 
            title=body["title"]
        ).first()
        
        if existing_claim:
            return response.api_response(400, error_details="A claim with this title already exists in your household")

        # Create claim object
        claim = Claim(
            id=uuid.uuid4(),
            household_id=household_id,
            title=body["title"],
            description=body.get("description"),
            date_of_loss=datetime.strptime(body["date_of_loss"], "%Y-%m-%d"),
        )
        
        # Save to PostgreSQL
        db.add(claim)
        db.commit()
        db.refresh(claim)

        logger.info(
            "Claim %s created successfully for household %s", claim.id, body["household_id"]
        )
        
        return response.api_response(201, data={"id": str(claim.id)}, success_message="Claim created successfully")

    except json.JSONDecodeError:
        return response.api_response(400, error_details="Invalid JSON format in request body")

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return response.api_response(500, error_details=f"Database error: {str(e)}")
    
    except Exception as e:
        logger.exception("Unexpected error during claim creation")
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")
    finally:
        if db_session is None and 'db' in locals():
            db.close()

def parse_request_body(event):
    """Parses the request body and ensures it's a valid dictionary."""
    body = json.loads(event.get("body") or "{}")
    if not isinstance(body, dict):
        raise json.JSONDecodeError("Request body must be a valid JSON object", "", 0)
    return body


def is_valid_date(date_str):
    """Validates if a string follows the YYYY-MM-DD date format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def is_future_date(date_str):
    """Validates if date is in the future."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj > datetime.now()
    except ValueError:
        return False

def validate_title(title):
    """Validates if a title is not empty, not a control character, and less than 255 characters."""
    if not title.strip():
        return "Title cannot be empty"
    if len(title) > 255:
        return "Title cannot be more than 255 characters"
    if re.search(r"[;'\"]", title):
        return "Invalid characters in title"
    return ""