import json
import pytest
import uuid
from labels.restore_label import lambda_handler
from models import Label
from models.file_labels import FileLabel
from models.file import File
from models.household import Household
from models.user import User
@pytest.fixture
def seed_soft_deleted_ai_label(test_db, seed_file_with_labels):
    """Ensure an AI label is soft deleted before testing restore functionality."""
    file_id, user_id, household_id, ai_label_id, _ = seed_file_with_labels

    file_label = test_db.query(FileLabel).filter(
        FileLabel.file_id == file_id, FileLabel.label_id == ai_label_id
    ).first()

    file_label.deleted = True
    test_db.commit()

    return file_id, user_id, ai_label_id

@pytest.fixture
def seed_soft_deleted_user_label(test_db, seed_file_with_labels):
    """Ensure a user-created label is soft deleted before testing restore."""
    file_id, user_id, household_id, _, user_label_id = seed_file_with_labels

    file_label = test_db.query(FileLabel).filter(
        FileLabel.file_id == file_id, FileLabel.label_id == user_label_id
    ).first()

    file_label.deleted = True
    test_db.commit()

    return file_id, user_id, user_label_id

# ✅ **Test: Restore AI Label Successfully**
def test_restore_ai_label(api_gateway_event, test_db, seed_soft_deleted_ai_label):
    """✅ Test that an AI label can be restored after being soft deleted."""
    file_id, user_id, ai_label_id= seed_soft_deleted_ai_label

    event = api_gateway_event("PATCH", path_params={"file_id": str(file_id), "label_id": str(ai_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200  # ✅ Should return success

    file_label = test_db.query(FileLabel).filter(
        FileLabel.file_id == file_id, FileLabel.label_id == ai_label_id
    ).first()
    assert not file_label.deleted  # ✅ Label should be reactivated

# ❌ **Test: Restore User Label Should Fail**
def test_restore_user_label_fails(api_gateway_event, test_db, seed_soft_deleted_user_label):
    """❌ Test that a user-created label cannot be restored."""
    file_id, user_id, user_label_id = seed_soft_deleted_user_label

    event = api_gateway_event("PATCH", path_params={"file_id": str(file_id), "label_id": str(user_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 403  # 🚨 Forbidden

# ❌ **Test: Restoring Non-Existing Label Should Fail**
def test_restore_nonexistent_label(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test restoring a label that doesn't exist in the file."""
    file_id, user_id, _, _, _ = seed_file_with_labels
    fake_label_id = uuid.uuid4()

    event = api_gateway_event("PATCH", path_params={"file_id": str(file_id), "label_id": str(fake_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404  # 🚨 Not found

# ❌ **Test: Restoring a Label Already Active Should Return 200 (No Change)**
def test_restore_already_active_label(api_gateway_event, test_db, seed_file_with_labels):
    """✅ Test that restoring an already active label does not change anything."""
    file_id, user_id, _, ai_label_id, _ = seed_file_with_labels

    event = api_gateway_event("PATCH", path_params={"file_id": str(file_id), "label_id": str(ai_label_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200  # ✅ No change, label is already active

# ❌ **Test: Unauthorized User Cannot Restore a Label**
def test_restore_label_unauthorized(api_gateway_event, test_db, seed_soft_deleted_ai_label):
    """❌ Test that a user cannot restore a label on a file they do not own."""
    file_id, _, ai_label_id = seed_soft_deleted_ai_label
    unauthorized_user = uuid.uuid4()  # 🚨 Different user ID
    unauthorized_household = uuid.uuid4()
    test_db.add(Household(id=unauthorized_household, name="Unauthorized Household"))
    test_db.add(User(id=unauthorized_user, household_id=unauthorized_household, email=f"{unauthorized_user}@example.com", first_name="Unauthorized", last_name="User"))
    test_db.commit()
    event = api_gateway_event("PATCH", path_params={"file_id": str(file_id), "label_id": str(ai_label_id)}, auth_user=str(unauthorized_user))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404  # ✅ Should return 404 to prevent info leaks

# ❌ **Test: Restoring Label When File Does Not Exist**
def test_restore_label_file_not_found(api_gateway_event, test_db, seed_file_with_labels):
    """❌ Test restoring a label for a file that does not exist."""
    _, user_id, _, _, _ = seed_file_with_labels
    fake_file_id = uuid.uuid4()
    fake_label_id = uuid.uuid4()

    event = api_gateway_event("PATCH", path_params={"file_id": str(fake_file_id), "label_id": str(fake_label_id)}, auth_user=str(user_id))
    
    response = lambda_handler(event, {}, db_session=test_db)
    print(response)
    assert response["statusCode"] == 404  # 🚨 File not found
