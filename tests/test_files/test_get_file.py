"""✅ Test retrieving a single file from PostgreSQL"""
import json
import pytest
from files.get_file import lambda_handler
from models import File  # Assuming your SQLAlchemy model is named File

@pytest.fixture
def seed_files(test_db):
    """Insert test file data into the database."""
    test_file = File(
        id="file-1",
        user_id="user-123",
        file_name="test.pdf",
        s3_key="test-key",
        uploaded_at="2025-02-16T22:39:25.452734",
        description=None,
        claim_id=None,
        labels=[],  # ✅ Ensure this is a list, not a string
        status="uploaded",
        file_url="https://example.com/test.pdf",  # ✅ Provide a default value
        mime_type="application/pdf",  # ✅ Provide a default value
        size=12345,  # ✅ Provide a default value
        resolution=None,
        detected_objects=[],
    )
    test_db.add(test_file)
    test_db.commit()

@pytest.mark.usefixtures("seed_files")
def test_get_file_success(api_gateway_event, test_db):
    """✅ Test retrieving a single file successfully"""

    event = api_gateway_event(
        http_method="GET",
        path_params={"id": "file-1"},
        auth_user="user-123",
    )

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["id"] == "file-1"

def test_get_file_not_found(api_gateway_event, test_db):
    """❌ Test retrieving a non-existent file"""

    event = api_gateway_event(
        http_method="GET",
        path_params={"id": "file-99"},
        auth_user="user-123",
    )

    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
