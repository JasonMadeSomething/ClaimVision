import json
import os
import sys
import uuid
from unittest.mock import MagicMock, patch
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from models.file_labels import FileLabel
from sqlalchemy import text
from models import Base, File, Household, User, Label
from models.file import FileStatus
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from models.item import Item
from models.claim import Claim
load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))



# -----------------
# ENVIRONMENT MOCKS
# -----------------
@pytest.fixture(scope="session", autouse=True)
def mock_env():
    """Set required environment variables for testing."""
    # Save original environment variables
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["DATABASE_URL"] = "postgresql://testuser:testpassword@localhost:5432/testdb"
    os.environ["S3_BUCKET_NAME"] = "test-bucket"
    os.environ["COGNITO_USER_POOL_ID"] = "us-east-1_testpool"
    os.environ["COGNITO_USER_POOL_CLIENT_ID"] = "1234567890abcdef1234567890"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["COGNITO_USER_POOL_CLIENT_SECRET"] = "test-user-pool-client-secret"
    os.environ["SQS_UPLOAD_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123456789012/test-upload-queue"
    os.environ["SQS_ANALYSIS_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123456789012/test-analysis-queue"
    os.environ["MIN_CONFIDENCE"] = "70"
    
    yield
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)

# -----------------
# DATABASE FIXTURE
# -----------------
@pytest.fixture(scope="function", autouse=True)
def test_db():
    """Provides a fresh test database for each test function."""
    engine = create_engine(os.getenv("DATABASE_URL"))
    TestingSessionLocal = sessionmaker(bind=engine)

    # Ensure tables are dropped and recreated before each test
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS file_labels CASCADE;"))  # Drop join table first
        conn.execute(text("DROP TABLE IF EXISTS labels CASCADE;"))  # Drop labels next
        conn.execute(text("DROP TABLE IF EXISTS files CASCADE;"))  # Now it's safe to drop files
        Base.metadata.drop_all(conn)
        Base.metadata.create_all(conn)

    session = TestingSessionLocal()

    yield session  # Provide session for the test

    # Teardown: Drop all tables after each test
    session.rollback()
    session.close()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS file_labels CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS labels CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS files CASCADE;"))
        Base.metadata.drop_all(conn)
    engine.dispose()
# -----------------
# API GATEWAY MOCKS
# -----------------
@pytest.fixture
def api_gateway_event():
    """Creates a mock API Gateway event for testing"""

    def _event(http_method="GET", path_params=None, query_params=None, body=None, auth_user="user-123"):
        """Generate an API event, allowing optional auth_user=None for unauthenticated tests"""
        event = {
            "httpMethod": http_method,
            "pathParameters": path_params or {},
            "queryStringParameters": query_params or {},
            "headers": {"Authorization": "Bearer fake-jwt-token"} if auth_user else {},
            "requestContext": {
                "authorizer": {"claims": {"sub": auth_user}} if auth_user else {}
            },
            "body": json.dumps(body) if isinstance(body, dict) else body,
        }
        return event

    return _event

# -----------------
# MOCK S3
# -----------------
@pytest.fixture
def mock_s3():
    """Mock S3 client for testing"""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_client.generate_presigned_url.return_value = "https://signed-url.com/file"
        yield mock_s3

# -----------------
# MOCK SQS
# -----------------
@pytest.fixture(autouse=True)
def mock_sqs():
    """Mock SQS client for testing"""
    with patch("boto3.client") as mock_boto3_client:
        mock_sqs = MagicMock()
        
        # Configure the mock to return our mock_sqs when boto3.client('sqs') is called
        def side_effect(service_name, *args, **kwargs):
            if service_name == 'sqs':
                return mock_sqs
            # For other services like s3, create a new mock
            return MagicMock()
            
        mock_boto3_client.side_effect = side_effect
        
        # Configure the mock SQS client's send_message method
        mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}
        
        # Ensure the SQS_ANALYSIS_QUEUE_URL is set
        with patch.dict("os.environ", {"SQS_ANALYSIS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/test-analysis-queue"}, clear=False):
            yield mock_sqs

# -----------------
# AUTH MOCKS
# -----------------
@pytest.fixture
def auth_event():
    """Mock API Gateway event with an authenticated user."""
    return {
        "requestContext": {
            "authorizer": {"claims": {"sub": "test-user-id"}}
        }
    }

