from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid
from models import File
from models.room import Room
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from utils.logging_utils import get_logger


logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True, requires_body=True)
def lambda_handler(event: dict, context=None, _context=None, db_session=None, user=None, body=None) -> dict:
    """
    Handles updating metadata for a file, excluding labels.

    Args:
        event (dict): API Gateway event containing authentication details, file ID, and update data.
        context/_context (dict): Lambda execution context (unused).
        db_session (Session, optional): Database session for testing.
        user (User): Authenticated user object (provided by decorator).
        body (dict): Request body containing metadata to update.

    Returns:
        dict: API response with updated file metadata or error.
    """
    # Extract and validate file ID
    success, result = extract_uuid_param(event, "id")
    if not success:
        return result  # Return error response
        
    file_id = result
    
    # Validate request body
    if not body or len(body) == 0:
        return response.api_response(400, error_details='Empty request body')
        
    # Validate fields that can be updated
    allowed_fields = ["room_id", "metadata", "description", "tags"]
    invalid_fields = [field for field in body.keys() if field not in allowed_fields]
    if invalid_fields:
        return response.api_response(400, error_details=f"Invalid field(s): {', '.join(invalid_fields)}")
    
    # Retrieve the file, ensuring it belongs to user's household
    file_data = db_session.query(File).filter(
        File.id == file_id,
        File.household_id == user.household_id
    ).first()

    if not file_data:
        return response.api_response(404, error_details="File not found")
    
    # Update file metadata
    metadata = file_data.file_metadata or {}
    
    # Handle room_id field
    if "room_id" in body:
        room_id = body.pop("room_id")
        # If room_id is None or empty string, remove room association
        if room_id is None or room_id == "":
            file_data.room_id = None
        else:
            # Validate room_id format
            try:
                room_uuid = uuid.UUID(room_id)
                # Verify room exists and belongs to the claim
                room = db_session.query(Room).filter_by(
                    id=room_uuid, 
                    claim_id=file_data.claim_id, 
                    household_id=user.household_id
                ).first()
                if not room:
                    return response.api_response(404, error_details='Room not found or not associated with this claim.')
                file_data.room_id = room_uuid
            except ValueError:
                return response.api_response(400, error_details='Invalid room ID format. Expected UUID.')
    
    # Update remaining fields in metadata
    metadata.update(body)
    
    # Update the file record
    try:
        file_data.file_metadata = metadata
        file_data.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        
        # Get room name from relationship if room_id exists
        room_name = None
        if file_data.room_id:
            room = db_session.query(Room).filter_by(id=file_data.room_id).first()
            if room:
                room_name = room.name
        
        # Format the response
        file_response = {
            "id": str(file_data.id),
            "file_name": file_data.file_name,
            "status": file_data.status.value,
            "created_at": file_data.created_at.isoformat() if file_data.created_at else None,
            "updated_at": file_data.updated_at.isoformat() if file_data.updated_at else None,
            "claim_id": str(file_data.claim_id) if file_data.claim_id else None,
            "room_id": str(file_data.room_id) if file_data.room_id else None,
            "room_name": room_name,
            "metadata": file_data.file_metadata or {}
        }
        
        return response.api_response(200, success_message="File metadata updated successfully", data=file_response)
        
    except SQLAlchemyError as e:
        logger.error("Database error updating file metadata: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Failed to update file metadata")
