"""Test register.py"""
import os
import json
import uuid
import sqlalchemy.exc
from auth.register import lambda_handler as register_handler
from models import User, Base, Household
from database.database import engine

# Initialize database tables
Base.metadata.create_all(engine)

def test_register_user_success(mock_cognito, test_db, mocker):
    """Ensure a new user can register successfully and is stored in Cognito and RDS."""

    # Mock Cognito to generate a unique UserSub
    generated_user_sub = str(uuid.uuid4())  # Generate the expected UserSub
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}

    # Ensure `register.py` uses `test_db`
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
    response = register_handler(event, None)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"

    #  Query the **same session** used in register.py
    user = test_db.query(User).filter(User.id == generated_user_sub).first()

    assert user is not None, f"User {generated_user_sub} was not found in test DB"
    assert user.email == "test@example.com"
    assert user.first_name == first_name,(
        f"Expected first name '{first_name}', got '{user.first_name}'"
    )
    assert user.last_name == last_name,(
        f"Expected last name '{last_name}', got '{user.last_name}'"
    )


#  SUCCESS: User registration with default household
def test_register_user_creates_default_household(mock_cognito, test_db, mocker):
    """Ensure a new user gets a default household if none is provided."""

    print("Starting test_register_user_creates_default_household")

    # Mock Cognito to generate a unique UserSub
    generated_user_sub = str(uuid.uuid4())  # Generate the expected UserSub
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}

    # Ensure `register.py` uses `test_db`
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
    response = register_handler(event, None)
    body = json.loads(response["body"])

    #  Query the **same session** used in register.py
    user = test_db.query(User).filter(User.id == generated_user_sub).first()

    user_not_found_msg = (
        f" User {generated_user_sub} was not found in test DB"
    )
    assert user is not None, user_not_found_msg
    assert user.email == f"user_{generated_user_sub}@example.com"

    first_name_msg = (
        f" Expected first name '{first_name}', got '{user.first_name}'"
    )
    assert user.first_name == first_name, first_name_msg

    last_name_msg = (
        f" Expected last name '{last_name}', got '{user.last_name}'"
    )
    assert user.last_name == last_name, last_name_msg

    # Ensure a household was created
    household = test_db.query(Household).filter(Household.id == user.household_id).first()

    household_not_found_msg = (
        f"Household for user {generated_user_sub} was not found in test DB"
    )
    assert household is not None, household_not_found_msg

    expected_household_name = f"{first_name}'s Household"  # Now using actual first name
    household_name_msg = (
        f"Expected household name '{expected_household_name}', got '{household.name}'"
    )
    assert household.name == expected_household_name, household_name_msg


def test_register_existing_user(mock_cognito, test_db, mocker):
    """Ensure registration fails if the user already exists in Cognito."""

    # Mock Cognito to raise UsernameExistsException
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.UsernameExistsException

    # Ensure `register.py` uses `test_db`
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

    print("Calling lambda_handler...")

    # Act: Call the registration Lambda
    response = register_handler(event, None)
    body = json.loads(response["body"])

    print("Lambda finished execution! Checking Response...")

    # Assert: Ensure it returns 409 Conflict
    assert response["statusCode"] == 409, f"Expected 409, got {response['statusCode']}"
    assert "Conflict" in body["error_details"], f"Expected 'Conflict' in error details, got '{body['error_details']}'"

    error_details_msg = (
        f"Expected 'User already exists' in error details, got '{body['error_details']}'"
    )
    assert "User already exists" in body["error_details"], error_details_msg
    print("Test Passed!")


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

    # Act: Call the registration Lambda
    response = register_handler(event, None)
    body = json.loads(response["body"])


    # Assert: Ensure it returns 400 Bad Request
    assert response["statusCode"] == 400, f"Expected 400, got {response['statusCode']}"
    assert body["error_details"].startswith("Bad Request:") or body["error_details"] == "Password does not meet complexity requirements", f"Expected error details to be 'Password does not meet complexity requirements' or start with 'Bad Request:', got '{body['error_details']}'"


