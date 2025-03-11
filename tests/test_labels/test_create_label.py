import json
import pytest
import uuid
from unittest.mock import patch
from labels.create_label import lambda_handler
from models import Label
from sqlalchemy.exc import SQLAlchemyError
def test_create_label_success(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding a new user-created label."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"label_text": "New User Label"}

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    body = json.loads(response["body"])
    assert response["statusCode"] == 201
    assert "labels_created" in body["data"]
    assert len(body["data"]["labels_created"]) == 1

def test_create_multiple_labels(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding multiple labels in one request."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"labels": ["Label One", "Label Two", "Label Three"]}

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 201  # All labels should succeed
    assert len(body["data"]["labels_created"]) == 3


def test_create_too_many_labels_in_one_request(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding too many labels in a single request (should return 400)."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"labels": [f"Label {i}" for i in range(11)]}  # Exceeds batch limit (assuming 10 max)

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400  # Request exceeds batch limit

def test_create_batch_with_duplicates(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding multiple labels where some are duplicates (should return 207 Multi-Status)."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"labels": ["New Label", "User Label", "Another Label", "User Label"]}  # "User Label" exists

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    body = json.loads(response["body"])
    assert response["statusCode"] == 207  # Some succeeded, some failed
    assert len(body["data"]["labels_created"]) == 2  # Only 2 new labels should be created
    assert len(body["data"]["labels_failed"]) == 2  # 2 duplicate labels should be rejected



def test_create_label_duplicate(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a duplicate label (should return 409 Conflict)."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"label_text": "User Label"}  # Already exists

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 409

def test_create_label_invalid_format(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a label with invalid format (empty, too long)."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"label_text": ""}  # Empty label

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400  # Label must not be empty

    payload = {"label_text": "A" * 300}  # Too long
    event["body"] = json.dumps(payload)
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400  # Label is too long

def test_create_label_too_many(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding too many labels to a single file."""
    file_id, user_id, _ = seed_file_with_labels

    # Add 50 labels (assuming 50 is the limit)
    for i in range(50):
        label = Label(file_id=file_id, label_text=f"Label {i}", is_ai_generated=False)
        test_db.add(label)
    test_db.commit()

    # Try adding one more label
    payload = {"label_text": "Overflow Label"}
    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400  # Exceeds max label limit

def test_create_labels_exceeding_file_limit(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding labels that exceed the per-file limit."""
    file_id, user_id, _ = seed_file_with_labels

    # Fill the file with max labels
    for i in range(50):
        test_db.add(Label(file_id=file_id, label_text=f"Existing Label {i}", is_ai_generated=False))
    test_db.commit()

    # Try adding more labels
    payload = {"labels": ["Extra Label 1", "Extra Label 2"]}
    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 400  # File limit exceeded


def test_create_label_unauthorized(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a label to a file the user does not own (should return 404 Not Found)."""
    file_id, _, _ = seed_file_with_labels
    payload = {"label_text": "Unauthorized Label"}

    # Authenticate as a different user
    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(uuid.uuid4()))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404

def test_create_label_special_characters(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a label with disallowed special characters (should return 400)."""
    file_id, user_id, _ = seed_file_with_labels
    invalid_labels = ["$@#%^!", "<script>", "DROP TABLE users;", "\nTabLabel"]

    for label in invalid_labels:
        payload = {"label_text": label}
        event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 400  # Should reject invalid characters

def test_create_label_whitespace_handling(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding a label with leading/trailing whitespace (should be stripped)."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"label_text": "   Trimmed Label   "}

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 201
    stored_label = test_db.query(Label).filter(Label.file_id == file_id, Label.label_text == "Trimmed Label").first().label_text
    assert stored_label == "Trimmed Label"  # Ensure stored value is trimmed

def test_create_label_database_failure(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test handling a database failure when adding labels (should return 500)."""
    file_id, user_id, _ = seed_file_with_labels
    payload = {"labels": ["DB Error Label"]}

    # ✅ Mock the database session's `commit()` method to raise an exception
    with patch.object(test_db, "commit", side_effect=SQLAlchemyError("DB Failure")):
        event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 500  # ✅ Now correctly checks for 500