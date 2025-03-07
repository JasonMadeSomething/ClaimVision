"""Test retrieving files for a user"""
import json
import uuid
import pytest
from files.get_files import lambda_handler
from models import File, User, Household
from models.file import FileStatus

@pytest.fixture
def seed_files(test_db):
    """Insert multiple test files into the database."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id,
    )

    test_files = [
        File(
            id=uuid.uuid4(),
            uploaded_by=user_id,
            household_id=household_id,
            file_name=f"file_{i}.jpg",
            s3_key=f"key_{i}",
            status=FileStatus.UPLOADED,
            labels=[],
            file_metadata={"mime_type": "image/jpeg", "size": 1234 + i},
        )
        for i in range(5)
    ]

    test_db.add_all([test_household, test_user, *test_files])
    test_db.commit()

    return user_id, household_id, test_files


@pytest.mark.usefixtures("seed_files")
def test_get_files_success(api_gateway_event, test_db, seed_files):
    """Test retrieving files successfully."""
    user_id, _, _ = seed_files

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "10"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "message" in body
    assert body["message"] == "Files retrieved successfully"
    assert len(body["data"]["files"]) == 5


def test_get_files_pagination(api_gateway_event, test_db, seed_files):
    """Test retrieving files with pagination."""
    user_id, _, _ = seed_files

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "2", "offset": "0"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "message" in body
    assert len(body["data"]["files"]) == 2


def test_get_files_empty(api_gateway_event, test_db):
    """Test retrieving files when none exist."""
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Empty Household")
    test_user = User(
        id=user_id,
        email="empty@example.com",
        first_name="Empty",
        last_name="User",
        household_id=household_id,
    )

    test_db.add_all([test_household, test_user])
    test_db.commit()

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "10"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "message" in body
    assert len(body["data"]["files"]) == 0


def test_get_files_invalid_limit(api_gateway_event, test_db, seed_files):
    """Test retrieving files with an invalid limit parameter (should return 400 Bad Request)"""
    user_id, _, _ = seed_files

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "invalid"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "error_details" in body
    assert body["error_details"] == "Invalid pagination parameters"
