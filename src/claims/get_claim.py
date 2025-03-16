from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models import Claim
from utils.logging_utils import get_logger


logger = get_logger(__name__)


# Configure logging
logger = get_logger(__name__)
@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, context: dict = None, db_session=None, user=None) -> dict:
    """
    Handles retrieving a claim by ID for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID.
        context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response containing the claim details or an error message.
    """
    # Extract claim ID from path parameters
    success, result = extract_uuid_param(event, "claim_id")
    if not success:
        return result  # Return error response
    
    claim_id = result
    
    try:
        # Query the claim
        claim = db_session.query(Claim).filter_by(id=claim_id).first()
        
        # Check if claim exists
        if not claim:
            return response.api_response(404, error_details="Claim not found")
        
        # Check if user has access to the claim (belongs to their household)
        if str(claim.household_id) != str(user.household_id):
            # Return 404 for security reasons (don't reveal that the claim exists)
            return response.api_response(404, error_details="Claim not found")
        
        # Prepare response
        claim_data = {
            "id": str(claim.id),
            "title": claim.title,
            "description": claim.description or "",
            "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d"),
            "created_at": claim.created_at.isoformat() if hasattr(claim, 'created_at') else None,
            "updated_at": claim.updated_at.isoformat() if hasattr(claim, 'updated_at') and claim.updated_at else None,
            "household_id": str(claim.household_id)
        }
        
        return response.api_response(200, data=claim_data)
        
    except SQLAlchemyError as e:
        logger.error("Database error: %s", str(e))
        return response.api_response(500, error_details=f"Database error: {str(e)}")
    except Exception as e:
        logger.error("Error retrieving claim: %s", str(e))
        return response.api_response(500, error_details=f"Error retrieving claim: {str(e)}")

    if db_session is None and 'db_session' in locals():
        db_session.close()
