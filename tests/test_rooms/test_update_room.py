import json
import uuid
import pytest
from unittest.mock import MagicMock
from rooms.update_room import lambda_handler
from models.room import Room
from models.claim import Claim
from models.household import Household
from models.user import User
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

def test_update_room_success(test_db, api_gateway_event):
    """Test updating a room successfully"""
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
    
    # Create request body
    update_data = {
        "name": "Updated Living Room",
        "description": "Updated description"
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"room_id": str(room_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["name"] == "Updated Living Room"
    assert body["data"]["description"] == "Updated description"
    assert body["data"]["claim_id"] == str(claim_id)
    assert body["data"]["household_id"] == str(household_id)
    
    # Verify room was updated in the database
    updated_room = test_db.query(Room).filter(Room.id == room_id).first()
    assert updated_room.name == "Updated Living Room"
    assert updated_room.description == "Updated description"

def test_update_room_partial(test_db, api_gateway_event):
    """Test updating only some fields of a room"""
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
    
    # Create request body with only name update
    update_data = {
        "name": "Updated Living Room"
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"room_id": str(room_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["name"] == "Updated Living Room"
    assert body["data"]["description"] == "Main living area"  # Unchanged
    
    # Verify room was updated in the database
    updated_room = test_db.query(Room).filter(Room.id == room_id).first()
    assert updated_room.name == "Updated Living Room"
    assert updated_room.description == "Main living area"

def test_update_room_not_found(test_db, api_gateway_event):
    """Test updating a non-existent room"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    non_existent_room_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create request body
    update_data = {
        "name": "Updated Room",
        "description": "Updated description"
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"room_id": str(non_existent_room_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Room not found" in body["error_details"]

def test_update_room_unauthorized(test_db, api_gateway_event):
    """Test updating a room from a different household"""
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
    
    # Create request body
    update_data = {
        "name": "Updated Room",
        "description": "Updated description"
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"room_id": str(room_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Room not found" in body["error_details"]

def test_update_room_invalid_id(test_db, api_gateway_event):
    """Test updating a room with invalid ID format"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create request body
    update_data = {
        "name": "Updated Room",
        "description": "Updated description"
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"room_id": "invalid-uuid"},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "Invalid room ID format" in body["error_details"]

def test_update_room_db_failure(test_db, api_gateway_event):
    """Test database error when updating a room"""
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
    
    # Create request body
    update_data = {
        "name": "Updated Room",
        "description": "Updated description"
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"room_id": str(room_id)},
        body=json.dumps(update_data),
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
