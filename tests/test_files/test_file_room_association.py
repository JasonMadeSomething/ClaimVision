import json
import uuid
import pytest
import base64
from unittest.mock import patch, MagicMock
from files.upload_file import lambda_handler as upload_file_handler
from files.update_file_metadata import lambda_handler as update_file_handler
from models.room import Room
from models.claim import Claim
from models.household import Household
from models.user import User
from models.file import File
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing"""
    with patch("boto3.client") as mock_get_client:
        s3_mock = MagicMock()
        mock_get_client.return_value = s3_mock
        s3_mock.put_object.return_value = {"ETag": "test-etag"}
        yield s3_mock

def test_upload_file_with_room(test_db, api_gateway_event, mock_s3_client):
    """Test uploading a file with a room assignment"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    
    # Create household, user, claim, and room
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    
    test_db.add_all([test_household, test_user, test_claim, test_room])
    test_db.commit()
    
    # Create file data
    file_content = "test file content"
    file_base64 = base64.b64encode(file_content.encode()).decode()
    
    # Create request body
    file_data = {
        "files": [{
            "file_name": "test_file.jpg",
            "file_data": file_base64,
            "content_type": "image/jpeg"
        }],
        "room_id": str(room_id),
        "claim_id": str(claim_id)
    }
    
    # Create event
    event = api_gateway_event(
        http_method="POST",
        path_params={},
        body=json.dumps(file_data),
        auth_user=str(user_id)
    )
    
    # Mock environment variables
    with patch.dict("os.environ", {"S3_BUCKET_NAME": "test-bucket"}):
        # Call lambda handler
        response = upload_file_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])
        
        # Assertions
        assert response["statusCode"] == 200
        assert "files_uploaded" in body["data"]
        assert len(body["data"]["files_uploaded"]) == 1
        assert body["data"]["files_uploaded"][0]["file_name"] == "test_file.jpg"
        assert "room_id" in body["data"]["files_uploaded"][0]
        
        # Verify file was created in the database with room association
        file_id = uuid.UUID(body["data"]["files_uploaded"][0]["file_id"])
        file = test_db.query(File).filter(File.id == file_id).first()
        assert file is not None
        assert file.room_id == room_id

def test_upload_file_without_room(test_db, api_gateway_event, mock_s3_client):
    """Test uploading a file without a room assignment"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household, user, and claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()
    
    # Create file data
    file_content = "test file content"
    file_base64 = base64.b64encode(file_content.encode()).decode()
    
    # Create request body without room_id
    file_data = {
        "files": [{
            "file_name": "test_file.jpg",
            "file_data": file_base64,
            "content_type": "image/jpeg"
        }],
        "claim_id": str(claim_id)
    }
    
    # Create event
    event = api_gateway_event(
        http_method="POST",
        path_params={},
        body=json.dumps(file_data),
        auth_user=str(user_id)
    )
    
    # Mock environment variables
    with patch.dict("os.environ", {"S3_BUCKET_NAME": "test-bucket"}):
        # Call lambda handler
        response = upload_file_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])
        
        # Assertions
        assert response["statusCode"] == 200
        assert "files_uploaded" in body["data"]
        assert len(body["data"]["files_uploaded"]) == 1
        assert body["data"]["files_uploaded"][0]["file_name"] == "test_file.jpg"
        assert "room_id" not in body["data"]["files_uploaded"][0]
        
        # Verify file was created in the database without room association
        file_id = uuid.UUID(body["data"]["files_uploaded"][0]["file_id"])
        file = test_db.query(File).filter(File.id == file_id).first()
        assert file is not None
        assert file.room_id is None

def test_update_file_add_room(test_db, api_gateway_event):
    """Test updating a file to add a room association"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    # Create household, user, claim, room, and file (without room)
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_file = File(
        id=file_id, 
        file_name="test_file.jpg", 
        household_id=household_id, 
        uploaded_by=user_id,
        claim_id=claim_id,
        s3_key="test/key",
        file_hash="hash123"
    )
    
    test_db.add_all([test_household, test_user, test_claim, test_room, test_file])
    test_db.commit()
    
    # Create request body to add room
    update_data = {
        "room_id": str(room_id)
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"id": str(file_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = update_file_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["room_id"] == str(room_id)
    
    # Verify file was updated in the database with room association
    updated_file = test_db.query(File).filter(File.id == file_id).first()
    assert updated_file.room_id == room_id

def test_update_file_change_room(test_db, api_gateway_event):
    """Test updating a file to change its room association"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room1_id = uuid.uuid4()
    room2_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    # Create household, user, claim, rooms, and file (with room1)
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room1 = Room(id=room1_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_room2 = Room(id=room2_id, name="Bedroom", description="Master bedroom", household_id=household_id, claim_id=claim_id)
    test_file = File(
        id=file_id, 
        file_name="test_file.jpg", 
        household_id=household_id, 
        uploaded_by=user_id,
        claim_id=claim_id,
        room_id=room1_id,
        s3_key="test/key",
        file_hash="hash123"
    )
    
    test_db.add_all([test_household, test_user, test_claim, test_room1, test_room2, test_file])
    test_db.commit()
    
    # Create request body to change room
    update_data = {
        "room_id": str(room2_id)
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"id": str(file_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = update_file_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["room_id"] == str(room2_id)
    
    # Verify file was updated in the database with new room association
    updated_file = test_db.query(File).filter(File.id == file_id).first()
    assert updated_file.room_id == room2_id

def test_update_file_remove_room(test_db, api_gateway_event):
    """Test updating a file to remove its room association"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    # Create household, user, claim, room, and file (with room)
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_file = File(
        id=file_id, 
        file_name="test_file.jpg", 
        household_id=household_id, 
        uploaded_by=user_id,
        claim_id=claim_id,
        room_id=room_id,
        s3_key="test/key",
        file_hash="hash123"
    )
    
    test_db.add_all([test_household, test_user, test_claim, test_room, test_file])
    test_db.commit()
    
    # Create request body to remove room
    update_data = {
        "room_id": None
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"id": str(file_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = update_file_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["room_id"] is None
    
    # Verify file was updated in the database with room association removed
    updated_file = test_db.query(File).filter(File.id == file_id).first()
    assert updated_file.room_id is None
