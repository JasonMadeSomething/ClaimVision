from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models import Claim
from database.database import get_db_session
from utils.logging_utils import get_logger


logger = get_logger(__name__)


# Configure logging
logger = get_logger(__name__)
@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, context: dict = None, db_session=None, user=None) -> dict:
    """
    Handles deleting a claim for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID.
        context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response confirming deletion or an error message.
    """
    # Extract claim ID from path parameters
    success, result = extract_uuid_param(event, "claim_id")
    if not success:
        return result  # Return error response
    
    claim_id = result
    
    try:
        db_session = db_session if db_session else get_db_session()
        logger.info("Received request for deleting a claim")

        # Query the claim
        claim = db_session.query(Claim).filter_by(id=claim_id).first()
        
        # Check if claim exists
        if not claim:
            return response.api_response(404, error_details="Claim not found")
        
        # Check if user has access to the claim (belongs to their household)
        if str(claim.household_id) != str(user.household_id):
            # Return 404 for security reasons (don't reveal that the claim exists)
            return response.api_response(404, error_details="Claim not found")

        # Delete the claim
        db_session.delete(claim)
        db_session.commit()
        
        return response.api_response(200, success_message="Claim deleted successfully")
        
    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details=f"Database error: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error deleting claim")
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")
    finally:
        if db_session is not None:
            db_session.close()