"""
Lambda handler for managing item labels.

This module handles adding and removing labels from an item.
"""
import uuid
from utils.logging_utils import get_logger
from utils.lambda_utils import enhanced_lambda_handler
from utils import response
from models.item import Item
from models.item_labels import ItemLabel
from models.label import Label
from sqlalchemy.exc import SQLAlchemyError

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
    Lambda handler to add or remove labels from an item.
    
    Args:
        event (dict): API Gateway event
        _context (dict): Lambda execution context (unused)
        db_session (Session): Database session
        user (User): Authenticated user object (provided by decorator)
        body (dict): Request body with 'add' and/or 'remove' label arrays
        
    Returns:
        dict: API response with label management status or error
    """
    item = resources['item']
    item_id = item.id
    
    # Validate request body
    add_labels = body.get("add", [])
    remove_labels = body.get("remove", [])
    
    if not add_labels and not remove_labels:
        return response.api_response(400, error_details="Request must include at least one label to add or remove")
    
    try:
        
        # Process labels to add
        labels_added = 0
        invalid_add_labels = []
        
        for label_id_str in add_labels:
            try:
                label_id = uuid.UUID(label_id_str)
                
                # Verify the label exists
                label = db_session.query(Label).filter(Label.id == label_id).first()
                if not label:
                    invalid_add_labels.append(label_id_str)
                    continue
                
                # Check if the label is already associated with the item
                existing_item_label = db_session.query(ItemLabel).filter(
                    ItemLabel.item_id == item_id,
                    ItemLabel.label_id == label_id
                ).first()
                
                if not existing_item_label:
                    # Create new association
                    db_session.add(ItemLabel(item_id=item_id, label_id=label_id, group_id=item.group_id))
                    labels_added += 1
                elif existing_item_label.deleted is True:
                    # Reactivate deleted association
                    existing_item_label.deleted = False
                    labels_added += 1
                    
            except ValueError:
                invalid_add_labels.append(label_id_str)
        
        # Process labels to remove
        labels_removed = 0
        invalid_remove_labels = []
        
        for label_id_str in remove_labels:
            try:
                label_id = uuid.UUID(label_id_str)
                
                # Check if the label is associated with the item
                existing_association = db_session.query(ItemLabel).filter(
                    ItemLabel.item_id == item_id,
                    ItemLabel.label_id == label_id,
                    ItemLabel.deleted.is_(False)
                ).first()
                
                if existing_association:
                    # Soft delete the association
                    existing_association.deleted = True
                    labels_removed += 1
                    
            except ValueError:
                invalid_remove_labels.append(label_id_str)
        
        # Commit changes
        db_session.commit()
        
        # Prepare response data
        response_data = {
            "item_id": str(item_id),
            "labels_added": labels_added,
            "labels_removed": labels_removed,
        }
        
        # Add information about invalid labels if any
        if invalid_add_labels:
            response_data["invalid_add_labels"] = invalid_add_labels
            
        if invalid_remove_labels:
            response_data["invalid_remove_labels"] = invalid_remove_labels
        
        logger.info("Updated labels for item %s: added %s, removed %s", 
                   item_id, labels_added, labels_removed)
        
        return response.api_response(
            200, 
            success_message="Labels updated successfully",
            data=response_data
        )
        
    except SQLAlchemyError as e:
        logger.error("Database error while managing item labels: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Database error occurred")
    
    except Exception as e:
        logger.error("Unexpected error while managing item labels: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Internal server error")
