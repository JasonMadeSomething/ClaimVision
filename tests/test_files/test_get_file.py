""" Test retrieving a single file from PostgreSQL"""
import json
import uuid
from datetime import datetime

import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

from files.get_file import lambda_handler
from models import Household, User

@pytest.mark.usefixtures("seed_file")
def test_get_file_success(api_gateway_event, test_db, seed_file, mock_s3):
    """ Test retrieving a single file successfully"""
    file_id, user_id = seed_file[:2]

    mock_s3.generate_presigned_url.return_value = "https://signed-url.com/file"

    event = api_gateway_event(
        http_method="GET",
        path_params={"id": str(file_id)},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["id"] == str(file_id)
    assert body["data"]["file_name"] == "original.jpg"



def test_get_file_not_found(api_gateway_event, test_db):
    """ Test retrieving a non-existent file"""
    # Create a valid user in the database
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test_not_found@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id,
    )
    
    test_db.add_all([test_household, test_user])
    test_db.commit()

    event = api_gateway_event(
        http_method="GET",
        path_params={"id": str(uuid.uuid4())},  # Non-existent file ID
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert body["status"] == "Not Found"
    assert "error_details" in body
    assert "File not found" in body["error_details"]


def test_get_file_invalid_uuid(api_gateway_event, test_db):
    """ Test retrieving a file with invalid UUID format"""
    user_id = uuid.uuid4()
    
    # Create a valid user
    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test_invalid_uuid@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id,
    )
    
    test_db.add_all([test_household, test_user])
    test_db.commit()

    # Test with invalid file UUID
    event = api_gateway_event(
        http_method="GET",
        path_params={"id": "not-a-valid-uuid"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert body["status"] == "Bad Request"
    assert "error_details" in body
    assert "Invalid id format. Expected UUID." in body["error_details"]

    # Test with invalid user UUID
    event = api_gateway_event(
        http_method="GET",
        path_params={"id": str(uuid.uuid4())},
        auth_user="not-a-valid-uuid",
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 401
    assert body["status"] == "Unauthorized"
    assert "error_details" in body
    assert "Unauthorized" in body["error_details"]


def test_get_file_unauthorized_access(api_gateway_event, test_db, seed_file):
    """ Test unauthorized access to a file from a different household"""
    file_id, _, original_household_id = seed_file
    
    # Create a new user in a different household
    new_household_id = uuid.uuid4()
    new_user_id = uuid.uuid4()
    
    new_household = Household(id=new_household_id, name="Different Household")
    new_user = User(
        id=new_user_id,
        email="different_user@example.com",
        first_name="Different",
        last_name="User",
        household_id=new_household_id,
    )
    
    test_db.add_all([new_household, new_user])
    test_db.commit()
    
    # Try to access the file with a user from a different household
    event = api_gateway_event(
        http_method="GET",
        path_params={"id": str(file_id)},
        auth_user=str(new_user_id),
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 404
    assert body["status"] == "Not Found"
    assert "error_details" in body
    assert "File not found" in body["error_details"]


def test_get_file_missing_parameters(api_gateway_event, test_db, seed_file):
    """ Test retrieving a file with missing parameters"""
    _, user_id = seed_file[:2]
    
    # Test with missing file ID by setting pathParameters to None
    # This simulates how API Gateway would handle a missing path parameter
    event = {
        "httpMethod": "GET",
        "pathParameters": None,  # API Gateway sets this to None when path parameter is missing
        "queryStringParameters": {},
        "headers": {"Authorization": "Bearer fake-jwt-token"},
        "requestContext": {
            "authorizer": {"claims": {"sub": str(user_id)}}
        },
        "body": None,
    }
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # The lambda handler returns 400 when pathParameters is None
    # because it tries to call .get("id") on None which causes an exception
    assert response["statusCode"] == 400
    assert body["status"] == "Bad Request"
    assert "error_details" in body


@patch('utils.lambda_utils.get_db_session')
def test_get_file_database_error(mock_get_db, api_gateway_event):
    """ Test database error handling"""
    # Mock the database session to raise an SQLAlchemyError
    mock_get_db.side_effect = SQLAlchemyError("Database error")
    
    # Create a test event
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    event = api_gateway_event(
        http_method="GET",
        path_params={"id": str(file_id)},
        auth_user=str(user_id),
    )
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 500
    assert body["status"] == "Internal Server Error"
    assert "Failed to establish database connection" in body["error_details"]
