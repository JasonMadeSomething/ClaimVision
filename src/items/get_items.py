from utils.logging_utils import get_logger
from sqlalchemy import desc

from models.item import Item
from models.claim import Claim
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param

# Configure logging
logger = get_logger(__name__)
@standard_lambda_handler(requires_auth=True)
def lambda_handler(event, context=None, _context=None, db_session=None, user=None):
    """
    Retrieves all items under a specific claim with pagination support.
    
    Parameters:
        event (dict): API Gateway event with claim ID and optional pagination parameters.
        context/_context (dict): Lambda execution context (unused).
        db_session (Session): SQLAlchemy session (provided by decorator).
        user (User): Authenticated user object (provided by decorator).
        
    Returns:
        dict: API response with paginated items list or error message.
    """
    # Extract and validate claim ID
    success, result = extract_uuid_param(event, "claim_id")
    if not success:
        return result  # Return error response
        
    claim_uuid = result
    
    # Verify the claim exists and belongs to the user's household
    claim = db_session.query(Claim).filter(
        Claim.id == claim_uuid,
        Claim.household_id == user.household_id
    ).first()
    
    if not claim:
        return response.api_response(404, error_details='Claim not found.')

    # Get pagination parameters from query string
    query_params = event.get("queryStringParameters") or {}
    limit = query_params.get("limit", "10")
    offset = query_params.get("offset", "0")
    
    # Validate pagination parameters
    try:
        limit = int(limit)
        offset = int(offset)
        if limit < 1 or limit > 100 or offset < 0:
            return response.api_response(400, error_details='Invalid pagination parameters')
    except ValueError:
        return response.api_response(400, error_details='Invalid pagination parameters')
    
    # Fetch total count of items for the claim
    total_items = db_session.query(Item).filter(Item.claim_id == claim_uuid).count()
    
    # Fetch paginated items for the claim - sort by id instead of created_at
    items = db_session.query(Item).filter(Item.claim_id == claim_uuid).order_by(desc(Item.id)).offset(offset).limit(limit).all()
    
    items_data = [{
        "id": str(item.id),
        "name": item.name,
        "description": item.description,
        "estimated_value": item.estimated_value,
        "condition": item.condition
    } for item in items]
    
    # Return response with pagination metadata matching files endpoint format
    response_data = {
        "items": items_data,
        "pagination": {
            "total": total_items,
            "limit": limit,
            "offset": offset
        }
    }
    
    return response.api_response(200, success_message='Items retrieved successfully', data=response_data)
