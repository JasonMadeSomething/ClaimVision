from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from models.item import Item
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param

# Configure logging
logger = get_logger(__name__)
@standard_lambda_handler(requires_auth=True)
def lambda_handler(event, context=None, _context=None, db_session=None, user=None):
    """
    Deletes an item, removing all file and label associations but preserving files.

    Parameters:
        event (dict): API Gateway event with item ID.
        context/_context (dict): Lambda execution context (unused).
        db_session (Session): SQLAlchemy session (provided by decorator).
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response confirming deletion or error message.
    """
    # Extract and validate item ID
    success, result = extract_uuid_param(event, "item_id")
    if not success:
        return result  # Return error response
        
    item_uuid = result

    try:
        # Fetch item
        item = db_session.query(Item).filter(Item.id == item_uuid).first()
        if not item:
            return response.api_response(404, error_details='Item not found.')

        # Remove file associations (but keep files intact)
        db_session.query(ItemFile).filter(ItemFile.item_id == item_uuid).delete()

        # Remove label associations for this item
        db_session.query(ItemLabel).filter(ItemLabel.item_id == item_uuid).delete()

        # Delete item itself
        db_session.delete(item)
        db_session.commit()

        logger.info(f"Deleted item {item_uuid} and cleared file/label associations.")
        return response.api_response(204, success_message='Item deleted successfully.')

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error deleting item: {str(e)}")
        return response.api_response(500, error_details='Database error.')

    except Exception as e:
        logger.exception(f"Unexpected error deleting item: {str(e)}")
        return response.api_response(500, error_details='Internal Server Error')

    finally:
        db_session.close()
