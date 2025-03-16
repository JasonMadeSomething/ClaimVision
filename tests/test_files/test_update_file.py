import json
import uuid
import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from models import File, Household, User, Room, Claim
from files.update_file_metadata import lambda_handler
from datetime import datetime

@pytest.fixture
def seed_file(test_db):
    """Insert a test file into the database for metadata updates."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    room_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id
    )
    
    test_claim = Claim(
        id=claim_id,
        household_id=household_id,
        title="Test Claim",
        date_of_loss=datetime(2023, 1, 1)
    )
    
    test_room = Room(
        id=room_id,
        name="Living Room",
        description="Main living area",
        household_id=household_id,
        claim_id=claim_id
    )

    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        file_name="original.jpg",
        s3_key="original-key",
        file_metadata={"mime_type": "image/jpeg", "size": 12345},
        claim_id=claim_id,
        file_hash="test_hash"
    )

    test_db.add_all([test_household, test_user, test_claim, test_room, test_file])
    test_db.commit()

    return file_id, user_id, household_id, room_id, claim_id

def test_update_file_metadata_success(api_gateway_event, test_db, seed_file):
    """ Test updating file metadata successfully."""
    file_id, user_id, _, room_id, _ = seed_file
    update_payload = {"room_id": str(room_id)}
    
    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": str(file_id)},
        body=json.dumps(update_payload),
        auth_user=str(user_id)
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    print(body)
    
    assert response["statusCode"] == 200
    assert body["data"]["room_id"] == str(room_id)
    assert "room_name" in body["data"]  # Room name should be included in response

def test_update_file_metadata_not_found(api_gateway_event, test_db, seed_file):
    """ Test updating metadata for a non-existent file (should return 404)."""
    _, user_id, _, room_id, _ = seed_file
    update_payload = {"room_id": str(room_id)}

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": str(uuid.uuid4())},
        body=json.dumps(update_payload),
        auth_user=str(user_id)
    )

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 404

def test_update_file_metadata_unauthorized(api_gateway_event, test_db, seed_file):
    """ Test unauthorized user trying to update metadata (should return 404)."""
    file_id, _, _, room_id, _ = seed_file
    unauthorized_user_id = uuid.uuid4()
    update_payload = {"room_id": str(room_id)}

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": str(file_id)},
        body=json.dumps(update_payload),
        auth_user=str(unauthorized_user_id)
    )

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 404

def test_update_file_metadata_invalid_field(api_gateway_event, test_db, seed_file):
    """ Test attempting to update an invalid field (should return 400)."""
    file_id, user_id, _, _, _ = seed_file
    update_payload = {"invalid_field": "Invalid Data"}

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": str(file_id)},
        body=json.dumps(update_payload),
        auth_user=str(user_id)
    )

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 400

def test_update_file_metadata_empty_payload(api_gateway_event, test_db, seed_file):
    """ Test updating metadata with an empty payload (should return 400)."""
    file_id, user_id, _, _, _ = seed_file
    update_payload = {}

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": str(file_id)},
        body=json.dumps(update_payload),
        auth_user=str(user_id)
    )

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 400

def test_update_file_metadata_database_error(api_gateway_event, test_db, seed_file):
    """ Test handling a database error during metadata update (should return 500)."""
    file_id, user_id, _, room_id, _ = seed_file
    update_payload = {"room_id": str(room_id)}

    event = api_gateway_event(
        http_method="PATCH",
        path_params={"id": str(file_id)},
        body=json.dumps(update_payload),
        auth_user=str(user_id)
    )

    with patch.object(test_db, 'commit', side_effect=SQLAlchemyError("Test DB Error")):
        response = lambda_handler(event, {}, db_session=test_db)
        assert response["statusCode"] == 500