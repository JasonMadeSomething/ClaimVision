"""
Lambda handler for retrieving a claim and its associated data.

This module handles the retrieval of claim details from the ClaimVision system,
ensuring proper authorization and data access.
"""
from sqlalchemy.exc import IntegrityError, OperationalError

from models import Claim
from utils import response
from utils.access_control import has_permission
from utils.lambda_utils import extract_uuid_param, standard_lambda_handler, enhanced_lambda_handler
from utils.logging_utils import get_logger
from utils.vocab_enums import PermissionAction, ResourceTypeEnum

logger = get_logger(__name__)

@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['claim_id'],
    permissions={'resource_type': 'claim', 'action': 'read', 'path_param': 'claim_id'},
    auto_load_resources={'claim_id': 'Claim'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
    """
    Handles retrieving a claim by ID for the authenticated user's group.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID.
        context (dict): Lambda execution context.
        db_session (Session): SQLAlchemy session.
        user (User): Authenticated user object.
        path_params (dict): Extracted path parameters.
        resources (dict): Auto-loaded resources.

    Returns:
        dict: API response containing the claim details or an error message.
    """
    claim = resources['claim']
    
    # Check if claim is soft-deleted
    if claim.deleted:
        return response.api_response(404, error_details="Claim not found")
        
        # Convert claim to dictionary for response
        claim_data = {
            "id": str(claim.id),
            "title": claim.title,
            "description": claim.description or "",
            "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d") if claim.date_of_loss else None
        }
        
        # Add created_at and updated_at if they exist
        if hasattr(claim, 'created_at') and claim.created_at:
            claim_data["created_at"] = claim.created_at.isoformat()
        
        if hasattr(claim, 'updated_at') and claim.updated_at:
            claim_data["updated_at"] = claim.updated_at.isoformat()
        
        return response.api_response(200, data=claim_data)
        
    except IntegrityError as e:
        logger.error("Database integrity error when retrieving claim %s: %s", str(claim_id), str(e))
        return response.api_response(500, error_details="Database integrity error when retrieving claim")
    except OperationalError as e:
        logger.error("Database operational error when retrieving claim %s: %s", str(claim_id), str(e))
        return response.api_response(500, error_details="Database operational error when retrieving claim")
    # Allow unanticipated exceptions to propagate to the standard handler
