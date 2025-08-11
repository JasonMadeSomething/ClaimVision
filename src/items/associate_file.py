"""
Lambda handler for associating a file with an item.

This module handles creating an association between a file and an item,
with optional seeding of labels from the file to the item.
"""
import uuid
from utils.logging_utils import get_logger
from utils.lambda_utils import enhanced_lambda_handler
from utils import response
from models.item import Item
from models.file import File
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from models.file_labels import FileLabel
from models.label import Label
from sqlalchemy.exc import SQLAlchemyError

logger = get_logger(__name__)

@enhanced_lambda_handler(
    requires_auth=True,
    requires_body=True,
    path_params=['item_id'],
    permissions={'resource_type': 'item', 'action': 'write', 'path_param': 'item_id'},
    auto_load_resources={'item_id': 'Item'},
    required_fields=['file_id']
)
def lambda_handler(event, context, db_session, user, body, path_params, resources):
    """
    Lambda handler to associate a file with an item.
    
    Args:
        event (dict): API Gateway event
        _context (dict): Lambda execution context (unused)
        db_session (Session): Database session
        user (User): Authenticated user object (provided by decorator)
        body (dict): Request body
        
    Returns:
        dict: API response with association status or error
    """
    item = resources['item']
    item_id = item.id
    
    # Extract file_id from body (already validated by decorator)
    try:
        file_id = uuid.UUID(body['file_id'])
    except ValueError:
        return response.api_response(400, error_details="Invalid file ID format")
    
    # Check if seed_labels is provided (defaults to False)
    seed_labels = body.get("seed_labels", False)
    
    try:
        # Item already loaded by decorator
        
        # Verify the file exists and belongs to the user's household
        file = db_session.query(File).filter(File.id == file_id).first()
        if not file:
            return response.api_response(404, error_details="File not found")
        
        # Verify the file belongs to the same claim as the item
        if file.claim_id != item.claim_id:
            return response.api_response(400, error_details="File must belong to the same claim as the item")
        
        # Check if the association already exists
        existing_association = db_session.query(ItemFile).filter(
            ItemFile.item_id == item_id,
            ItemFile.file_id == file_id
        ).first()
        
        if existing_association:
            # Association already exists, return success
            logger.info("File %s is already associated with item %s", file_id, item_id)
            
            # If seed_labels is True, proceed with label seeding even if association exists
            if not seed_labels:
                # Return current label count and already_associated flag for better UX
                current_label_count = db_session.query(ItemLabel).filter(
                    ItemLabel.item_id == item_id,
                    ItemLabel.deleted.is_(False)
                ).count()
                return response.api_response(
                    200,
                    success_message="File is already associated with this item",
                    data={
                        "item_id": str(item_id),
                        "file_id": str(file_id),
                        "already_associated": True,
                        "label_count": current_label_count,
                    },
                )
        else:
            # Create the association
            db_session.add(ItemFile(item_id=item_id, file_id=file_id, group_id=item.group_id))
            logger.info("Created association between file %s and item %s", file_id, item_id)
        
        # If seed_labels is True, copy labels from file to item
        if seed_labels:
            # Get all non-deleted labels associated with the file
            file_labels = db_session.query(FileLabel, Label).join(
                Label, FileLabel.label_id == Label.id
            ).filter(
                FileLabel.file_id == file_id,
                FileLabel.deleted.is_(False)
            ).all()
            
            labels_added = 0
            
            for file_label, label in file_labels:
                # Check if this label is already associated with the item
                existing_item_label = db_session.query(ItemLabel).filter(
                    ItemLabel.item_id == item_id,
                    ItemLabel.label_id == label.id
                ).first()
                
                if not existing_item_label:
                    # Create new association
                    db_session.add(ItemLabel(item_id=item_id, label_id=label.id, group_id=item.group_id))
                    labels_added += 1
                elif existing_item_label.deleted:
                    # Reactivate deleted association
                    existing_item_label.deleted = False
                    labels_added += 1
            
            logger.info("Added %s labels from file %s to item %s", labels_added, file_id, item_id)
            
            # Commit changes
            db_session.commit()
            
            return response.api_response(
                200, 
                success_message="File associated with item and labels seeded",
                data={
                    "file_id": str(file_id),
                    "item_id": str(item_id),
                    "labels_added": labels_added,
                    "already_associated": bool(existing_association),
                }
            )
        
        # Commit changes
        db_session.commit()
        
        return response.api_response(
            200, 
            success_message="File associated with item",
            data={
                "file_id": str(file_id),
                "item_id": str(item_id)
            }
        )
        
    except SQLAlchemyError as e:
        logger.error("Database error while associating file with item: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Database error occurred")
    
    except Exception as e:
        logger.error("Unexpected error while associating file with item: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Internal server error")
