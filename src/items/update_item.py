from utils.logging_utils import get_logger
import uuid

from models.item import Item
from models.room import Room
from utils import response
from utils.lambda_utils import enhanced_lambda_handler

# Configure logging
logger = get_logger(__name__)
@enhanced_lambda_handler(
    requires_auth=True,
    requires_body=True,
    path_params=['item_id'],
    permissions={'resource_type': 'item', 'action': 'write', 'path_param': 'item_id'},
    auto_load_resources={'item_id': 'Item'}
)
def lambda_handler(event, context, db_session, user, body, path_params, resources):
    """
    Updates an item's properties.
    
    Parameters:
        event (dict): API Gateway event with item ID and request body.
        context (dict): Lambda execution context.
        db_session (Session): SQLAlchemy session (provided by decorator).
        user (User): Authenticated user object (provided by decorator).
        body (dict): Request body (provided by decorator).
        path_params (dict): Path parameters (provided by decorator).
        resources (dict): Auto-loaded resources (provided by decorator).
        
    Returns:
        dict: API response with success or error message.
    """
    item = resources['item']
    
    try:
            
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
                    room = db_session.query(Room).filter(Room.id == room_id).first()
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
            
        db_session.commit()
        
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
        db_session.rollback()
        return response.api_response(500, error_details=f'Internal Server Error: {str(e)}')
