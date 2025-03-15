import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from labels.create_label import lambda_handler
from models import Label, File
from models.file_labels import FileLabel


def test_create_label_success(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding a new label to a file."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    payload = {"labels": ["New Label"]}

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 201
    assert len(body["data"]["labels_created"]) == 1

def test_create_multiple_labels(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding multiple labels in one request."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    payload = {"labels": ["Label One", "Label Two", "Label Three"]}

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 201  # All labels should succeed
    assert len(body["data"]["labels_created"]) == 3


def test_create_too_many_labels_in_one_request(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding too many labels in a single request (should return 400)."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    payload = {"labels": [f"Label {i}" for i in range(11)]}  # Exceeds batch limit (assuming 10 max)

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400  # Request exceeds batch limit

def test_create_batch_with_duplicates(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding multiple labels where some are duplicates (should return 207 Multi-Status)."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    payload = {"labels": ["New Label", "User Label", "Another Label", "User Label"]}  # "User Label" exists

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    body = json.loads(response["body"])
    assert response["statusCode"] == 207  # Some succeeded, some failed
    assert len(body["data"]["labels_created"]) == 2  # Only 2 new labels should be created
    assert len(body["data"]["labels_failed"]) == 2  # 2 duplicate labels should be rejected



def test_create_label_duplicate(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a duplicate label (should return 409 Conflict)."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    payload = {"label_text": "User Label"}  # Already exists

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 409

def test_create_label_invalid_format(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a label with invalid format (empty, too long)."""
    file_id, user_id, _, _, _ = seed_file_with_labels
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
    file_id, user_id, household_id, _, _ = seed_file_with_labels

    # Add 50 labels (assuming 50 is the limit)
    for i in range(50):
        label = Label(label_text=f"Existing Label {i}", is_ai_generated=False, household_id=household_id)
        test_db.add(label)
        test_db.commit()  # Ensure label ID is generated before linking

    # ✅ Associate label with the file
        file_label = FileLabel(file_id=file_id, label_id=label.id)
        test_db.add(file_label)
    test_db.commit()

    # Try adding one more label
    payload = {"label_text": "Overflow Label"}
    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400  # Exceeds max label limit

def test_create_labels_exceeding_file_limit(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding labels that exceed the per-file limit."""
    file_id, user_id, household_id, _, _ = seed_file_with_labels

    # Fill the file with max labels
    for i in range(50):
        label = Label(label_text=f"Existing Label {i}", is_ai_generated=False, household_id=household_id)
        test_db.add(label)
        test_db.commit()  # Ensure label ID is generated before linking

    # ✅ Associate label with the file
        file_label = FileLabel(file_id=file_id, label_id=label.id)
        test_db.add(file_label)
    test_db.commit()


    # Try adding more labels
    payload = {"labels": ["Extra Label 1", "Extra Label 2"]}
    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 400  # File limit exceeded


def test_create_label_unauthorized(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a label to a file the user does not own (should return 404 Not Found)."""
    file_id, _, _, _, _ = seed_file_with_labels
    payload = {"label_text": "Unauthorized Label"}

    # Authenticate as a different user
    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(uuid.uuid4()))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404

def test_create_label_special_characters(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test adding a label with disallowed special characters (should return 400)."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    invalid_labels = ["$@#%^!", "<script>", "DROP TABLE users;", "\nTabLabel"]

    for label in invalid_labels:
        payload = {"label_text": label}
        event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 400  # Should reject invalid characters

def test_create_label_whitespace_handling(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test adding a label with leading/trailing whitespace (should be stripped)."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    payload = {"label_text": "   Trimmed Label   "}

    event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 201
    
    stored_label = (
        test_db.query(Label)
        .join(FileLabel, FileLabel.label_id == Label.id)  # ✅ Join with FileLabel
        .filter(FileLabel.file_id == file_id, Label.label_text == "Trimmed Label")
        .first()
    )
    
    assert stored_label is not None, "Label should exist in the database"
    assert stored_label.label_text == "Trimmed Label"  # ✅ Ensure correct value

def test_create_label_database_failure(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test handling a database failure when adding labels (should return 500)."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    payload = {"labels": ["DB Error Label"]}

    # ✅ Mock the database session's `commit()` method to raise an exception
    with patch.object(test_db, "commit", side_effect=SQLAlchemyError("DB Failure")):
        event = api_gateway_event("POST", path_params={"file_id": str(file_id)}, body=json.dumps(payload), auth_user=str(user_id))
        response = lambda_handler(event, {}, db_session=test_db)

        assert response["statusCode"] == 500  # ✅ Now correctly checks for 500

def test_ai_and_user_can_have_identical_labels(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test that AI and user can create identical labels on different files."""
    file_id, user_id, household_id, ai_label_id, user_label_id = seed_file_with_labels

    first_file = test_db.query(File).filter(File.id == file_id).first()
    # ✅ Create a second file
    second_file_id = uuid.uuid4()
    second_file = File(
        id=second_file_id,
        uploaded_by=user_id,
        household_id=household_id,
        claim_id=first_file.claim_id,
        file_name="test2.jpg",
        s3_key="test-key-2"
    )
    test_db.add(second_file)
    test_db.commit()

    # ✅ AI assigns "Test Label" to first file
    ai_label = Label(label_text="Test Label", is_ai_generated=True, household_id=household_id, deleted=False)
    test_db.add(ai_label)
    test_db.commit()

    ai_file_label = FileLabel(file_id=file_id, label_id=ai_label.id)
    test_db.add(ai_file_label)
    test_db.commit()

    # ✅ User assigns "Test Label" to second file
    user_label = Label(label_text="Test Label", is_ai_generated=False, household_id=household_id, deleted=False)
    test_db.add(user_label)
    test_db.commit()

    user_file_label = FileLabel(file_id=second_file_id, label_id=user_label.id)
    test_db.add(user_file_label)
    test_db.commit()

    # ✅ Ensure both labels exist separately
    ai_label_from_db = test_db.query(Label).filter(Label.label_text == "Test Label", Label.is_ai_generated == True).first()
    user_label_from_db = test_db.query(Label).filter(Label.label_text == "Test Label", Label.is_ai_generated == False).first()

    assert ai_label_from_db is not None, "AI label should exist."
    assert user_label_from_db is not None, "User label should exist."
    assert ai_label_from_db.id != user_label_from_db.id, "AI and User labels should be distinct."
