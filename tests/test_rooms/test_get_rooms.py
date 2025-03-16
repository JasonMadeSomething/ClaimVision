import json
import uuid
import pytest
from unittest.mock import MagicMock
from rooms.get_rooms import lambda_handler
from models.room import Room
from models.claim import Claim
from models.household import Household
from models.user import User
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

def test_get_rooms_success(test_db, api_gateway_event):
    """Test retrieving all rooms for a claim successfully"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room1_id = uuid.uuid4()
    room2_id = uuid.uuid4()
    
    # Create household, user, claim, and rooms
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room1 = Room(id=room1_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_room2 = Room(id=room2_id, name="Kitchen", description="Cooking area", household_id=household_id, claim_id=claim_id)
    
    test_db.add_all([test_household, test_user, test_claim, test_room1, test_room2])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="GET",
        query_params={"claim_id": str(claim_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert "rooms" in body["data"]
    assert len(body["data"]["rooms"]) == 2
    
    # Verify room details
    room_names = [room["name"] for room in body["data"]["rooms"]]
    assert "Living Room" in room_names
    assert "Kitchen" in room_names

def test_get_rooms_empty_list(test_db, api_gateway_event):
    """Test retrieving rooms for a claim with no rooms"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household, user, and claim (but no rooms)
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="GET",
        query_params={"claim_id": str(claim_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert "rooms" in body["data"]
    assert len(body["data"]["rooms"]) == 0

def test_get_rooms_claim_not_found(test_db, api_gateway_event):
    """Test retrieving rooms for a non-existent claim"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    non_existent_claim_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="GET",
        query_params={"claim_id": str(non_existent_claim_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Claim not found or access denied" in body["error_details"]

def test_get_rooms_unauthorized(test_db, api_gateway_event):
    """Test retrieving rooms for a claim from a different household"""
    # Create test data
    household1_id = uuid.uuid4()
    household2_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create households, user, and claim
    test_household1 = Household(id=household1_id, name="Test Household 1")
    test_household2 = Household(id=household2_id, name="Test Household 2")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household1_id)
    test_claim = Claim(id=claim_id, household_id=household2_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    
    test_db.add_all([test_household1, test_household2, test_user, test_claim])
    test_db.commit()
    
    # Create event
    event = api_gateway_event(
        http_method="GET",
        query_params={"claim_id": str(claim_id)},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "Claim not found or access denied" in body["error_details"]

def test_get_rooms_missing_claim_id(test_db, api_gateway_event):
    """Test retrieving rooms without providing a claim ID"""
    # Create test data
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household and user
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()
    
    # Create event without claim_id
    event = api_gateway_event(
        http_method="GET",
        query_params={},
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "Invalid or missing claim ID" in body["error_details"]

def test_get_rooms_db_failure(test_db, api_gateway_event):
    """Test database error when retrieving rooms"""
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
    
    # Create event
    event = api_gateway_event(
        http_method="GET",
        query_params={"claim_id": str(claim_id)},
        auth_user=str(user_id)
    )
    
    # Create a mock session with a query method that raises an exception
    mock_session = MagicMock()
    mock_session.query.side_effect = SQLAlchemyError("Database error")
    
    # Call lambda handler with the mock session
    response = lambda_handler(event, {}, db_session=mock_session)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 500
    assert "Database error" in body["error_details"]
