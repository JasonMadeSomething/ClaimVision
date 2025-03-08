import json
import uuid
import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from models import File, Household, User, Claim
from files.delete_file import lambda_handler

@pytest.fixture
def seed_file(test_db):
    """Insert a test file attached to a claim for deletion tests."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id
    )

    test_claim = Claim(id=claim_id, household_id=household_id, title="Lost Item")

    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        claim_id=claim_id,  # ✅ File is always attached to a claim
        file_name="deletable.jpg",
        s3_key="deletable-key",
        deleted_at=None,
        deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        file_hash="test_hash"
    )

    test_db.add_all([test_household, test_user, test_claim, test_file])
    test_db.commit()

    return file_id, user_id, household_id, claim_id

def test_delete_file_soft_delete(api_gateway_event, test_db, seed_file):
    """✅ Test soft-deleting a file attached to a claim."""
    file_id, user_id, _, _ = seed_file

    event = api_gateway_event(http_method="DELETE", path_params={"id": str(file_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204
    file = test_db.query(File).filter_by(id=file_id).first()
    assert file.deleted is True
    assert file.deleted_at is not None  # ✅ Soft delete

def test_delete_file_not_found(api_gateway_event, test_db):
    """❌ Test deleting a file that does not exist (should return 404)."""
    event = api_gateway_event(http_method="DELETE", path_params={"id": str(uuid.uuid4())}, auth_user=str(uuid.uuid4()))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404

def test_delete_file_unauthorized(api_gateway_event, test_db, seed_file):
    """❌ Test deleting a file from another household (should return 404)."""
    file_id, _, _, _ = seed_file
    unauthorized_user_id = uuid.uuid4()

    event = api_gateway_event(http_method="DELETE", path_params={"id": str(file_id)}, auth_user=str(unauthorized_user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404

def test_delete_file_without_claim(api_gateway_event, test_db):
    """❌ Test deleting a file that isn't attached to a claim (should return 400)."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id
    )

    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        claim_id=None,  # 🚨 No claim attached
        file_name="orphaned.jpg",
        s3_key="orphaned-key",
        deleted_at=None,
        deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    test_db.add_all([test_household, test_user, test_file])
    test_db.commit()

    event = api_gateway_event(http_method="DELETE", path_params={"id": str(file_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    assert "Files must be attached to a claim" in json.loads(response["body"])["error_details"]

