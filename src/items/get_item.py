from utils.logging_utils import get_logger
from models.item import Item
from models.item_labels import ItemLabel
from models.label import Label
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction

# Configure logging
logger = get_logger(__name__)
@standard_lambda_handler(requires_auth=True)
def lambda_handler(event, context=None, _context=None, db_session=None, user=None):
    """
    Retrieves an item by ID and its associated labels.

    Parameters:
        event (dict): API Gateway event with item ID.
        context/_context (dict): Lambda execution context (unused).
        db_session (Session): SQLAlchemy session (provided by decorator).
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response with item details or error message.
    """
    # Extract and validate item ID
    success, result = extract_uuid_param(event, "item_id")
    if not success:
        return result  # Return error response
        
    item_uuid = result
    
    # Fetch the item
    item = db_session.query(Item).filter(Item.id == item_uuid).first()
    
    if not item:
        return response.api_response(404, error_details='Item not found.')
    
    # Check if user has permission to view the claim this item belongs to
    if not has_permission(
        user=user,
        action=PermissionAction.READ,
        resource_type=ResourceTypeEnum.CLAIM.value,
        db=db_session,
        resource_id=item.claim_id
    ):
        return response.api_response(403, error_details='You do not have permission to access this item.')

    # Fetch associated labels
    item_labels = db_session.query(Label).join(ItemLabel, Label.id == ItemLabel.label_id).filter(ItemLabel.item_id == item_uuid).all()
    
    # Get associated file IDs
    file_ids = [str(file.id) for file in item.files]
    
    # Prepare response data
    item_data = {
        "id": str(item.id),
        "name": item.name,
        "description": item.description,
        "unit_cost": item.unit_cost,
        "condition": item.condition,
        "room_id": str(item.room_id) if item.room_id else None,
        "file_ids": file_ids,  
        "labels": [
            {
                "id": str(label.id),
                "text": label.label_text,
                "is_ai_generated": label.is_ai_generated
            } for label in item_labels
        ]
    }

    return response.api_response(200, success_message='Item retrieved successfully.', data=item_data)
