import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import uuid
from models.household import Household
from claims.get_claims import lambda_handler
from models.claim import Claim
from models.user import User
from sqlalchemy.exc import SQLAlchemyError

def test_get_claims_success(test_db, api_gateway_event):
    """Test retrieving claims successfully using household ID from JWT"""
    household_id = uuid.uuid4()  # Generate valid UUID

    # Create a household first
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()

    user_id = uuid.uuid4()  # Generate valid UUID for user

    # Create a user associated with the household
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_db.add(test_user)
    test_db.commit()

    # Create test claims with the valid household_id
    claim1 = Claim(id=uuid.uuid4(), household_id=household_id, title="Claim 1", date_of_loss=datetime(2024, 1, 10))
    claim2 = Claim(id=uuid.uuid4(), household_id=household_id, title="Claim 2", date_of_loss=datetime(2024, 1, 11))
    test_db.add_all([claim1, claim2])
    test_db.commit()

    event = api_gateway_event(http_method="GET", auth_user=str(user_id))  # Use a valid UUID for user_id
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["results"]) == 2
    assert body["data"]["results"][0]["title"] == "Claim 1"
    assert body["data"]["results"][1]["title"] == "Claim 2"


def test_get_claims_empty(test_db, api_gateway_event):
    """Test retrieving claims when the user has none"""
    household_id = uuid.uuid4()

    # Create a valid household and user
    test_household = Household(id=household_id, name="Test Household")
    user_id = uuid.uuid4()  # Generate a valid user UUID
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id)
    test_db.add_all([test_household, test_user])
    test_db.commit()

    event = api_gateway_event(http_method="GET", auth_user=str(user_id))  # Use a valid UUID for user_id
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["results"]) == 0


def test_get_claims_unauthorized(test_db, api_gateway_event):
    """Test retrieving claims for a household the user doesn't belong to"""
    # Create two separate households
    household1_id = uuid.uuid4()
    household2_id = uuid.uuid4()
    
    test_household1 = Household(id=household1_id, name="Household 1")
    test_household2 = Household(id=household2_id, name="Household 2")
    test_db.add_all([test_household1, test_household2])
    test_db.commit()
    
    # Create a user in household 1
    user_id = uuid.uuid4()
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household1_id)
    test_db.add(test_user)
    test_db.commit()
    
    # Create claims in household 2
    claim = Claim(id=uuid.uuid4(), household_id=household2_id, title="Other Household Claim", date_of_loss=datetime(2024, 1, 10))
    test_db.add(claim)
    test_db.commit()
    
    # Try to access claims with user from household 1
    event = api_gateway_event(http_method="GET", auth_user=str(user_id))
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    # Should only see claims from their own household (which is empty)
    assert response["statusCode"] == 200
    assert len(body["data"]["results"]) == 0
    
    # Verify the claim in household 2 still exists
    claim_check = test_db.query(Claim).filter_by(title="Other Household Claim").first()
    assert claim_check is not None


def test_get_claims_db_failure(api_gateway_event):
    """Test handling a database connection failure"""
    # We need to patch the database session after it's been created by the decorator
    with patch("utils.lambda_utils.get_db_session") as mock_db:
        # Configure the mock to raise an exception when used
        mock_session = mock_db.return_value
        mock_session.query.side_effect = SQLAlchemyError("Database error occurred")
        
        # Call the lambda handler
        event = api_gateway_event(http_method="GET", auth_user=str(uuid.uuid4()))
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
    
    assert response["statusCode"] == 500
    assert "Database error" in body["error_details"]


def test_get_claims_invalid_jwt(api_gateway_event):
    """Test retrieving claims with a malformed or missing JWT"""
    event = api_gateway_event(http_method="GET", auth_user=None)  # Missing auth
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 401
    assert "Unauthorized" in body["error_details"]