"""
Lambda handler for deleting a claim and its associated items and files.

This module handles the soft deletion of claims from the ClaimVision system,
ensuring proper authorization and data integrity.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models import Claim
from database.database import get_db_session
from datetime import datetime, timezone
from utils.access_control import has_permission, AccessDeniedError
from utils.vocab_enums import ResourceTypeEnum, PermissionAction


logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles soft deleting a claim for the authenticated user.

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
        
        # Check if user has permission to delete the claim
        if not has_permission(
            user=user,
            action=PermissionAction.DELETE,
            resource_type=ResourceTypeEnum.CLAIM.value,
            db=db_session,
            resource_id=claim_id
        ):
            logger.warning(f"User {user.id} attempted to delete claim {claim_id} without permission")
            return response.api_response(403, error_details="You do not have access to delete this claim")

        # Perform soft delete
        try:
            # Check for an existing deleted claim with the same title in this group
            existing_deleted_claim = db_session.query(Claim).filter(
                Claim.title == claim.title,
                Claim.group_id == claim.group_id,
                Claim.deleted,  
                Claim.id != claim.id
            ).first()
            
            if existing_deleted_claim:
                # If there's already a deleted claim with the same title, hard delete it
                logger.info(f"Found existing deleted claim with same title. Hard deleting claim: {existing_deleted_claim.id}")
                db_session.delete(existing_deleted_claim)
            
            # Soft delete the current claim - only set these values if it's not already deleted
            if not claim.deleted:
                claim.deleted = True
                claim.deleted_at = datetime.now(timezone.utc)
                claim.updated_at = datetime.now(timezone.utc)
            db_session.commit()
            
            logger.info(f"Claim {claim_id} soft deleted successfully")
            return response.api_response(200, success_message="Claim deleted successfully")
        except SQLAlchemyError as e:
            logger.error(f"Database error soft deleting claim: {str(e)}")
            db_session.rollback()
            return response.api_response(500, error_details="Failed to delete claim")
        
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
    except AccessDeniedError as e:
        logger.warning(f"Access denied: {str(e)}")
        return response.api_response(403, error_details=f"Access denied: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error deleting claim")
        return response.api_response(500, error_details=f"Internal server error: {str(e)}")
    finally:
        if db_session is not None:
            db_session.close()