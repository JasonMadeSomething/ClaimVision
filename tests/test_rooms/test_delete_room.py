import json
import uuid
import pytest
from unittest.mock import MagicMock
from rooms.delete_room import lambda_handler
from models.room import Room
from models.claim import Claim
from models.household import Household
from models.user import User
from models.item import Item
from models.file import File
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

def test_delete_room_success(test_db, api_gateway_event):
    """Test deleting a room successfully"""
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
    
    # Create event
    event = api_gateway_event(
        http_method="DELETE",
        path_params={"room_id": str(room_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert "Room deleted successfully" in body["message"]
    
    # Verify room was soft deleted in the database
    deleted_room = test_db.query(Room).filter(Room.id == room_id).first()
    assert deleted_room.deleted is True

def test_delete_room_with_items_and_files(test_db, api_gateway_event):
    """Test deleting a room that has associated items and files"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    item_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    # Create household, user, claim, room, item, and file
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_item = Item(id=item_id, claim_id=claim_id, name="Sofa", room_id=room_id)
    test_file = File(id=file_id, file_name="photo.jpg", household_id=household_id, uploaded_by=user_id, room_id=room_id, file_hash="hash123", s3_key="test/photo.jpg")
    
    test_db.add_all([test_household, test_user, test_claim, test_room, test_item, test_file])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="DELETE",
        path_params={"room_id": str(room_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert "Room deleted successfully" in body["message"]
    
    # Verify room was soft deleted in the database
    deleted_room = test_db.query(Room).filter(Room.id == room_id).first()
    assert deleted_room.deleted is True
    
    # Verify item and file room associations were removed
    updated_item = test_db.query(Item).filter(Item.id == item_id).first()
    assert updated_item.room_id is None
    
    updated_file = test_db.query(File).filter(File.id == file_id).first()
    assert updated_file.room_id is None

def test_delete_room_not_found(test_db, api_gateway_event):
    """Test deleting a non-existent room"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    non_existent_room_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="DELETE",
        path_params={"room_id": str(non_existent_room_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Room not found" in body["error_details"]

def test_delete_room_unauthorized(test_db, api_gateway_event):
    """Test deleting a room from a different household"""
    # Create test data
    household1_id = uuid.uuid4()
    household2_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    
    # Create households, user, claim, and room
    test_household1 = Household(id=household1_id, name="Test Household 1")
    test_household2 = Household(id=household2_id, name="Test Household 2")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household1_id)
    test_claim = Claim(id=claim_id, household_id=household2_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household2_id, claim_id=claim_id)
    
    test_db.add_all([test_household1, test_household2, test_user, test_claim, test_room])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="DELETE",
        path_params={"room_id": str(room_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Room not found" in body["error_details"]

def test_delete_room_invalid_id(test_db, api_gateway_event):
    """Test deleting a room with invalid ID format"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="DELETE",
        path_params={"room_id": "invalid-uuid"},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "Invalid room ID format" in body["error_details"]

def test_delete_room_db_failure(test_db, api_gateway_event):
    """Test database error when deleting a room"""
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
    
    # Create event
    event = api_gateway_event(
        http_method="DELETE",
        path_params={"room_id": str(room_id)},
        auth_user=str(user_id)
    )
    
    # Create a mock session
    mock_session = MagicMock()
    
    # Configure the mock to return a room when queried
    mock_room = MagicMock()
    mock_room.id = room_id
    mock_room.household_id = household_id
    mock_session.query.return_value.filter.return_value.first.return_value = mock_room
    
    # Make commit throw an exception
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Call lambda handler with the mock session
    response = lambda_handler(event, {}, db_session=mock_session)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 500
    assert "Database error" in body["error_details"]