@pytest.fixture(scope="function")
def mock_cognito():
    """Fully mock Cognito interactions for all tests."""
    with patch("boto3.client") as mock_boto_client:
        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client

        # Ensure a **unique** Cognito UserSub is generated per test
        def generate_unique_user_sub(*args, **kwargs):
            return {"UserSub": str(uuid.uuid4())}  # Unique ID for each test

        mock_cognito_client.sign_up.side_effect = generate_unique_user_sub  # Apply dynamic user generation

        # Assign exception classes directly, instead of using a nested class
        mock_cognito_client.exceptions = MagicMock()
        mock_cognito_client.exceptions.UsernameExistsException = type("UsernameExistsException", (Exception,), {})
        mock_cognito_client.exceptions.InvalidPasswordException = type("InvalidPasswordException", (Exception,), {})
        mock_cognito_client.exceptions.UserNotFoundException = type("UserNotFoundException", (Exception,), {})
        mock_cognito_client.exceptions.NotAuthorizedException = type("NotAuthorizedException", (Exception,), {})
        mock_cognito_client.exceptions.InternalErrorException = type("InternalErrorException", (Exception,), {})
        mock_cognito_client.exceptions.TooManyRequestsException = type("TooManyRequestsException", (Exception,), {})
        mock_cognito_client.exceptions.UserNotConfirmedException = type("UserNotConfirmedException", (Exception,), {})
        mock_cognito_client.exceptions.PasswordResetRequiredException = type("PasswordResetRequiredException", (Exception,), {})
        mock_cognito_client.exceptions.CodeMismatchException = type("CodeMismatchException", (Exception,), {})
        mock_cognito_client.exceptions.LimitExceededException = type("LimitExceededException", (Exception,), {})

        # Mock Attribute Updates (e.g., Household ID)
        mock_cognito_client.admin_update_user_attributes.return_value = {}

        # Mock Cognito Login - make sure this is a valid format for JWT decoding
        mock_cognito_client.initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "IdToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "RefreshToken": "mock-refresh-token"
            }
        }

        yield mock_cognito_client  # Provide mock to all tests

@pytest.fixture
def seed_file(test_db):
    """Inserts a test file into the database."""
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
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        file_name="original.jpg",
        s3_key="original-key",
        status=FileStatus.UPLOADED,
        file_metadata={"mime_type": "image/jpeg", "size": 12345},
        file_hash="test_hash"
    )

    test_db.add_all([test_household, test_user, test_claim, test_file])
    test_db.commit()

    return file_id, user_id, household_id