# FAILURE: Missing required fields
def test_register_missing_fields(test_db, mocker):
    """ Ensure registration fails if required fields are missing."""

    # Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    # Test cases with missing required fields
    missing_fields_cases = [
        # Missing username
        {
            "password": "StrongPass!123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"},
        # Missing password
        {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"},
        # Missing email
        {
            "username": "testuser",
            "password": "StrongPass!123",
            "first_name": "John",
            "last_name": "Doe"},
        # Missing first_name
        {
            "username": "testuser",
            "password": "StrongPass!123",
            "email": "test@example.com",
            "last_name": "Doe"},
        # Missing last_name
        {
            "username": "testuser",
            "password": "StrongPass!123",
            "email": "test@example.com",
            "first_name": "John"},
    ]

    for idx, invalid_payload in enumerate(missing_fields_cases):

        event = {"body": json.dumps(invalid_payload)}

        # Act: Call the registration Lambda
        response = register_handler(event, None)
        body = json.loads(response["body"])
        # Assert: Ensure it returns 400 Bad Request
        status_code_msg = (
            f"Expected 400, got {response['statusCode']} for missing fields test {idx + 1}"
        )
        assert response["statusCode"] == 400, status_code_msg

        assert body["error_details"] == "Missing required fields", f"Expected 'Missing required fields', got '{body['error_details']}' for missing fields test {idx + 1}"
        assert "missing_fields" in body["data"], f"Expected 'missing_fields' in data, missing for test {idx + 1}"


def test_register_invalid_email(test_db, mocker):
    """ Ensure registration fails if the email format is invalid."""

    print("Starting test_register_invalid_email")

    # Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    # Test cases with invalid email formats
    invalid_emails = [
        "plainaddress",
        "@missingusername.com",
        "missingatsymbol.com",
        "user@.com",
        "user@domain..com",
        "user@domain,com",
        "user@domain@domain.com",
        "user@domain space.com"
    ]

    for idx, invalid_email in enumerate(invalid_emails):
        print(f"Calling lambda_handler with invalid email (Test {idx + 1}): {invalid_email}")

        event = {
            "body": json.dumps({
                "username": "testuser",
                "password": "StrongPass!123",
                "email": invalid_email,  # Invalid email
                "first_name": "John",
                "last_name": "Doe"
            })
        }

        # Act: Call the registration Lambda
        response = register_handler(event, None)
        body = json.loads(response["body"])

        print(f"Lambda finished execution! Checking Response (Test {idx + 1})...")

        # Assert: Ensure it returns 400 Bad Request
        status_code_msg = (
            f"Expected 400, got {response['statusCode']} for invalid email test {idx + 1}"
        )
        assert response["statusCode"] == 400, status_code_msg

        assert body["error_details"] == "Invalid email format", f"Expected 'Invalid email format', got '{body['error_details']}' for invalid email test {idx + 1}"

    print("All invalid email format tests passed!")


# FAILURE: Cognito Internal Error
def test_register_cognito_internal_error(mock_cognito, test_db, mocker):
    """Ensure proper handling if Cognito has an internal error."""

    print("Starting test_register_cognito_internal_error")

    # Mock Cognito to raise InternalErrorException
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.InternalErrorException

    # Ensure `register.py` uses `test_db`
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

    print("Calling lambda_handler...")

    # Act: Call the registration Lambda
    response = register_handler(event, None)
    body = json.loads(response["body"])

    print("Lambda finished execution! Checking Response...")

    # Assert: Ensure it returns 500 Internal Server Error
    assert response["statusCode"] == 500, f"Expected 500, got {response['statusCode']}"
    assert body["error_details"] == "Authentication service unavailable", f"Expected 'Authentication service unavailable', got '{body['error_details']}'"

    print("Test Passed!")


# FAILURE: Database connection failure
def test_register_db_failure(mock_cognito, test_db, mocker):
    """Ensure registration fails gracefully if the database is down."""

    print("Starting test_register_db_failure")

    # Patch the correct path to ensure `get_db_session()` fails
    mocker.patch(
        "auth.register.get_db_session",
        side_effect=sqlalchemy.exc.OperationalError("DB Connection Error", None, None)
    )

    # Mock Cognito (should NOT be called)
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": str(uuid.uuid4())}

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    print("Calling lambda_handler...")

    # Act: Call the registration Lambda
    response = register_handler(event, None)
    body = json.loads(response["body"])

    print("Lambda finished execution! Checking Response...")

    # Ensure Cognito was never called (because DB failed first)
    assert mock_cognito.sign_up.call_count == 0,(
        "Cognito should NOT be called if DB connection fails."
    )

    # Assert: Ensure it returns 500 Internal Server Error
    assert response["statusCode"] == 500, f"Expected 500, got {response['statusCode']}"
    assert body["error_details"] == "Database connection failed", f"Expected 'Database connection failed', got '{body['error_details']}'"

    print("Test Passed!")

def test_register_user_stores_in_db(mock_cognito, test_db, mocker):
    """Ensure the user is stored in the PostgreSQL database after successful registration."""

    print("Starting test_register_user_stores_in_db")

    # Mock Cognito to return a valid UserSub
    generated_user_sub = str(uuid.uuid4())
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}

    # Ensure `register.py` uses `test_db`
    mocker.patch("auth.register.get_db_session", return_value=test_db)

    first_name = "John"
    last_name = "Doe"
    email = f"user_{generated_user_sub}@example.com"

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        })
    }

    print("Calling lambda_handler...")

    # Act: Call the registration Lambda
    response = register_handler(event, None)

    print("Lambda finished execution! Checking DB...")

    # Query the **same session** used in register.py
    user = test_db.query(User).filter(User.id == generated_user_sub).first()

    print(f"DB Query Result: {user}")  # DEBUG

    # Ensure the user exists
    assert user is not None, f"User {generated_user_sub} was not found in test DB"

    # Ensure all fields are stored correctly
    assert user.email == email, f"Expected email '{email}', got '{user.email}'"
    assert user.first_name == first_name, f"Expected first name '{first_name}', got '{user.first_name}'"
    assert user.last_name == last_name, f"Expected last name '{last_name}', got '{user.last_name}'"
    assert user.household_id is not None, "Expected user to have a household ID, but got None"

    # Ensure the household exists
    household = test_db.query(Household).filter(Household.id == user.household_id).first()
    assert household is not None, f"Household {user.household_id} was not found in test DB"
    
    expected_household_name = f"{first_name}'s Household"
    assert household.name == expected_household_name, f"Expected household name '{expected_household_name}', got '{household.name}'"

    print("User successfully stored in PostgreSQL!")


