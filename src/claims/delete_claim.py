"""
Lambda handler for deleting a claim and its associated items and files.

This module handles the deletion of claims from the ClaimVision system,
ensuring proper authorization and data integrity.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models import Claim
from database.database import get_db_session


logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles deleting a claim for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID.
        _context (dict): Lambda execution context (unused).
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
        db_session.query(Claim).filter(Claim.id == claim_id).delete()
        db_session.commit()
        
        logger.info(f"Claim {claim_id} deleted successfully")
        return response.api_response(200, success_message="Claim deleted successfully")
        
    except IntegrityError as e:
        db_session.rollback()
        logger.error(f"Integrity error when deleting claim {claim_id}: {str(e)}")
        return response.api_response(500, error_details="Integrity error when deleting claim")
    except OperationalError as e:
        db_session.rollback()
        logger.error(f"Operational error when deleting claim {claim_id}: {str(e)}")
        return response.api_response(500, error_details="Operational error when deleting claim")
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error when deleting claim {claim_id}: {str(e)}")
        return response.api_response(500, error_details="Database error when deleting claim")
    except Exception as e:
        logger.exception("Unexpected error deleting claim")
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")
    finally:
        if db_session is not None:
            db_session.close()