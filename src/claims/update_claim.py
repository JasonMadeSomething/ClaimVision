"""
Lambda handler for updating claim information.

This module handles the updating of claim details in the ClaimVision system,
ensuring proper authorization, data validation, and consistency.
"""
from utils.logging_utils import get_logger
from datetime import datetime, date
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models import Claim
from utils.access_control import has_permission, AccessDeniedError
from utils.vocab_enums import ResourceTypeEnum, PermissionAction


logger = get_logger(__name__)


# Configure logging
@standard_lambda_handler(requires_auth=True, requires_body=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None, body=None) -> dict:
    """
    Handles updating a claim by ID for the authenticated user.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID.
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.
        user (User): Authenticated user object (provided by decorator).
        body (dict): Request body containing updated claim data (provided by decorator).

    Returns:
        dict: API response containing the updated claim details or an error message.
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
        
        # Check if user has permission to update the claim
        if not has_permission(
            user=user,
            action=PermissionAction.WRITE,
            resource_type=ResourceTypeEnum.CLAIM.value,
            db=db_session,
            resource_id=claim_id
        ):
            logger.warning(f"User {user.id} attempted to update claim {claim_id} without permission")
            return response.api_response(403, error_details="You do not have access to update this claim")
        
        # Validate that only allowed fields are being updated
        allowed_fields = ["title", "description", "date_of_loss"]
        invalid_fields = [field for field in body.keys() if field not in allowed_fields]
        if invalid_fields:
            return response.api_response(400, error_details="Invalid update fields")
            
        # Validate fields
        if "title" in body and not body["title"].strip():
            return response.api_response(400, error_details="Title cannot be empty")
        
        # Check for SQL injection or invalid characters in title
        if "title" in body and ("'" in body["title"] or ";" in body["title"]):
            return response.api_response(400, error_details="Invalid characters in title")
            
        # Validate date format if provided
        if "date_of_loss" in body:
            try:
                date_of_loss = datetime.strptime(body["date_of_loss"], "%Y-%m-%d").date()
                
                # Validate date is not in the future
                if date_of_loss > date.today():
                    return response.api_response(400, error_details="Future date is not allowed")
                    
                claim.date_of_loss = date_of_loss
            except ValueError:
                return response.api_response(400, error_details="Invalid date format. Expected YYYY-MM-DD")
        
        # Update fields if provided
        if "title" in body:
            claim.title = body["title"]
            
        if "description" in body:
            claim.description = body["description"]
            
        # Update the claim
        updates = {
            "title": claim.title,
            "description": claim.description,
            "date_of_loss": claim.date_of_loss
        }
        for key, value in updates.items():
            setattr(claim, key, value)
        
        # Update the updated_at timestamp
        if hasattr(claim, 'updated_at'):
            claim.updated_at = datetime.now()
        
        # Commit the changes
        db_session.commit()
        
        # Prepare response
        updated_claim = {
            "id": str(claim.id),
            "title": claim.title,
            "description": claim.description or "",
            "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d"),
            "created_at": claim.created_at.isoformat() if hasattr(claim, 'created_at') else None,
            "updated_at": claim.updated_at.isoformat() if hasattr(claim, 'updated_at') and claim.updated_at else None
        }
        
        return response.api_response(200, data=updated_claim, success_message="Claim updated successfully")
        
    except IntegrityError as e:
        db_session.rollback()
        logger.error(f"Integrity error when updating claim {claim_id}: {str(e)}")
        return response.api_response(500, error_details="Integrity error when updating claim")
    except OperationalError as e:
        db_session.rollback()
        logger.error(f"Operational error when updating claim {claim_id}: {str(e)}")
        return response.api_response(500, error_details="Operational error when updating claim")
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error when updating claim {claim_id}: {str(e)}")
        return response.api_response(500, error_details="Database error when updating claim")
    except AccessDeniedError as e:
        logger.warning(f"Access denied: {str(e)}")
        return response.api_response(403, error_details=f"Access denied: {str(e)}")
    except Exception as e:
        logger.error("Error updating claim: %s", str(e))
        return response.api_response(500, error_details=f"Error updating claim: {str(e)}")
