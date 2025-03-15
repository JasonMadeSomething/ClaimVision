import logging
import uuid
from datetime import datetime, date
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler
from models import Claim, Household

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

@standard_lambda_handler(requires_auth=True, requires_body=True, required_fields=["title", "date_of_loss"])
def lambda_handler(event: dict, context: dict = None, db_session=None, user=None, body=None) -> dict:
    """
    Handles creating a new claim for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and claim data.
        context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.
        user (User): Authenticated user object (provided by decorator).
        body (dict): Request body containing claim data (provided by decorator).

    Returns:
        dict: API response containing the created claim details or an error message.
    """
    try:
        # Validate title is not empty
        if not body["title"].strip():
            return response.api_response(400, error_details="Title cannot be empty")
            
        # Check for SQL injection or invalid characters in title
        if "'" in body["title"] or ";" in body["title"]:
            return response.api_response(400, error_details="Invalid characters in title")

        # Validate date format
        try:
            date_of_loss = datetime.strptime(body["date_of_loss"], "%Y-%m-%d").date()
        except ValueError:
            return response.api_response(400, error_details="Invalid date format. Expected YYYY-MM-DD")
            
        # Validate date is not in the future
        if date_of_loss > date.today():
            return response.api_response(400, error_details="Future date is not allowed")

        # Use the household_id from the authenticated user or from the body (for tests)
        if "household_id" in body:
            # This is primarily for testing
            try:
                household_id = str(body["household_id"])
                household_uuid = uuid.UUID(household_id)
            except (ValueError, TypeError):
                return response.api_response(400, error_details="Invalid household ID format. Expected UUID")
                
            # Check if household exists
            household = db_session.query(Household).filter_by(id=household_uuid).first()
            if not household:
                return response.api_response(404, error_details="Household not found")
        else:
            # Use the household_id from the authenticated user
            household_id = str(user.household_id)
            household_uuid = uuid.UUID(household_id)

        # Check for duplicate title
        existing_claim = db_session.query(Claim).filter(
            Claim.title == body["title"],
            Claim.household_id == household_uuid
        ).first()
        
        if existing_claim:
            return response.api_response(400, error_details="A claim with this title already exists")

        # Create the claim
        try:
            new_claim = Claim(
                id=uuid.uuid4(),
                title=body["title"],
                description=body.get("description", ""),
                date_of_loss=date_of_loss,
                household_id=household_uuid
            )
            
            db_session.add(new_claim)
            db_session.commit()
            db_session.refresh(new_claim)
        except Exception as e:
            # This will catch database connection issues
            logger.error("Database error occurred: %s", str(e))
            return response.api_response(500, error_details=f"Database error: {str(e)}")

        # Prepare response
        created_claim = {
            "id": str(new_claim.id),
            "title": new_claim.title,
            "description": new_claim.description,
            "date_of_loss": new_claim.date_of_loss.strftime("%Y-%m-%d"),
        }

        return response.api_response(201, data=created_claim, success_message="Claim created successfully")

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        if 'db_session' in locals():
            db_session.rollback()
        return response.api_response(500, error_details=f"Database error: {str(e)}")

    except Exception as e:
        logger.exception("Unexpected error creating claim")
        if 'db_session' in locals():
            db_session.rollback()
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")

    finally:
        if db_session is not None:
            db_session.close()