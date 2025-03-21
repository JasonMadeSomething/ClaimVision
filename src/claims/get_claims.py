from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from utils import response
from utils.lambda_utils import standard_lambda_handler
from models import Claim


logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(_event: dict, _context: dict = None, db_session=None, user=None) -> dict:
    """
    Handles retrieving all claims for the authenticated user's household.

    Args:
        _event (dict): API Gateway event containing authentication details (unused).
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response containing the list of claims or an error message.
    """
    try:
        # Get all claims for the user's household, excluding soft-deleted claims
        claims = db_session.query(Claim).filter_by(
            household_id=user.household_id,
            deleted=False
        ).all()
        
        # Format claims for response
        claims_data = []
        for claim in claims:
            claims_data.append({
                "id": str(claim.id),
                "title": claim.title,
                "description": claim.description or "",
                "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d"),
                "created_at": claim.created_at.isoformat() if hasattr(claim, 'created_at') else None,
                "updated_at": claim.updated_at.isoformat() if hasattr(claim, 'updated_at') and claim.updated_at else None,
                "household_id": str(claim.household_id)
            })
        
        return response.api_response(200, data=claims_data)
        
    except SQLAlchemyError as e:
        logger.error("Database error: %s", str(e))
        return response.api_response(500, error_details=f"Database error: {str(e)}")
    except Exception as e:
        logger.error("Error retrieving claims: %s", str(e))
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")
