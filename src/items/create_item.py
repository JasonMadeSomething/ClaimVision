import json
from utils.logging_utils import get_logger
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models.item import Item
from models.file import File
from models.item_files import ItemFile
from models.claim import Claim
from models.user import User
from models.room import Room
from utils import response
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction
from utils.auth_utils import extract_user_id

# Configure logging
logger = get_logger(__name__)
def lambda_handler(event, _context, db_session: Session = None):
    """
    Creates a new item under a claim. Allows blank items and file associations.

    Parameters:
        event (dict): API Gateway event with claim ID and optional item details.
        _context (dict): AWS Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing.

    Returns:
        dict: API response confirming item creation or error message.
    """
    db = db_session if db_session else get_db_session()
    
    try:
        # Get the authenticated user ID using the same method as create_claim.py
        success, user_id_or_response = extract_user_id(event)
        if not success:
            return user_id_or_response
        
        user_id = user_id_or_response
        
        if not user_id:
            logger.error("Invalid authentication: user_id not found in request context")
            return response.api_response(400, error_details='Invalid authentication.')
        
        claim_id = event.get("pathParameters", {}).get("claim_id")
        if not claim_id:
            logger.error("Claim ID is required but not provided")
            return response.api_response(400, error_details='Claim ID is required.')

        try:
            claim_uuid = uuid.UUID(claim_id)
        except ValueError:
            return response.api_response(400, error_details='Invalid claim ID format.')
            
        # Verify the claim exists
        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
        if not claim:
            return response.api_response(404, error_details='Claim not found.')
            
        # Get the user from the database (using cognito_sub like in create_claim.py)
        user = db.query(User).filter(User.cognito_sub == user_id).first()
        if not user:
            return response.api_response(404, error_details='User not found.')
            
        # Check if user has permission to edit this claim
        if not has_permission(
            user=user,
            action=PermissionAction.WRITE,
            resource_type=ResourceTypeEnum.CLAIM.value,
            db=db,
            resource_id=claim_uuid
        ):
            return response.api_response(403, error_details='You do not have permission to create items in this claim.')

        body = json.loads(event.get("body", "{}"))

        # ✅ Allow blank items (default values assigned if missing)
        name = body.get("name", "New Item")
        description = body.get("description", None)
        unit_cost = body.get("unit_cost", None)
        condition = body.get("condition", None)
        is_ai_suggested = body.get("is_ai_suggested", False)
        
        # Handle room_id if provided
        room_id = None
        room_id_str = body.get("room_id")
        if room_id_str:
            try:
                room_id = uuid.UUID(room_id_str) if not isinstance(room_id_str, uuid.UUID) else room_id_str
                
                # Verify the room exists and belongs to the same claim
                room = db.query(Room).filter(Room.id == room_id).first()
                if not room:
                    return response.api_response(404, error_details='Room not found.')
                    
                # Verify the room belongs to the same claim
                if room.claim_id != claim_uuid:
                    return response.api_response(400, error_details='Room must belong to the same claim.')
                    
            except ValueError:
                return response.api_response(400, error_details='Invalid room ID format.')

        # ✅ Create new item
        # Use the claim's group_id for the item to ensure consistency
        new_item = Item(
            claim_id=claim_uuid,
            name=name,
            description=description,
            unit_cost=unit_cost,
            condition=condition,
            is_ai_suggested=is_ai_suggested,
            room_id=room_id,
            group_id=claim.group_id  # Set the group_id from the claim
        )

        db.add(new_item)
        db.flush()  # Flush to get the new item ID
        
        # Handle file associations if file_ids are provided
        file_ids = body.get("file_ids", [])
        if file_ids:
            for file_id_str in file_ids:
                try:
                    file_id = uuid.UUID(file_id_str) if not isinstance(file_id_str, uuid.UUID) else file_id_str
                except ValueError:
                    return response.api_response(400, error_details=f'Invalid file ID format: {file_id_str}')
                    
                # Ensure file exists
                file = db.query(File).filter(File.id == file_id).first()
                if not file:
                    return response.api_response(404, error_details=f'File not found with ID: {file_id_str}')
                    
                # Verify the file belongs to the same claim
                if file.claim_id != claim_uuid:
                    return response.api_response(400, error_details='File must belong to the same claim as the item.')
                    
                # Create the file-item association
                db.add(ItemFile(item_id=new_item.id, file_id=file_id))
        
        # For backward compatibility, also handle single file_id if provided
        file_id_str = body.get("file_id")
        if file_id_str:
            try:
                file_id = uuid.UUID(file_id_str) if not isinstance(file_id_str, uuid.UUID) else file_id_str
                
                # Ensure file exists
                file = db.query(File).filter(File.id == file_id).first()
                if not file:
                    return response.api_response(404, error_details='File not found.')
                    
                # Verify the file belongs to the same claim
                if file.claim_id != claim_uuid:
                    return response.api_response(400, error_details='File must belong to the same claim as the item.')
                    
                # Create the file-item association
                db.add(ItemFile(item_id=new_item.id, file_id=file_id))
            except ValueError:
                return response.api_response(400, error_details='Invalid file ID format.')
        
        db.commit()
        
        # Prepare response data with item information
        response_data = {
            "id": str(new_item.id),
            "name": new_item.name,
            "description": new_item.description,
            "unit_cost": new_item.unit_cost,
            "condition": new_item.condition,
            "is_ai_suggested": new_item.is_ai_suggested,
            "claim_id": str(new_item.claim_id)
        }
        
        # Include room_id in response if it exists
        if new_item.room_id:
            response_data["room_id"] = str(new_item.room_id)

        return response.api_response(201, success_message='Item created successfully.', data=response_data)

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating item: {str(e)}")
        return response.api_response(500, error_details='Database error.')

    except Exception:
        db.rollback()
        logger.exception("Unexpected error creating item")
        return response.api_response(500, error_details='Internal Server Error')

    finally:
        db.close()
