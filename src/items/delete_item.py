from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from models.item import Item
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from utils import response
from utils.lambda_utils import enhanced_lambda_handler
import uuid

# Configure logging
logger = get_logger(__name__)
@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['item_id'],
    permissions={'resource_type': 'item', 'action': 'write', 'path_param': 'item_id'},
    auto_load_resources={'item_id': 'Item'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
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
    item = resources['item']
    item_uuid = uuid.UUID(path_params['item_id'])

    try:

        # Remove file associations (but keep files intact)
        db_session.query(ItemFile).filter(ItemFile.item_id == item_uuid).delete()

        # Remove label associations for this item
        db_session.query(ItemLabel).filter(ItemLabel.item_id == item_uuid).delete()

        # Delete item itself
        db_session.delete(item)
        db_session.commit()

        logger.info(f"Deleted item {item_uuid} and cleared file/label associations.")
        return response.api_response(200, success_message='Item deleted successfully.', data={"item_id": str(item_uuid)})

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error deleting item: {str(e)}")
        return response.api_response(500, error_details='Database error.')

    except Exception as e:
        logger.exception(f"Unexpected error deleting item: {str(e)}")
        return response.api_response(500, error_details='Internal Server Error')

