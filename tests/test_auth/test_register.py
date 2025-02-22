import os
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock
from auth.register import lambda_handler
from models import User, Base, Household, File, Claim
from database.database import engine

# Initialize database tables
Base.metadata.create_all(engine)

def test_register_user_success(mock_cognito, test_db, mocker):
    """✅ Ensure a new user can register successfully and is stored in Cognito and RDS."""

    # Mock Cognito to generate a unique UserSub
    generated_user_sub = str(uuid.uuid4())  # Generate the expected UserSub
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}

    #Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    first_name = "John"
    last_name = "Doe"

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": "test@example.com",
            "first_name": first_name,  
            "last_name": last_name  
        })
    }

    # Act: Call the registration Lambda
    response = lambda_handler(event, None)

    #  Query the **same session** used in register.py
    user = test_db.query(User).filter(User.id == generated_user_sub).first()


    assert user is not None, f"User {generated_user_sub} was not found in test DB"
    assert user.email == "test@example.com"
    assert user.first_name == first_name, f"Expected first name '{first_name}', got '{user.first_name}'"
    assert user.last_name == last_name, f"Expected last name '{last_name}', got '{user.last_name}'"
    assert user.full_name == f"{first_name} {last_name}", f"Expected full name '{first_name} {last_name}', got '{user.full_name}'"




#  SUCCESS: User registration with default household
def test_register_user_creates_default_household(mock_cognito, test_db, mocker):
    """✅ Ensure a new user gets a default household if none is provided."""

    print("🚀 Starting test_register_user_creates_default_household")

    # ✅ Mock Cognito to generate a unique UserSub
    generated_user_sub = str(uuid.uuid4())  # Generate the expected UserSub
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}

    # ✅ Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    first_name = "John"
    last_name = "Doe"
    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": f"user_{generated_user_sub}@example.com",
            "first_name": first_name,  
            "last_name": last_name
        })
    }

    # Act: Call the registration Lambda
    response = lambda_handler(event, None)

    #  Query the **same session** used in register.py
    user = test_db.query(User).filter(User.id == generated_user_sub).first()


    assert user is not None, f" User {generated_user_sub} was not found in test DB"
    assert user.email == f"user_{generated_user_sub}@example.com"
    assert user.first_name == first_name, f" Expected first name '{first_name}', got '{user.first_name}'"
    assert user.last_name == last_name, f" Expected last name '{last_name}', got '{user.last_name}'"

    # ✅ Ensure a household was created
    household = test_db.query(Household).filter(Household.id == user.household_id).first()
    assert household is not None, f"Household for user {generated_user_sub} was not found in test DB"

    expected_household_name = f"{first_name}'s Household"  # ✅ Now using actual first name
    assert household.name == expected_household_name, f"Expected household name '{expected_household_name}', got '{household.name}'"


def test_register_existing_user(mock_cognito, test_db, mocker):
    """Ensure registration fails if the user already exists in Cognito."""

    # ✅ Mock Cognito to raise UsernameExistsException
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.UsernameExistsException

    # ✅ Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    print("📡 Calling lambda_handler...")

    # ✅ Act: Call the registration Lambda
    response = lambda_handler(event, None)
    body = json.loads(response["body"])

    print("✅ Lambda finished execution! Checking Response...")

    # ✅ Assert: Ensure it returns 409 Conflict
    assert response["statusCode"] == 409, f"Expected 409, got {response['statusCode']}"
    assert "User already exists" in body["message"], f"Expected 'User already exists' in message, got '{body['message']}'"

    print("✅ Test Passed!")

def test_register_weak_password(mock_cognito, test_db, mocker):
    """Ensure registration fails if password does not meet security requirements."""


    # Mock Cognito to raise InvalidPasswordException
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.InvalidPasswordException

    # Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "weak",  # Weak password example
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    # ✅ Act: Call the registration Lambda
    response = lambda_handler(event, None)
    body = json.loads(response["body"])


    # ✅ Assert: Ensure it returns 400 Bad Request
    assert response["statusCode"] == 400, f"Expected 400, got {response['statusCode']}"
    assert "Bad Request" in body["message"], f"Expected 'Bad Request' in message, got '{body['message']}'"



# FAILURE: Missing required fields
def test_register_missing_fields(test_db, mocker):
    """❌ Ensure registration fails if required fields are missing."""
    pass  # TODO: Implement

# ❌ FAILURE: Invalid email format
def test_register_invalid_email(test_db, mocker):
    """❌ Ensure registration fails if the email format is invalid."""
    pass  # TODO: Implement

# ❌ FAILURE: Cognito Internal Error
def test_register_cognito_internal_error(test_db, mocker):
    """❌ Ensure proper handling if Cognito has an internal error."""
    pass  # TODO: Implement

# ❌ FAILURE: Database connection failure
def test_register_db_failure(test_db, mocker):
    """❌ Ensure registration fails gracefully if the database is down."""
    pass  # TODO: Implement

# ✅ SUCCESS: Ensure user is stored in PostgreSQL
def test_register_user_stores_in_db(test_db, mocker):
    """✅ Ensure the user is stored in the PostgreSQL database after successful registration."""
    pass  # TODO: Implement

# ✅ SUCCESS: Ensure Cognito user attributes are set correctly
def test_register_sets_cognito_attributes(test_db, mocker):
    """✅ Ensure Cognito user attributes like email and name are set correctly."""
    pass  # TODO: Implement

# ✅ SUCCESS: Ensure household ID syncs correctly
def test_register_syncs_household_id(test_db, mocker):
    """✅ Ensure the user's household ID is correctly stored in PostgreSQL."""
    pass  # TODO: Implement

# ❌ FAILURE: Cognito rejects email already in use
def test_register_email_already_used(test_db, mocker):
    """❌ Ensure registration fails if the email is already linked to another Cognito user."""
    pass  # TODO: Implement
