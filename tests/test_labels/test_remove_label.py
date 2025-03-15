import json
import pytest
import uuid
from unittest.mock import patch
from labels.remove_label import lambda_handler
from models import Label, File, User, Household
from models.file_labels import FileLabel


# ✅ **Test: Remove a user-created label from a file (label remains in DB)**
def test_remove_user_label_from_file(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test removing a user label from a file (label remains, just unlinked)."""
    file_id, user_id, _, _, user_label_id = seed_file_with_labels

    event = api_gateway_event("DELETE", path_params={"file_id": str(file_id), "label_id": str(user_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # ✅ No Content
    assert not test_db.query(FileLabel).filter(FileLabel.file_id == file_id, FileLabel.label_id == user_label_id).first()  # ✅ Unlinked
    assert test_db.query(Label).filter(Label.id == user_label_id).first() is None  # ✅ Label does not exist


# ✅ **Test: Remove an AI-generated label from a file (label is soft deleted)**
def test_remove_ai_label_per_file(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test removing an AI label from a single file (soft delete in FileLabel)."""
    file_id, user_id, _, ai_label_id, _ = seed_file_with_labels

    event = api_gateway_event("DELETE", path_params={"file_id": str(file_id), "label_id": str(ai_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # ✅ No Content

    file_label_entry = test_db.query(FileLabel).filter(
        FileLabel.file_id == file_id, FileLabel.label_id == ai_label_id
    ).first()
    assert file_label_entry is not None  # ✅ File label entry should still exist
    assert file_label_entry.deleted is True  # ✅ Soft deleted in join table

    label = test_db.query(Label).filter(Label.id == ai_label_id).first()
    assert label is not None  # ✅ Label still exists globally
    assert label.deleted is False  # ✅ AI label is NOT globally deleted



# ✅ **Test: Removing a label from a file does not delete it if linked elsewhere**
def test_remove_label_keeps_shared_label(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test that removing a label from one file **does not delete it** if linked to other files."""
    file_id, user_id, household_id, _, user_label_id = seed_file_with_labels
    second_file_id = uuid.uuid4()
    file = test_db.query(File).filter(File.id == file_id).first()
    test_file = File(
        id=second_file_id,
        uploaded_by=user_id,
        household_id=household_id,
        claim_id=file.claim_id,  # Assign to the same claim
        file_name="test2.jpg",
        s3_key="test-key-2",
        file_hash="test_hash2"
    )
    test_db.add(test_file)
    test_db.commit()
    assert test_db.query(File).filter(File.id == second_file_id).first() is not None, "Second file should exist before linking label."

    # ✅ Associate label with a second file
    test_db.add(FileLabel(file_id=second_file_id, label_id=user_label_id))
    test_db.commit()

    event = api_gateway_event("DELETE", path_params={"file_id": str(file_id), "label_id": str(user_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # ✅ No Content
    assert not test_db.query(FileLabel).filter(FileLabel.file_id == file_id, FileLabel.label_id == user_label_id).first()  # ✅ Unlinked from first file
    assert test_db.query(FileLabel).filter(FileLabel.file_id == second_file_id, FileLabel.label_id == user_label_id).first() is not None  # ✅ Still linked elsewhere
    assert test_db.query(Label).filter(Label.id == user_label_id).first() is not None  # ✅ Label still exists


# ✅ **Test: Unauthorized removal attempt**
def test_remove_label_unauthorized(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test that a user cannot remove a label from a file they don't own."""
    file_id, user_id, _, user_label_id, _ = seed_file_with_labels
    unauthorized_user_id = uuid.uuid4()  # 🚨 Different user ID

    unauthorized_household_id = uuid.uuid4()
    unauthorized_household = Household(
        id=unauthorized_household_id,
        name="Unauthorized Household"
    )
    test_db.add(unauthorized_household)
    test_db.commit()

    # ✅ Create unauthorized user
    unauthorized_user = User(
        id=unauthorized_user_id,
        email=f"{unauthorized_user_id}@example.com",
        first_name="Unauthorized",
        last_name="User",
        household_id=unauthorized_household_id
    )
    test_db.add(unauthorized_user)
    test_db.commit()

    event = api_gateway_event("DELETE", path_params={"file_id": str(file_id), "label_id": str(user_label_id)}, auth_user=str(unauthorized_user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404  # ✅ Secure: Pretend it doesn’t exist


# ✅ **Test: Label removal does not affect file**
def test_remove_label_does_not_delete_file(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test that removing a label does not remove or alter the file itself."""
    file_id, user_id, _, user_label_id, _ = seed_file_with_labels

    event = api_gateway_event("DELETE", path_params={"file_id": str(file_id), "label_id": str(user_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # ✅ No Content
    assert test_db.query(File).filter(File.id == file_id).first() is not None  # ✅ File still exists

def test_remove_ai_label_keeps_other_files(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test that removing an AI label from one file does not affect other files."""
    file_id, user_id, _, ai_label_id, _ = seed_file_with_labels
    second_file_id = uuid.uuid4()
    user = test_db.query(User).filter(User.id == user_id).first()
    file = test_db.query(File).filter(File.id == file_id).first()
    second_file = File(
        id=second_file_id,
        uploaded_by=user_id,
        household_id=user.household_id,
        claim_id=file.claim_id,
        file_name="test2.jpg",
        s3_key="test-key-2",
        file_hash="test_hash2"
    )
    test_db.add(second_file)
    test_db.commit()
    # ✅ Associate label with a second file
    test_db.add(FileLabel(file_id=second_file_id, label_id=ai_label_id, deleted=False))
    test_db.commit()

    event = api_gateway_event("DELETE", path_params={"file_id": str(file_id), "label_id": str(ai_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # ✅ No Content

    # ✅ Label should be deleted only for first file
    assert test_db.query(FileLabel).filter(FileLabel.file_id == file_id, FileLabel.label_id == ai_label_id, FileLabel.deleted.is_(True)).first() is not None
    assert test_db.query(FileLabel).filter(FileLabel.file_id == second_file_id, FileLabel.label_id == ai_label_id, FileLabel.deleted.is_(False)).first() is not None  # ✅ Still active for second file
