import json
import uuid
import pytest
import base64
from hashlib import sha256
from models import File, Household, User, Claim
from files.upload_file import lambda_handler as upload_handler
from files.replace_file import lambda_handler as replace_handler

@pytest.fixture
def seed_household_user(test_db):
    """Creates a household and a user for testing."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    claim_id = uuid.uuid4()
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id
    )

    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    return household_id, user_id, claim_id

def test_upload_file_with_hash(api_gateway_event, test_db, seed_household_user):
    """✅ Ensure uploaded files are hashed correctly."""

    household_id, user_id, claim_id = seed_household_user
    file_data = b"testfiledata"
    file_hash = sha256(file_data).hexdigest()

    payload = {
        "files": [{"file_name": "test.jpg", "file_data": base64.b64encode(file_data).decode("utf-8")}],
        "claim_id": str(claim_id)
    }

    event = api_gateway_event(http_method="POST", body=json.dumps(payload), auth_user=str(user_id))
    response = upload_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    uploaded_file = test_db.query(File).first()
    assert uploaded_file.file_hash == file_hash  # ✅ Ensures correct hashing

def test_prevent_duplicate_upload(api_gateway_event, test_db, seed_household_user):
    """❌ Prevent duplicate file uploads (same hash)."""
    household_id, user_id, claim_id = seed_household_user
    file_data = b"duplicatefiledata"
    file_hash = sha256(file_data).hexdigest()

    # Upload the first file
    payload = {"files": [{"file_name": "dup1.jpg", "file_data": base64.b64encode(file_data).decode("utf-8")}],
               "claim_id": str(claim_id)}
    event = api_gateway_event(http_method="POST", body=json.dumps(payload), auth_user=str(user_id))
    response = upload_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200

    # Attempt to upload the same file again
    event = api_gateway_event(http_method="POST", body=json.dumps(payload), auth_user=str(user_id))
    response = upload_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 409  # ✅ Conflict due to duplicate hash
    assert "Duplicate file detected" in response["body"]

def test_replace_file_updates_hash(api_gateway_event, test_db, seed_household_user):
    """✅ Ensure replacing a file updates its hash."""
    household_id, user_id, claim_id = seed_household_user
    old_file_data = b"oldfiledata"
    new_file_data = b"newfiledata"

    old_file_hash = sha256(old_file_data).hexdigest()
    new_file_hash = sha256(new_file_data).hexdigest()

    # Upload initial file
    upload_payload = {"files": [{"file_name": "replace.jpg", "file_data": base64.b64encode(old_file_data).decode("utf-8")}],
                      "claim_id": str(claim_id)}
    event = api_gateway_event(http_method="POST", body=json.dumps(upload_payload), auth_user=str(user_id))
    response = upload_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    file = test_db.query(File).first()
    file_id = file.id
    assert file.file_hash == old_file_hash

    # Replace the file with new data
    replace_payload = {"file_name": "replace.jpg", "file_data": base64.b64encode(new_file_data).decode("utf-8"),
                       "claim_id": str(claim_id)}
    event = api_gateway_event(http_method="PUT", path_params={"id": str(file_id)}, body=json.dumps(replace_payload), auth_user=str(user_id))
    response = replace_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    updated_file = test_db.query(File).filter_by(id=file_id).first()
    assert updated_file.file_hash == new_file_hash  # ✅ Ensures hash is updated
