import json
import pytest
import uuid
from unittest.mock import patch
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from labels.get_labels import lambda_handler
from models import Label, File, Household, User
from models.file_labels import FileLabel

def test_get_labels_success(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test retrieving all labels for a file."""
    file_id, user_id, _ = seed_file_with_labels
    event = api_gateway_event("GET", path_params={"file_id": str(file_id)}, auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["labels"]) == 2  # ✅ Includes soft-deleted AI label

def test_get_labels_file_not_found(api_gateway_event, test_db):
    """❌ Test retrieving labels for a non-existent file."""
    fake_file_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    event = api_gateway_event("GET", path_params={"file_id": fake_file_id}, auth_user=user_id)

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 404

def test_get_labels_unauthorized(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test retrieving labels for a file the user does not have access to."""
    file_id, _, _ = seed_file_with_labels  # ✅ File exists, but the user doesn't belong to the household
    unauthorized_user_id = str(uuid.uuid4())

    event = api_gateway_event("GET", path_params={"file_id": str(file_id)}, auth_user=unauthorized_user_id)
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404  # ✅ Prevents leaking file existence

def test_get_labels_empty(api_gateway_event, test_db):
    """✅ Test retrieving labels when a file has none."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_file = File(id=file_id, uploaded_by=user_id, household_id=household_id, file_name="empty.jpg", s3_key="empty-key")

    test_db.add_all([test_household, test_user, test_file])
    test_db.commit()

    event = api_gateway_event("GET", path_params={"file_id": str(file_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["labels"]) == 0  # ✅ No labels exist

def test_get_labels_database_failure(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test handling a database failure when retrieving labels."""
    file_id, user_id, _ = seed_file_with_labels

    with patch.object(test_db, "query", side_effect=SQLAlchemyError("DB Failure")):
        event = api_gateway_event("GET", path_params={"file_id": str(file_id)}, auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 500  # ✅ Now correctly checks for 500

def test_get_labels_excludes_soft_deleted_ai_labels(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test that soft-deleted AI labels are not returned in get labels response."""
    
    file_id, user_id, household_id = seed_file_with_labels

    # ✅ Create labels: One AI (soft deleted), One User (should always show)
    ai_label = Label(
        label_text="Soft Deleted AI Label",
        is_ai_generated=True,
        deleted=True,  # ✅ Soft-deleted
        household_id=household_id
    )
    user_label = Label(
        label_text="Potato Label",
        is_ai_generated=False,
        deleted=False,
        household_id=household_id
    )

    test_db.add_all([ai_label, user_label])
    test_db.commit()

    # ✅ Link labels to the file
    test_db.add_all([
        FileLabel(file_id=file_id, label_id=ai_label.id),
        FileLabel(file_id=file_id, label_id=user_label.id)
    ])
    test_db.commit()

    # 🔹 Perform GET request to retrieve labels
    event = api_gateway_event("GET", path_params={"file_id": str(file_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    # ✅ Assertions: Ensure soft-deleted AI labels are **excluded**
    assert response["statusCode"] == 200
    label_texts = [label["label_text"] for label in body["data"]["labels"]]

    assert "Soft Deleted AI Label" not in label_texts  # ❌ Soft-deleted AI label should be hidden
    assert "Potato Label" in label_texts  # ✅ User-created labels should always be present
