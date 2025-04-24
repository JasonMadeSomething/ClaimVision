from models.claim import Claim
from models.permissions import Permission
from utils.vocab_enums import PermissionAction, ResourceTypeEnum
from utils.lambda_utils import standard_lambda_handler
from utils.auth_utils import extract_user_id, get_authenticated_user
from utils import response
from sqlalchemy.exc import SQLAlchemyError
from utils.logging_utils import get_logger

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event, context, db_session):
    try:
        # Extract user ID from the event
        success, result = extract_user_id(event)
        if not success:
            return result  # Return error response
        
        user_id = result
        
        # Get the user from the database
        success, user_or_error = get_authenticated_user(db_session, user_id)
        if not success:
            return user_or_error  # Return error response
        user = user_or_error
        
        # Subquery: all claims this user can read
        permitted_claim_ids = db_session.query(Permission.resource_id).filter(
            Permission.subject_id == user.id,
            Permission.subject_type == "user",
            Permission.resource_type_id == ResourceTypeEnum.CLAIM.value,
            Permission.action == PermissionAction.READ.value
        ).subquery()

        claims = db_session.query(Claim).filter(
            Claim.id.in_(permitted_claim_ids),
            Claim.deleted_at.is_(None)
        ).all()

        if not claims:
            return response.api_response(200, message="No claims found", data=[])

        claims_data = [
            {
                "id": str(claim.id),
                "title": claim.title,
                "description": claim.description or "",
                "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d"),
                "created_at": claim.created_at.isoformat(),
                "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
            }
            for claim in claims
        ]

        return response.api_response(200, data=claims_data)

    except SQLAlchemyError as e:
        logger.error("Database error: %s", str(e))
        return response.api_response(500, error_details=f"Database error: {str(e)}")
    except Exception as e:
        logger.error("Error retrieving claims: %s", str(e))
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")
