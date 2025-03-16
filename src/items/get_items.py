import logging
import uuid
from sqlalchemy import desc

from database.database import get_db_session
from models.item import Item
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, _context, db_session=None):
    """
    Retrieves all items under a specific claim with pagination support.
    
    Parameters:
        event (dict): API Gateway event with claim ID and optional pagination parameters.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing.
        
    Returns:
        dict: API response with paginated items list or error message.
    """
    db = db_session if db_session else get_db_session()
    
    try:
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(400, message="Invalid authentication.")

        claim_id = event.get("pathParameters", {}).get("claim_id")
        if not claim_id:
            return response.api_response(400, message="Claim ID is required.")
            
        try:
            # Handle case where claim_id is already a UUID object
            if isinstance(claim_id, uuid.UUID):
                claim_uuid = claim_id
            else:
                claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            return response.api_response(400, message="Invalid claim ID format.")

        # Get pagination parameters from query string
        query_params = event.get("queryStringParameters") or {}
        limit = query_params.get("limit", "10")
        offset = query_params.get("offset", "0")
        
        # Validate pagination parameters
        try:
            limit = int(limit)
            offset = int(offset)
            if limit < 1 or limit > 100 or offset < 0:
                return response.api_response(400, message="Invalid pagination parameters")
        except ValueError:
            return response.api_response(400, message="Invalid pagination parameters")
        
        # Fetch total count of items for the claim
        total_items = db.query(Item).filter(Item.claim_id == claim_uuid).count()
        
        # Fetch paginated items for the claim - sort by id instead of created_at
        items = db.query(Item).filter(Item.claim_id == claim_uuid).order_by(desc(Item.id)).offset(offset).limit(limit).all()
        
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
        
        return response.api_response(200, message="Items retrieved successfully.", data=response_data)
        
    except Exception as e:
        logger.exception(f"Unexpected error retrieving items: {str(e)}")
        return response.api_response(500, message="Internal Server Error")
        
    finally:
        db.close()
