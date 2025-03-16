import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models.item import Item
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, _context, db_session: Session = None):
    """
    Deletes an item, removing all file and label associations but preserving files.

    Parameters:
        event (dict): API Gateway event with item ID.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing.

    Returns:
        dict: API response confirming deletion or error message.
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
            item_uuid = uuid.UUID(item_id)
        except ValueError:
            return response.api_response(400, message="Invalid item ID format.")

        # ✅ Fetch item
        item = db.query(Item).filter(Item.id == item_uuid).first()
        if not item:
            return response.api_response(404, message="Item not found.")

        # ✅ Remove file associations (but keep files intact)
        db.query(ItemFile).filter(ItemFile.item_id == item_uuid).delete()

        # ✅ Remove label associations for this item
        db.query(ItemLabel).filter(ItemLabel.item_id == item_uuid).delete()

        # ✅ Delete item itself
        db.delete(item)
        db.commit()

        logger.info(f"Deleted item {item_id} and cleared file/label associations.")
        return response.api_response(204, message="Item deleted successfully.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting item: {str(e)}")
        return response.api_response(500, message="Database error.")

    except Exception as e:
        logger.exception("Unexpected error deleting item")
        return response.api_response(500, message="Internal Server Error")

    finally:
        db.close()
