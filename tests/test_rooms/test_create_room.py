import json
import uuid
import pytest
from unittest.mock import MagicMock
from rooms.create_room import lambda_handler
from models.room import Room
from models.claim import Claim
from models.household import Household
from models.user import User
from datetime import datetime

def test_create_room_success(test_db, api_gateway_event):
    """Test creating a room successfully"""
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
    
    # Create request body - claim_id is now in path parameters
    room_data = {
        "name": "Living Room",
        "description": "Main living area"
    }
    
    # Create event with claim_id in path parameters
    event = api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps(room_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 201
    assert body["data"]["name"] == "Living Room"
    assert body["data"]["description"] == "Main living area"
    assert body["data"]["claim_id"] == str(claim_id)
    assert body["data"]["household_id"] == str(household_id)
    assert "id" in body["data"]
    
    # Verify room was created in the database
    room = test_db.query(Room).filter(Room.id == uuid.UUID(body["data"]["id"])).first()
    assert room is not None
    assert room.name == "Living Room"
    assert room.description == "Main living area"

def test_create_room_missing_name(test_db, api_gateway_event):
    """Test creating a room with missing name"""
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
    
    # Create request body with missing name
    room_data = {
        "description": "Main living area"
    }
    
    # Create event with claim_id in path parameters
    event = api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps(room_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "Room name is required" in body["error_details"]

def test_create_room_invalid_claim_id(test_db, api_gateway_event):
    """Test creating a room with invalid claim ID"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create request body
    room_data = {
        "name": "Living Room",
        "description": "Main living area"
    }
    
    # Create event with invalid claim_id in path parameters
    event = api_gateway_event(
        http_method="POST",
        path_params={"claim_id": "invalid-uuid"},
        body=json.dumps(room_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "Invalid UUID format" in body["error_details"]

def test_create_room_claim_not_found(test_db, api_gateway_event):
    """Test creating a room with non-existent claim"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    non_existent_claim_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create request body
    room_data = {
        "name": "Living Room",
        "description": "Main living area"
    }
    
    # Create event with non-existent claim_id in path parameters
    event = api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(non_existent_claim_id)},
        body=json.dumps(room_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Claim not found or access denied" in body["error_details"]

def test_create_room_missing_claim_id(test_db, api_gateway_event):
    """Test creating a room with missing claim ID"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create request body
    room_data = {
        "name": "Living Room",
        "description": "Main living area"
    }
    
    # Create event with no claim_id in path parameters
    event = api_gateway_event(
        http_method="POST",
        path_params={},
        body=json.dumps(room_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "Claim ID is required" in body["error_details"]

def test_create_room_db_error(test_db, api_gateway_event):
    """Test database error when creating a room"""
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
    
    # Create request body
    room_data = {
        "name": "Living Room",
        "description": "Main living area"
    }
    
    # Create event with claim_id in path parameters
    event = api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps(room_data),
        auth_user=str(user_id)
    )
    
    # Create a mock session with add method that raises an exception
    mock_session = MagicMock()
    mock_session.query = test_db.query  # Keep the query method working normally
    mock_session.add.side_effect = Exception("Database error")
    
    # Call lambda handler with the mock session
    response = lambda_handler(event, {}, db_session=mock_session)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 500
    assert "Database error" in body["error_details"]
