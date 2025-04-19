import json
from utils.logging_utils import get_logger
import uuid

from database.database import get_db_session
from models.item import Item
from models.claim import Claim
from models.user import User
from models.room import Room
from utils import response

# Configure logging
logger = get_logger(__name__)
def lambda_handler(event, _context, db_session=None):
    """
    Updates an item's properties.
    
    Parameters:
        event (dict): API Gateway event with item ID and request body.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing.
        
    Returns:
        dict: API response with success or error message.
    """
    db = db_session if db_session else get_db_session()
    
    try:
        # Extract user ID from event for authentication
        user_id_str = event.get("requestContext", {}).get("authorizer", {}).get("user_id")
        
        # For testing purposes, allow auth_user to be passed directly
        if not user_id_str and "auth_user" in event:
            user_id_str = event.get("auth_user")
            
        if not user_id_str:
            return response.api_response(401, error_details='Authentication required.')
            
        try:
            user_id = uuid.UUID(user_id_str) if not isinstance(user_id_str, uuid.UUID) else user_id_str
        except ValueError:
            return response.api_response(400, error_details='Invalid user ID format.')

        # Get item_id from path parameters
        item_id_str = event.get("pathParameters", {}).get("item_id")
        if not item_id_str:
            return response.api_response(400, error_details='Item ID is required.')
            
        try:
            # Handle case where item_id is already a UUID object
            if isinstance(item_id_str, uuid.UUID):
                item_id = item_id_str
            else:
                item_id = uuid.UUID(item_id_str)
        except ValueError:
            return response.api_response(400, error_details='Invalid item ID format.')

        # Parse request body
        body = json.loads(event.get("body", "{}")) if event.get("body") else {}
        
        # Ensure item exists
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            return response.api_response(404, error_details='Item not found.')
            
        # Authorization check - verify the user has access to this item
        # Get the claim associated with this item
        claim = db.query(Claim).filter(Claim.id == item.claim_id).first()
        if not claim:
            return response.api_response(404, error_details='Associated claim not found.')
            
        # Get the user from the database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response.api_response(404, error_details='User not found.')
            
        # Check if the user's household matches the claim's household
        if user.household_id != claim.household_id:
            return response.api_response(404, error_details='Item not found.')
            
        # Handle item property updates (name, description, etc.)
        item_updated = False
        if "name" in body:
            item.name = body["name"]
            item_updated = True
            
        if "description" in body:
            item.description = body["description"]
            item_updated = True
            
        if "unit_cost" in body:
            item.unit_cost = body["unit_cost"]
            item_updated = True
            
        if "condition" in body:
            item.condition = body["condition"]
            item_updated = True
            
        if "brand_manufacturer" in body:
            item.brand_manufacturer = body["brand_manufacturer"]
            item_updated = True
            
        if "model_number" in body:
            item.model_number = body["model_number"]
            item_updated = True
            
        if "original_vendor" in body:
            item.original_vendor = body["original_vendor"]
            item_updated = True
            
        if "quantity" in body:
            item.quantity = body["quantity"]
            item_updated = True
            
        if "age_years" in body:
            item.age_years = body["age_years"]
            item_updated = True
            
        if "age_months" in body:
            item.age_months = body["age_months"]
            item_updated = True
            
        # Handle room_id updates
        if "room_id" in body:
            room_id_str = body["room_id"]
            
            # If room_id is None, remove room association
            if room_id_str is None:
                item.room_id = None
                item_updated = True
            else:
                try:
                    # Handle case where room_id is already a UUID object
                    if isinstance(room_id_str, uuid.UUID):
                        room_id = room_id_str
                    else:
                        room_id = uuid.UUID(room_id_str)
                        
                    # Verify the room exists and belongs to the same claim
                    room = db.query(Room).filter(Room.id == room_id).first()
                    if not room:
                        return response.api_response(404, error_details='Room not found.')
                        
                    # Verify the room belongs to the same claim as the item
                    if room.claim_id != item.claim_id:
                        return response.api_response(400, error_details='Room must belong to the same claim as the item.')
                        
                    # Update the item's room_id
                    item.room_id = room_id
                    item_updated = True
                    
                except ValueError:
                    return response.api_response(400, error_details='Invalid room ID format.')
        
        # Check if any updates were made
        if not item_updated:
            return response.api_response(400, error_details='No updates provided.')
            
        db.commit()
        
        # Prepare response data with updated item information
        response_data = {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "unit_cost": item.unit_cost,
            "condition": item.condition,
            "is_ai_suggested": item.is_ai_suggested,
            "brand_manufacturer": item.brand_manufacturer,
            "model_number": item.model_number,
            "original_vendor": item.original_vendor,
            "quantity": item.quantity,
            "age_years": item.age_years,
            "age_months": item.age_months,
            "claim_id": str(item.claim_id)
        }
        
        # Include room_id in response if it exists
        if item.room_id:
            response_data["room_id"] = str(item.room_id)
        
        return response.api_response(200, success_message='Item properties updated successfully.', data=response_data)

    except Exception as e:
        logger.exception("Unexpected error updating item")
        db.rollback()
        return response.api_response(500, error_details=f'Internal Server Error: {str(e)}')

    finally:
        if db_session is None and db:
            db.close()
