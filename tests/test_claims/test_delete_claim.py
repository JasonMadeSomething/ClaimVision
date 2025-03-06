import json
import uuid
import pytest
from unittest.mock import patch
from claims.delete_claim import lambda_handler
from models import Claim, Household, User
from datetime import datetime

def test_delete_claim_success(test_db, api_gateway_event):
    """✅ Test successful claim deletion"""
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    # ✅ Create household, user, and claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=uuid.uuid4(), email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": str(claim_id)}, auth_user=str(test_user.id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "Claim deleted successfully" in body["message"]

def test_delete_claim_unauthorized(test_db, api_gateway_event):
    """❌ Test deleting a claim that belongs to another user"""

    # ✅ Create two separate households
    authorized_household_id = uuid.uuid4()
    unauthorized_household_id = uuid.uuid4()

    test_household = Household(id=authorized_household_id, name="Authorized Household")
    unauthorized_household = Household(id=unauthorized_household_id, name="Unauthorized Household")
    
    test_db.add_all([test_household, unauthorized_household])
    test_db.commit()

    # ✅ Create two users, each in their own household
    authorized_user_id = uuid.uuid4()
    unauthorized_user_id = uuid.uuid4()

    authorized_user = User(id=authorized_user_id, email="auth@example.com", first_name="Auth", last_name="User", household_id=authorized_household_id)
    unauthorized_user = User(id=unauthorized_user_id, email="unauth@example.com", first_name="Unauth", last_name="User", household_id=unauthorized_household_id)

    test_db.add_all([authorized_user, unauthorized_user])
    test_db.commit()

    # ✅ Now create a claim in the authorized household
    claim_id = uuid.uuid4()
    test_claim = Claim(id=claim_id, household_id=authorized_household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))

    test_db.add(test_claim)
    test_db.commit()

    # ✅ The unauthorized user tries to delete the claim
    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": str(claim_id)}, auth_user=str(unauthorized_user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404  # ✅ Security: Pretend it doesn't exist


def test_delete_claim_not_found(test_db, api_gateway_event):
    """✅ Test deleting a non-existent claim"""

    household_id = uuid.uuid4()
    user_id = uuid.uuid4()  # ✅ Generate a valid user UUID

    # ✅ Create a household and user before calling lambda_handler
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_db.add_all([test_household, test_user])
    test_db.commit()

    # ✅ Attempt to delete a claim that doesn’t exist
    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": str(uuid.uuid4())}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert "Claim not found" in body["error_details"]


def test_delete_claim_invalid_id(api_gateway_event):
    """❌ Test deleting a claim with an invalid UUID"""
    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": "invalid-uuid"}, auth_user=str(uuid.uuid4()))
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Invalid claim ID format" in body["error_details"]

def test_delete_claim_db_failure(api_gateway_event):
    """❌ Test handling a database failure during claim deletion"""
    with patch("claims.delete_claim.get_db_session", side_effect=Exception("DB Failure")):
        event = api_gateway_event(http_method="DELETE", path_params={"claim_id": str(uuid.uuid4())}, auth_user=str(uuid.uuid4()))
        response = lambda_handler(event, {})
        body = json.loads(response["body"])

    assert response["statusCode"] == 500
    assert "Internal Server Error" in body["message"]