def test_register_sets_cognito_attributes(mock_cognito, test_db, mocker):
    """Ensure Cognito user attributes like email and name are set correctly."""

    print("Starting test_register_sets_cognito_attributes")

    # Mock Cognito to return a valid UserSub
    generated_user_sub = str(uuid.uuid4())
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}

    # Ensure `register.py` uses `test_db`
    mocker.patch("auth.register.get_db_session", return_value=test_db)

    first_name = "John"
    last_name = "Doe"
    email = f"user_{generated_user_sub}@example.com"

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        })
    }

    print("Calling lambda_handler...")

    # Act: Call the registration Lambda
    response = register_handler(event, None)

    print("Lambda finished execution! Checking Cognito Calls...")

    # Assert: Ensure Cognito `sign_up` was called once
    mock_cognito.sign_up.assert_called_once()

    # Extract the actual call arguments
    cognito_call_args = mock_cognito.sign_up.call_args[1]  # Get the keyword arguments used in the call

    # Ensure the expected attributes were sent to Cognito
    assert cognito_call_args["ClientId"] == os.getenv("COGNITO_USER_POOL_CLIENT_ID"), "Incorrect Cognito ClientId"
    assert cognito_call_args["Username"] == "testuser", "Incorrect Cognito Username"
    assert cognito_call_args["Password"] == "StrongPass!123", "Incorrect Cognito Password"

    # Ensure the correct user attributes were set
    expected_attributes = [
        {"Name": "email", "Value": email},
        {"Name": "given_name", "Value": first_name},
        {"Name": "family_name", "Value": last_name},
    ]
    
    assert cognito_call_args["UserAttributes"] == expected_attributes, \
        f"Expected Cognito UserAttributes {expected_attributes}, got {cognito_call_args['UserAttributes']}"

    print("Cognito user attributes were set correctly!")


