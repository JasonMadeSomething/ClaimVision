import json
from utils.logging_utils import get_logger
import uuid

from database.database import get_db_session
from models.file import File
from models.item import Item
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from models.label import Label
from models.claim import Claim
from models.user import User
from utils import response

# Configure logging
logger = get_logger(__name__)
def lambda_handler(event, _context, db_session=None):
    """
    Updates an item's properties and/or associates a file with an item and specifies applicable labels.
    
    Parameters:
        event (dict): API Gateway event with item ID and request body.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing.
        
    Returns:
        dict: API response with success or error message.
    """
    db = db_session if db_session else get_db_session()
    
    try:
        # Extract user ID from event for authentication
        user_id_str = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        
        # For testing purposes, allow auth_user to be passed directly
        if not user_id_str and "auth_user" in event:
            user_id_str = event.get("auth_user")
            
        if not user_id_str:
            return response.api_response(401, error_details='Authentication required.')
            
        try:
            user_id = uuid.UUID(user_id_str) if not isinstance(user_id_str, uuid.UUID) else user_id_str
        except ValueError:
            return response.api_response(400, error_details='Invalid user ID format.')

        # Get item_id from path parameters
        item_id_str = event.get("pathParameters", {}).get("item_id")
        if not item_id_str:
            return response.api_response(400, error_details='Item ID is required.')
            
        try:
            # Handle case where item_id is already a UUID object
            if isinstance(item_id_str, uuid.UUID):
                item_id = item_id_str
            else:
                item_id = uuid.UUID(item_id_str)
        except ValueError:
            return response.api_response(400, error_details='Invalid item ID format.')

        # Parse request body
        body = json.loads(event.get("body", "{}")) if event.get("body") else {}
        
        # Ensure item exists
        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            return response.api_response(404, error_details='Item not found.')
            
        # Authorization check - verify the user has access to this item
        # Get the claim associated with this item
        claim = db.query(Claim).filter(Claim.id == item.claim_id).first()
        if not claim:
            return response.api_response(404, error_details='Associated claim not found.')
            
        # Get the user from the database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response.api_response(404, error_details='User not found.')
            
        # Check if the user's household matches the claim's household
        if user.household_id != claim.household_id:
            return response.api_response(404, error_details='Item not found.')
            
        # Handle item property updates (name, description, etc.)
        item_updated = False
        if "name" in body:
            item.name = body["name"]
            item_updated = True
            
        if "description" in body:
            item.description = body["description"]
            item_updated = True
            
        if "estimated_value" in body:
            item.estimated_value = body["estimated_value"]
            item_updated = True
            
        if "condition" in body:
            item.condition = body["condition"]
            item_updated = True
            
        if "is_ai_suggested" in body:
            item.is_ai_suggested = body["is_ai_suggested"]
            item_updated = True
            
        # Handle file and label associations if file_id is provided
        file_id_str = body.get("file_id")
        if file_id_str:
            try:
                # Handle case where file_id is already a UUID object
                if isinstance(file_id_str, uuid.UUID):
                    file_id = file_id_str
                else:
                    file_id = uuid.UUID(file_id_str)
            except ValueError:
                return response.api_response(400, error_details='Invalid file ID format.')
                
            # Ensure file exists
            file = db.query(File).filter(File.id == file_id).first()
            if not file:
                return response.api_response(404, error_details='File not found.')
                
            # Verify the file belongs to the same claim as the item
            if file.claim_id != item.claim_id:
                return response.api_response(404, error_details='File not found.')
    
            # Create the file-item association if it doesn't exist
            existing_association = db.query(ItemFile).filter(
                ItemFile.item_id == item_id, 
                ItemFile.file_id == file_id
            ).first()
            
            if not existing_association:
                db.add(ItemFile(item_id=item_id, file_id=file_id))
    
            # Process labels if provided
            selected_labels = body.get("labels", [])
            if selected_labels:
                # Remove existing label associations for this item
                db.query(ItemLabel).filter(ItemLabel.item_id == item_id).delete()
                
                # Apply selected labels
                for label_text in selected_labels:
                    label = db.query(Label).filter(Label.label_text == label_text).first()
                    if label:
                        db.add(ItemLabel(item_id=item_id, label_id=label.id))

        db.commit()
        
        # Return appropriate success message based on what was updated
        if file_id_str:
            if item_updated:
                return response.api_response(200, success_message='Item properties and file/label associations updated successfully.')
            else:
                return response.api_response(200, success_message='File associated with item and labels updated successfully.')
        else:
            return response.api_response(200, success_message='Item properties updated successfully.')

    except Exception as e:
        logger.exception("Unexpected error updating item")
        db.rollback()
        return response.api_response(500, error_details=f'Internal Server Error: {str(e)}')

    finally:
        if db_session is None and db:
            db.close()