@pytest.fixture
def seed_files(test_db):
    """Insert multiple test files into the database."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id,
    )
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
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
            file_hash=f"test_hash_{i}",
            claim_id=claim_id
        )
        for i in range(5)
    ]

    test_db.add_all([test_household, test_user, test_claim, *test_files])
    test_db.commit()

    return user_id, household_id, test_files

@pytest.fixture
def seed_file_with_labels(test_db: Session):
    """Insert a test file with AI-generated and user-created labels, ensuring uniqueness."""

    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    # Create Household, User, and Claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Lost Item")

    # Create File
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        claim_id=claim_id,  # Files must belong to a claim
        file_name="test.jpg",
        s3_key="test-key",
        file_hash="test_hash"
    )

    # Insert Labels (Ensuring Unique Entries)
    ai_label = Label(id=uuid.uuid4(), label_text="AI Label", is_ai_generated=True, deleted=False, household_id=household_id)
    user_label = Label(id=uuid.uuid4(), label_text="User Label", is_ai_generated=False, deleted=False, household_id=household_id)

    test_db.add_all([test_household, test_user, test_claim, test_file, ai_label, user_label])
    test_db.commit()

    # Link Labels to File
    ai_file_label = FileLabel(file_id=file_id, label_id=ai_label.id)
    user_file_label = FileLabel(file_id=file_id, label_id=user_label.id)

    test_db.add_all([ai_file_label, user_file_label])
    test_db.commit()

    return file_id, user_id, household_id, ai_label.id, user_label.id  # Include label IDs

@pytest.fixture
def seed_labels(test_db: Session):
    """Insert a test file with labels for label deletion tests."""
    
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    # Create Household, User, and Claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")

    # Create File
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        claim_id=claim_id,
        file_name="test.jpg",
        s3_key="test-key",
        file_hash="test_hash"
    )

    # Insert Labels
    ai_label = Label(id=uuid.uuid4(), label_text="AI Label", is_ai_generated=True, deleted=False, household_id=household_id)
    user_label = Label(id=uuid.uuid4(), label_text="User Label", is_ai_generated=False, deleted=False, household_id=household_id)

    test_db.add_all([test_household, test_user, test_claim, test_file, ai_label, user_label])
    test_db.commit()

    # Link Labels to File
    ai_file_label = FileLabel(file_id=file_id, label_id=ai_label.id)
    user_file_label = FileLabel(file_id=file_id, label_id=user_label.id)

    test_db.add_all([ai_file_label, user_file_label])
    test_db.commit()

    return file_id, user_id, ai_label.id, user_label.id

@pytest.fixture
def seed_claim(test_db: Session):
    """Seeds a claim and returns its ID."""
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    file_id = uuid.uuid4()
    
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email=f"{user_id}@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim")
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        claim_id=claim_id,
        file_name="test.jpg",
        s3_key="test-key",
        file_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    test_db.add_all([test_household, test_user, test_claim, test_file])
    test_db.commit()
    
    return claim_id, user_id, file_id


@pytest.fixture
def seed_item(test_db: Session, seed_claim):
    """Seeds a single item under a claim."""
    claim_id, user_id, file_id = seed_claim
    item_id = uuid.uuid4()
    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_item = Item(id=item_id, claim_id=claim_id, name="Test Item", description="A sample item", estimated_value=100.00)
    test_db.add_all([test_household, test_item])
    test_db.commit()

    return item_id, user_id, file_id

@pytest.fixture
def seed_multiple_items(test_db: Session, seed_claim):
    """Seeds multiple items under the same claim."""
    claim_id, user_id, file_id = seed_claim
    item_ids = []

    for _ in range(3):
        item_id = uuid.uuid4()
        test_item = Item(id=item_id, claim_id=claim_id, name=f"Test Item {_}", description="A sample item", estimated_value=100.00)
        test_db.add_all([test_item])
        item_ids.append(item_id)

    test_db.commit()
    return claim_id, user_id, item_ids

@pytest.fixture
def seed_item_with_file_labels(test_db: Session, seed_item):
    """Seeds an item with a file and labels."""
    item_id, user_id, _ = seed_item  # Ignore the original file_id
    
    # Get the item to find its claim_id
    item = test_db.query(Item).filter(Item.id == item_id).first()
    user = test_db.query(User).filter(User.id == user_id).first()
    
    # Create file with the same claim_id and household_id
    test_file = File(
        id=uuid.uuid4(),
        uploaded_by=user_id,
        household_id=user.household_id,  # Use the same household_id as the user
        claim_id=item.claim_id,  # Use the same claim_id as the item
        file_name="test.jpg",
        s3_key="test-key",
        file_hash="test_file_hash"
    )
    test_db.add(test_file)
    test_db.commit()

    # Associate file with item
    test_db.add(ItemFile(item_id=item_id, file_id=test_file.id))
    test_db.commit()

    # Create labels with the same household_id
    label_1 = Label(
        id=uuid.uuid4(),
        label_text="TV",
        is_ai_generated=True,
        household_id=user.household_id  # Use the same household_id as the user
    )
    label_2 = Label(
        id=uuid.uuid4(),
        label_text="Couch",
        is_ai_generated=True,
        household_id=user.household_id  # Use the same household_id as the user
    )

    test_db.add_all([label_1, label_2])
    test_db.commit()

    # Associate only the TV label with the item
    test_db.add(ItemLabel(item_id=item_id, label_id=label_1.id))
    test_db.commit()

    return item_id, user_id, test_file.id

@pytest.fixture
def seed_multiple_items_with_labels(test_db: Session, seed_multiple_items):
    """Seeds multiple items, each with different labels, ensuring label inheritance is correct."""
    _, user_id, item_ids = seed_multiple_items
    labels = ["TV", "Couch", "Table"]
    
    # Get the user to find their household_id
    user = test_db.query(User).filter(User.id == user_id).first()
    
    # Ensure we're using the same household_id as the user
    household_id = user.household_id

    for i, item_id in enumerate(item_ids):
        # Create label with the same household_id as the user
        label = Label(
            id=uuid.uuid4(), 
            label_text=labels[i], 
            is_ai_generated=True, 
            household_id=household_id
        )
        test_db.add(label)
        test_db.commit()

        # Associate label with item
        test_db.add(ItemLabel(item_id=item_id, label_id=label.id))
        test_db.commit()

    return item_ids, user_id