# SUCCESS: Ensure household ID syncs correctly
def test_register_syncs_household_id(mock_cognito, test_db, mocker):
    """Ensure the user's household ID is correctly stored in PostgreSQL and synced with Cognito."""

    print("Starting test_register_syncs_household_id")

    # Mock Cognito to return a valid UserSub
    generated_user_sub = str(uuid.uuid4())
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}

    # Mock Cognito user attribute update
    mock_cognito.admin_update_user_attributes.return_value = {}

    # Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    first_name = "John"
    last_name = "Doe"
    email = f"user_{generated_user_sub}@example.com"

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        })
    }

    print("Calling lambda_handler...")

    # Act: Call the registration Lambda
    _response = register_handler(event, None)

    print("Lambda finished execution! Checking DB...")

    # Query the **same session** used in register.py
    user = test_db.query(User).filter(User.id == generated_user_sub).first()

    print(f"DB Query Result: {user}")  # DEBUG

    # Ensure the user exists and has a household ID
    user_not_found_msg = (
        f"User {generated_user_sub} was not found in test DB"
    )
    assert user is not None, user_not_found_msg
    assert user.household_id is not None, "Expected user to have a household ID, but got None"

    # Ensure the household exists
    household = test_db.query(Household).filter(Household.id == user.household_id).first()
    household_not_found_msg = (
        f"Household {user.household_id} was not found in test DB"
    )
    assert household is not None, household_not_found_msg
    
    expected_household_name = f"{first_name}'s Household"
    household_name_msg = (
        f"Expected household name '{expected_household_name}', got '{household.name}'"
    )
    assert household.name == expected_household_name, household_name_msg

    print(f"Household successfully created and linked: {household.id} ({household.name})")  # DEBUG

    # Assert: Ensure Cognito `admin_update_user_attributes` was called with the correct household ID
    mock_cognito.admin_update_user_attributes.assert_called_once_with(
        UserPoolId=os.getenv("COGNITO_USER_POOL_ID"),
        Username=generated_user_sub,
        UserAttributes=[{"Name": "custom:household_id", "Value": str(user.household_id)}]
    )

    print("Household ID successfully synced with Cognito!")


def test_register_email_already_used(mock_cognito, test_db, mocker):
    """Ensure registration fails if the email is already linked to another Cognito user."""

    print("Starting test_register_email_already_used")

    # Mock Cognito to raise UsernameExistsException when trying to sign up
    mock_cognito.sign_up.side_effect = mock_cognito.exceptions.UsernameExistsException

    # Ensure `register.py` uses `test_db`
    mocker.patch("database.database.get_db_session", return_value=test_db)

    first_name = "John"
    last_name = "Doe"
    email = "test@example.com"

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        })
    }

    print("Calling lambda_handler...")

    # Act: Call the registration Lambda
    response = register_handler(event, None)
    body = json.loads(response["body"])

    print("Lambda finished execution! Checking Response...")

    # Assert: Ensure it returns 409 Conflict
    assert response["statusCode"] == 409, f"Expected 409, got {response['statusCode']}"

    error_details_msg = (
        f"Unexpected error details: {body['error_details']}"
    )
    assert "User already exists" in body["error_details"], error_details_msg

    print("Test Passed!")

def test_register_cognito_household_sync_failure(mock_cognito, test_db, mocker):
    """Ensure registration doesn't fail if Cognito household sync fails."""
    generated_user_sub = str(uuid.uuid4())
    mock_cognito.sign_up.side_effect = lambda *args, **kwargs: {"UserSub": generated_user_sub}
    mock_cognito.admin_update_user_attributes.side_effect = Exception("Cognito update failed")

    mocker.patch("auth.register.get_db_session", return_value=test_db)

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "StrongPass!123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    response = register_handler(event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200, f"Expected 200, got {response['statusCode']}"
    assert "message" in body, "Expected 'message' in response body"
    assert body["message"] == "OK" or "User registered successfully" in body["message"]

def test_register_weak_password_prevalidation(mock_cognito, test_db, mocker):
    """Ensure weak passwords are caught before Cognito is called."""
    mocker.patch("auth.register.get_cognito_client", return_value=mock_cognito)
    mock_cognito.sign_up.side_effect = AssertionError("Cognito should not be called for weak passwords")

    event = {
        "body": json.dumps({
            "username": "testuser",
            "password": "weakpass",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
    }

    response = register_handler(event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400, f"Expected 400, got {response['statusCode']}"
    assert body["error_details"] == "Password does not meet complexity requirements", f"Expected 'Password does not meet complexity requirements', got '{body['error_details']}'"
