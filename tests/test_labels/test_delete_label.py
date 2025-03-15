import json
import pytest
import uuid
from unittest.mock import patch
from labels.delete_label import lambda_handler
from models.file_labels import FileLabel
from models import User, Label, File, Household


# **Test: Hard delete user-created labels**
def test_delete_user_label(api_gateway_event, test_db, seed_file_with_labels):
    """ Test that user-created labels are **hard deleted**."""
    file_id, user_id, _, _, user_label_id = seed_file_with_labels

    event = api_gateway_event("DELETE", path_params={"label_id": str(user_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # No Content
    assert not test_db.query(Label).filter(Label.id == user_label_id).first()  # Hard delete


# **Test: Soft delete AI-generated labels**
def test_delete_ai_label(api_gateway_event, test_db, seed_file_with_labels):
    """ Test that AI-generated labels are **soft deleted** instead of removed from the database**."""
    file_id, user_id, _, ai_label_id, _  = seed_file_with_labels

    event = api_gateway_event("DELETE", path_params={"label_id": str(ai_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # No Content
    label = test_db.query(Label).filter(Label.id == ai_label_id).first()
    assert label is not None  # Label still exists
    assert label.deleted is True  # Soft deleted


# **Test: Unauthorized label deletion**
def test_delete_label_unauthorized(api_gateway_event, test_db, seed_labels):
    """ Test that a user **cannot delete a label** if they don’t own the file."""
    file_id, _, ai_label_id, user_label_id = seed_labels
    unauthorized_user_id = uuid.uuid4()  # Different user ID
    unauthorized_household_id = uuid.uuid4()
    unauthorized_houshold = Household(
        id=unauthorized_household_id,
        name="Unauthorized Household"
    )
    # Create unauthorized user
    unauthorized_user = User(
        id=unauthorized_user_id,
        email=f"{unauthorized_user_id}@example.com",
        first_name="Unauthorized",
        last_name="User",
        household_id=unauthorized_household_id
    )
    test_db.add(unauthorized_user)
    test_db.add(unauthorized_houshold)
    test_db.commit()

    event = api_gateway_event("DELETE", path_params={"label_id": str(user_label_id)}, auth_user=str(unauthorized_user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404  # Secure: Pretend label doesn’t exist


# **Test: Label not found**
def test_delete_label_not_found(api_gateway_event, test_db, seed_labels):
    """ Test deleting a **nonexistent label** returns 404."""
    file_id, user_id, _, _ = seed_labels

    fake_label_id = uuid.uuid4()
    event = api_gateway_event("DELETE", path_params={"label_id": str(fake_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404  # Label not found


# **Test: Deleting a label removes it from FileLabel**
def test_delete_label_removes_from_file_label(api_gateway_event, test_db, seed_labels):
    """ Test that **deleting a label removes its association** in `FileLabel`."""
    file_id, user_id, ai_label_id, user_label_id = seed_labels

    event = api_gateway_event("DELETE", path_params={"label_id": str(user_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204  # No Content
    assert not test_db.query(FileLabel).filter(FileLabel.label_id == user_label_id).first()  # Removed from FileLabel


# **Test: Prevent orphaned file records**
def test_delete_last_label_does_not_affect_file(api_gateway_event, test_db, seed_labels):
    """ Test that **deleting the last label** does not remove or alter the file itself."""
    file_id, user_id, ai_label_id, user_label_id = seed_labels

    # Delete both labels
    event_ai = api_gateway_event("DELETE", path_params={"label_id": str(ai_label_id)}, auth_user=str(user_id))
    event_user = api_gateway_event("DELETE", path_params={"label_id": str(user_label_id)}, auth_user=str(user_id))

    lambda_handler(event_ai, {}, db_session=test_db)
    lambda_handler(event_user, {}, db_session=test_db)

    # Ensure file still exists
    assert test_db.query(File).filter(File.id == file_id).first() is not None


def test_global_delete_only_affects_user_labels(api_gateway_event, test_db, seed_file_with_labels):
    """ Test that deleting a label globally removes user labels but keeps AI labels intact."""
    file_id, user_id, household_id, ai_label_id, user_label_id = seed_file_with_labels

    # Create AI label
    ai_label = Label(label_text="Test Label", is_ai_generated=True, household_id=household_id, deleted=False)
    test_db.add(ai_label)
    test_db.commit()

    ai_file_label = FileLabel(file_id=file_id, label_id=ai_label.id)
    test_db.add(ai_file_label)
    test_db.commit()

    # Create User label
    user_label = Label(label_text="Test Label", is_ai_generated=False, household_id=household_id, deleted=False)
    test_db.add(user_label)
    test_db.commit()

    user_file_label = FileLabel(file_id=file_id, label_id=user_label.id)
    test_db.add(user_file_label)
    test_db.commit()

    # Store the AI label ID for later querying
    ai_label_id_to_check = ai_label.id
    user_label_id_to_check = user_label.id

    # Delete the user label globally
    event = api_gateway_event("DELETE", path_params={"label_id": str(user_label.id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204, "User label should be deleted successfully."

    # Ensure AI label still exists - query fresh instances to avoid detached session issues
    ai_label_from_db = test_db.query(Label).filter(Label.id == ai_label_id_to_check).first()
    user_label_from_db = test_db.query(Label).filter(Label.id == user_label_id_to_check).first()

    assert ai_label_from_db is not None, "AI label should still exist after user label deletion."
    assert user_label_from_db is None, "User label should be completely removed."
