"""
Lambda handler for inheriting labels from a file to an item.

This module handles copying labels from a file to an item without 
overwriting existing labels, ensuring proper deduplication.
"""
from utils.logging_utils import get_logger
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from utils import response
from models.item import Item
from models.file import File
from models.item_labels import ItemLabel
from models.file_labels import FileLabel
from models.label import Label
from sqlalchemy.exc import SQLAlchemyError

logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Lambda handler to inherit labels from a file to an item.
    
    Args:
        event (dict): API Gateway event
        _context (dict): Lambda execution context (unused)
        db_session (Session): Database session
        user (User): Authenticated user object (provided by decorator)
        
    Returns:
        dict: API response with inheritance status or error
    """
    # Extract item_id and file_id from path parameters
    path_params = event.get("pathParameters") or {}
    
    # Extract item_id
    success, result = extract_uuid_param(path_params, "item_id")
    if not success:
        return result  # This is already an API response with error details
    item_id = result
    
    # Extract file_id
    success, result = extract_uuid_param(path_params, "file_id")
    if not success:
        return result  # This is already an API response with error details
    file_id = result
    
    try:
        # Verify the item exists and belongs to the user's household
        item = db_session.query(Item).filter(Item.id == item_id).first()
        if not item:
            return response.api_response(404, error_details="Item not found")
        
        # Verify the file exists
        file = db_session.query(File).filter(File.id == file_id).first()
        if not file:
            return response.api_response(404, error_details="File not found")
        
        # Verify the file belongs to the same claim as the item
        if file.claim_id != item.claim_id:
            return response.api_response(400, error_details="File must belong to the same claim as the item")
        
        # Get all non-deleted labels associated with the file
        file_labels = db_session.query(FileLabel, Label).join(
            Label, FileLabel.label_id == Label.id
        ).filter(
            FileLabel.file_id == file_id,
            FileLabel.deleted.is_(False)
        ).all()
        
        if not file_labels:
            return response.api_response(
                200, 
                success_message="No labels found to inherit from the file",
                data={
                    "file_id": str(file_id),
                    "item_id": str(item_id),
                    "labels_added": 0
                }
            )
        
        labels_added = 0
        
        for file_label, label in file_labels:
            # Check if this label is already associated with the item
            existing_item_label = db_session.query(ItemLabel).filter(
                ItemLabel.item_id == item_id,
                ItemLabel.label_id == label.id
            ).first()
            
            if not existing_item_label:
                # Create new association
                db_session.add(ItemLabel(item_id=item_id, label_id=label.id))
                labels_added += 1
            elif existing_item_label.deleted:
                # Reactivate deleted association
                existing_item_label.deleted = False
                labels_added += 1
        
        # Commit changes
        db_session.commit()
        
        logger.info("Inherited %s labels from file %s to item %s", labels_added, file_id, item_id)
        
        return response.api_response(
            200, 
            success_message=f"Successfully inherited {labels_added} labels from file to item",
            data={
                "file_id": str(file_id),
                "item_id": str(item_id),
                "labels_added": labels_added
            }
        )
        
    except SQLAlchemyError as e:
        logger.error("Database error while inheriting labels: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Database error occurred")
    
    except Exception as e:
        logger.error("Unexpected error while inheriting labels: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Internal server error")
