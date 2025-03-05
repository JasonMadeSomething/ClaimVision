import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import uuid
from models.household import Household
from claims.get_claims import lambda_handler
from models.claim import Claim
from models.user import User

def test_get_claims_success(test_db, api_gateway_event):
    """✅ Test retrieving claims successfully using household ID from JWT"""
    household_id = uuid.uuid4()  # ✅ Generate valid UUID

    # ✅ Create a household first
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()

    user_id = uuid.uuid4()  # ✅ Generate valid UUID for user

    # ✅ Create a user associated with the household
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_db.add(test_user)
    test_db.commit()

    # ✅ Create test claims with the valid household_id
    claim1 = Claim(id=uuid.uuid4(), household_id=household_id, title="Claim 1", date_of_loss=datetime(2024, 1, 10))
    claim2 = Claim(id=uuid.uuid4(), household_id=household_id, title="Claim 2", date_of_loss=datetime(2024, 1, 11))
    test_db.add_all([claim1, claim2])
    test_db.commit()

    event = api_gateway_event(http_method="GET", auth_user=str(user_id))  # ✅ Use a valid UUID for user_id
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["results"]) == 2
    assert body["data"]["results"][0]["title"] == "Claim 1"
    assert body["data"]["results"][1]["title"] == "Claim 2"




def test_get_claims_empty(test_db, api_gateway_event):
    """✅ Test retrieving claims when the user has none"""
    event = api_gateway_event(http_method="GET", auth_user="user-123")
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"] == []

def test_get_claims_unauthorized(test_db, api_gateway_event):
    """❌ Test retrieving claims for a household the user doesn't belong to"""
    event = api_gateway_event(http_method="GET", auth_user="user-unauthorized")
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404  # ✅ Security: Pretend the household doesn't exist
    assert "Not Found" in body["message"]

def test_get_claims_db_failure(api_gateway_event):
    """❌ Test handling a database connection failure"""
    with patch("claims.get_claims.get_db_session", side_effect=Exception("DB Failure")):
        event = api_gateway_event(http_method="GET", auth_user="user-123")
        response = lambda_handler(event, {})
        body = json.loads(response["body"])

    assert response["statusCode"] == 500
    assert "Internal Server Error" in body["message"]

def test_get_claims_invalid_jwt(api_gateway_event):
    """❌ Test retrieving claims with a malformed or missing JWT"""
    event = api_gateway_event(http_method="GET", auth_user=None)  # No JWT
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Invalid authentication" in body["message"]