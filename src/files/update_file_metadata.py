from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid
from models import File
from models.room import Room
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param, enhanced_lambda_handler
from utils.logging_utils import get_logger
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction


logger = get_logger(__name__)

@enhanced_lambda_handler(
    requires_auth=True,
    requires_body=True,
    path_params=['file_id'],
    auto_load_resources={'file_id': 'File'},
    validation_schema={
        'room_id': {'type': str, 'required': False}
    }
)
def lambda_handler(event, context, db_session, user, body, path_params, resources):
    """
    Handles updating the room association for a file.

    Args:
        event (dict): API Gateway event containing authentication details, file ID, and update data.
        context/_context (dict): Lambda execution context (unused).
        db_session (Session, optional): Database session for testing.
        user (User): Authenticated user object (provided by decorator).
        body (dict): Request body containing room_id to update.

    Returns:
        dict: API response with updated file metadata or error.
    """
    # Extract and validate file ID
    success, result = extract_uuid_param(event, "file_id")
    if not success:
        return result  # Return error response
        
    file_id = result
    
    # Validate request body
    if not body or len(body) == 0:
        return response.api_response(400, error_details='Empty request body')
        
    # Validate fields that can be updated
    allowed_fields = ["room_id"]
    invalid_fields = [field for field in body.keys() if field not in allowed_fields]
    if invalid_fields:
        return response.api_response(400, error_details=f"Invalid field(s): {', '.join(invalid_fields)}")
    
    # Retrieve the file
    file_data = db_session.query(File).filter(
        File.id == file_id
    ).first()

    if not file_data:
        return response.api_response(404, error_details="File not found")
    
    # Check if user has edit permission on the claim
    if not has_permission(
        user=user,
        action=PermissionAction.WRITE,
        resource_type=ResourceTypeEnum.CLAIM.value,
        db=db_session,
        resource_id=file_data.claim_id
    ):
        return response.api_response(403, error_details="You do not have permission to update files in this claim")
    
    # Handle room_id field
    if "room_id" in body:
        room_id = body["room_id"]
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
                    claim_id=file_data.claim_id
                ).first()
                if not room:
                    return response.api_response(404, error_details='Room not found or not associated with this claim.')
                file_data.room_id = room_uuid
            except ValueError:
                return response.api_response(400, error_details='Invalid room ID format. Expected UUID.')
    
    # Update the file record
    try:
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
        
        return response.api_response(200, success_message="File room updated successfully", data=file_response)
        
    except SQLAlchemyError as e:
        logger.error("Database error updating file room: %s", str(e))
        db_session.rollback()
        return response.api_response(500, error_details="Failed to update file room")
