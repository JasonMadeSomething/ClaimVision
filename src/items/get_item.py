from utils.logging_utils import get_logger
from sqlalchemy.orm import joinedload
from models.item import Item
from models.item_labels import ItemLabel
from models.label import Label
from utils import response
from utils.lambda_utils import enhanced_lambda_handler

# Configure logging
logger = get_logger(__name__)
@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['item_id'],
    permissions={'resource_type': 'item', 'action': 'read', 'path_param': 'item_id'},
    auto_load_resources={'item_id': 'Item'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
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
    item = resources['item']
    item_uuid = item.id
    
    # Reload item with eager-loaded files to avoid N+1
    item = (
        db_session.query(Item)
        .options(joinedload(Item.files))
        .filter(Item.id == item_uuid)
        .first()
    )

    # Fetch associated labels (exclude soft-deleted)
    item_labels = (
        db_session.query(Label)
        .join(ItemLabel, Label.id == ItemLabel.label_id)
        .filter(
            ItemLabel.item_id == item_uuid,
            ItemLabel.deleted.is_(False)
        )
        .all()
    )
    
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
