from utils.logging_utils import get_logger
from sqlalchemy.orm import joinedload
from sqlalchemy import desc

from models.item import Item
from models.claim import Claim
from utils import response
from utils.lambda_utils import enhanced_lambda_handler

# Configure logging
logger = get_logger(__name__)
@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['claim_id'],
    permissions={'resource_type': 'claim', 'action': 'read', 'path_param': 'claim_id'},
    auto_load_resources={'claim_id': 'Claim'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
    """
    Retrieves all items under a specific claim with pagination support.
    
    Parameters:
        event (dict): API Gateway event with claim ID and optional pagination parameters.
        context (dict): Lambda execution context.
        db_session (Session): SQLAlchemy session.
        user (User): Authenticated user object.
        path_params (dict): Extracted path parameters.
        resources (dict): Auto-loaded resources.
        
    Returns:
        dict: API response with paginated items list or error message.
    """
    claim = resources['claim']
    claim_uuid = claim.id

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
    
    # Fetch paginated items for the claim with eager-loaded files to avoid N+1
    items = (
        db_session.query(Item)
        .options(joinedload(Item.files))
        .filter(Item.claim_id == claim_uuid)
        .order_by(desc(Item.id))
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    items_data = []
    for item in items:
        # Get associated file IDs for this item
        file_ids = [str(file.id) for file in item.files]
        
        # Build item data with file IDs
        item_data = {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "unit_cost": item.unit_cost,
            "condition": item.condition,
            "file_ids": file_ids,  # Include associated file IDs
            "room_id": str(item.room_id) if item.room_id else None
        }
        items_data.append(item_data)
    
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
