import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
from claims.update_claim import lambda_handler
from models.claim import Claim
from models.household import Household
from models.user import User


def test_update_claim_success(test_db, api_gateway_event):
    """ Test successful claim update"""
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    # Create household, user, and claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id,
    )
    test_claim = Claim(
        id=claim_id,
        household_id=household_id,
        title="Old Title",
        date_of_loss=datetime(2024, 1, 10),
    )

    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        auth_user=str(test_user.id),
        body={"title": "New Title"},
    )
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["title"] == "New Title"


def test_update_claim_unauthorized(test_db, api_gateway_event):
    """ Test updating a claim that belongs to another user"""

    # Create two separate households
    authorized_household_id = uuid.uuid4()
    unauthorized_household_id = uuid.uuid4()

    test_household = Household(id=authorized_household_id, name="Authorized Household")
    unauthorized_household = Household(
        id=unauthorized_household_id, name="Unauthorized Household"
    )

    test_db.add_all([test_household, unauthorized_household])
    test_db.commit()

    # Create two users, each in their own household
    authorized_user_id = uuid.uuid4()
    unauthorized_user_id = uuid.uuid4()

    authorized_user = User(
        id=authorized_user_id,
        email="auth@example.com",
        first_name="Auth",
        last_name="User",
        household_id=authorized_household_id,
    )
    unauthorized_user = User(
        id=unauthorized_user_id,
        email="unauth@example.com",
        first_name="Unauth",
        last_name="User",
        household_id=unauthorized_household_id,
    )

    test_db.add_all([authorized_user, unauthorized_user])
    test_db.commit()

    # Now create a claim in the authorized household
    claim_id = uuid.uuid4()
    test_claim = Claim(
        id=claim_id,
        household_id=authorized_household_id,
        title="Old Title",
        date_of_loss=datetime(2024, 1, 10),
    )

    test_db.add(test_claim)
    test_db.commit()

    # The unauthorized user tries to update the claim
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        auth_user=str(unauthorized_user_id),
        body={"title": "New Title"},
    )
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404  # Security: Pretend it doesn't exist


def test_update_claim_not_found(test_db, api_gateway_event):
    """ Test updating a non-existent claim"""

    household_id = uuid.uuid4()
    user_id = uuid.uuid4()  # Generate a valid user UUID

    # Create a household and user before calling lambda_handler
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id,
    )
    test_db.add_all([test_household, test_user])
    test_db.commit()

    # Attempt to update a claim that doesn’t exist
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(uuid.uuid4())},
        auth_user=str(user_id),
        body={"title": "Updated Title"},
    )
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert "Claim not found" in body["error_details"]


def test_update_claim_invalid_id(test_db, api_gateway_event):
    """ Test updating a claim with an invalid UUID"""

    # Ensure the user exists before testing the invalid claim ID
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    
    test_db.add_all([test_household, test_user])
    test_db.commit()

    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": "invalid-uuid"},  # Invalid claim ID
        auth_user=str(user_id),  # User exists in the DB
        body={"title": "New Title"},
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Invalid claim ID format" in body["error_details"]

def test_update_claim_invalid_fields(api_gateway_event):
    """ Test updating a claim with invalid fields"""
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(uuid.uuid4())},
        auth_user=str(uuid.uuid4()),
        body={"invalid_field": "Bad Data"},
    )
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Invalid update fields" in body["error_details"]


def test_update_claim_db_failure(api_gateway_event):
    """ Test handling a database failure during claim update"""
    with patch(
        "claims.update_claim.get_db_session", side_effect=Exception("DB Failure")
    ):
        event = api_gateway_event(
            http_method="PUT",
            path_params={"claim_id": str(uuid.uuid4())},
            auth_user=str(uuid.uuid4()),
            body={"title": "New Title"},
        )
        response = lambda_handler(event, {})
        body = json.loads(response["body"])

    assert response["statusCode"] == 500
    assert "Internal Server Error" in body["error_details"]

def test_update_claim_no_future_date(test_db, api_gateway_event):
    """ Test that claim date of loss cannot be set to a future date"""
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    # Create household, user, and claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=uuid.uuid4(), email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Old Title", date_of_loss=datetime(2024, 1, 10))
    
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")

    event = api_gateway_event(http_method="PUT", path_params={"claim_id": str(claim_id)}, auth_user=str(test_user.id), body={"date_of_loss": future_date})
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "Date of loss cannot be in the future" in body["error_details"]
