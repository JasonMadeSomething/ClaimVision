from utils.logging_utils import get_logger
import uuid
from models.item import Item
from models.file import File
from models.item_files import ItemFile
from models.claim import Claim
from models.room import Room
from utils import response
from utils.access_control import has_permission
from utils.vocab_enums import ResourceTypeEnum, PermissionAction
from utils.lambda_utils import extract_uuid_param, standard_lambda_handler, enhanced_lambda_handler

# Configure logging
logger = get_logger(__name__)

@enhanced_lambda_handler(
    requires_auth=True,
    requires_body=True,
    path_params=['claim_id'],
    permissions={'resource_type': 'claim', 'action': 'write', 'path_param': 'claim_id'},
    auto_load_resources={'claim_id': 'Claim'},
    validation_schema={
        'name': {'type': str, 'max_length': 255, 'required': False},
        'unit_cost': {'type': (int, float), 'min': 0, 'required': False}
    }
)
def lambda_handler(event, context, db_session, user, body, path_params, resources):
    """
    Creates a new item under a claim. Allows blank items and file associations.

    Parameters:
        event (dict): API Gateway event with claim ID and optional item details.
        context (dict): AWS Lambda execution context.
        db_session (Session): SQLAlchemy session.
        user (User): Authenticated user object.
        body (dict): Parsed and validated request body.
        path_params (dict): Extracted path parameters.
        resources (dict): Auto-loaded resources.

    Returns:
        dict: API response confirming item creation or error message.
    """
    claim = resources['claim']
    claim_uuid = uuid.UUID(path_params['claim_id'])

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
            room = db_session.query(Room).filter(Room.id == room_id).first()
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

    db_session.add(new_item)
    db_session.flush()  # Flush to get the new item ID

    # Handle file associations if file_ids are provided
    file_ids = body.get("file_ids", [])
    if file_ids:
        for file_id_str in file_ids:
            try:
                file_id = uuid.UUID(file_id_str) if not isinstance(file_id_str, uuid.UUID) else file_id_str
            except ValueError:
                return response.api_response(400, error_details=f'Invalid file ID format: {file_id_str}')

            # Ensure file exists
            file = db_session.query(File).filter(File.id == file_id).first()
            if not file:
                return response.api_response(404, error_details=f'File not found with ID: {file_id_str}')

            # Verify the file belongs to the same claim
            if file.claim_id != claim_uuid:
                return response.api_response(400, error_details='File must belong to the same claim as the item.')

            # Create the file-item association with group_id
            db_session.add(ItemFile(item_id=new_item.id, file_id=file_id, group_id=new_item.group_id))

    # For backward compatibility, also handle single file_id if provided
    file_id_str = body.get("file_id")
    if file_id_str:
        try:
            file_id = uuid.UUID(file_id_str) if not isinstance(file_id_str, uuid.UUID) else file_id_str

            # Ensure file exists
            file = db_session.query(File).filter(File.id == file_id).first()
            if not file:
                return response.api_response(404, error_details='File not found.')

            # Verify the file belongs to the same claim
            if file.claim_id != claim_uuid:
                return response.api_response(400, error_details='File must belong to the same claim as the item.')

            # Create the file-item association with group_id
            db_session.add(ItemFile(item_id=new_item.id, file_id=file_id, group_id=new_item.group_id))
        except ValueError:
            return response.api_response(400, error_details='Invalid file ID format.')

    db_session.commit()

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
