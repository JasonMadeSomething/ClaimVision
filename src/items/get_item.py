import logging
import uuid
from database.database import get_db_session
from models.item import Item
from models.item_labels import ItemLabel
from models.label import Label
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, _context, db_session=None):
    """
    Retrieves an item by ID and its associated labels.

    Parameters:
        event (dict): API Gateway event with item ID.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing.

    Returns:
        dict: API response with item details or error message.
    """
    db = db_session if db_session else get_db_session()
    
    try:
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(400, message="Invalid authentication.")

        item_id = event.get("pathParameters", {}).get("item_id")
        if not item_id:
            return response.api_response(400, message="Item ID is required.")

        try:
            # Handle case where item_id is already a UUID object
            if isinstance(item_id, uuid.UUID):
                item_uuid = item_id
            else:
                item_uuid = uuid.UUID(item_id)
        except ValueError:
            return response.api_response(400, message="Invalid item ID format.")

        # Fetch the item
        item = db.query(Item).filter(Item.id == item_uuid).first()
        if not item:
            return response.api_response(404, message="Item not found.")

        # Fetch associated labels
        item_labels = db.query(Label).join(ItemLabel, Label.id == ItemLabel.label_id).filter(ItemLabel.item_id == item_uuid).all()
        
        # Prepare response data
        item_data = {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "estimated_value": item.estimated_value,
            "condition": item.condition,
            "labels": [
                {
                    "id": str(label.id),
                    "text": label.label_text,
                    "is_ai_generated": label.is_ai_generated
                } for label in item_labels
            ]
        }

        return response.api_response(200, message="Item retrieved successfully.", data=item_data)

    except Exception as e:
        logger.exception(f"Unexpected error retrieving item: {str(e)}")
        return response.api_response(500, message="Internal Server Error")

    finally:
        db.close()
