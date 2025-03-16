import json
import uuid
import pytest
from unittest.mock import MagicMock
from rooms.get_room import lambda_handler
from models.room import Room
from models.claim import Claim
from models.household import Household
from models.user import User
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

def test_get_room_success(test_db, api_gateway_event):
    """Test retrieving a room successfully by ID"""
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
        http_method="GET",
        path_params={"room_id": str(room_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["name"] == "Living Room"
    assert body["data"]["description"] == "Main living area"
    assert body["data"]["claim_id"] == str(claim_id)
    assert body["data"]["household_id"] == str(household_id)
    assert body["data"]["id"] == str(room_id)

def test_get_room_not_found(test_db, api_gateway_event):
    """Test retrieving a non-existent room"""
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
        http_method="GET",
        path_params={"room_id": str(non_existent_room_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Room not found" in body["error_details"]

def test_get_room_unauthorized(test_db, api_gateway_event):
    """Test retrieving a room from a different household"""
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
        http_method="GET",
        path_params={"room_id": str(room_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Room not found" in body["error_details"]

def test_get_room_invalid_id(test_db, api_gateway_event):
    """Test retrieving a room with invalid ID format"""
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
        http_method="GET",
        path_params={"room_id": "invalid-uuid"},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "Invalid room ID format" in body["error_details"]

def test_get_room_db_failure(test_db, api_gateway_event):
    """Test database error when retrieving a room"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="GET",
        path_params={"room_id": str(room_id)},
        auth_user=str(user_id)
    )
    
    # Create a mock session with query method that raises an exception
    mock_session = MagicMock()
    mock_session.query.side_effect = SQLAlchemyError("Database error")
    
    # Call lambda handler with the mock session
    response = lambda_handler(event, {}, db_session=mock_session)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 500
    assert "Database error" in body["error_details"]
