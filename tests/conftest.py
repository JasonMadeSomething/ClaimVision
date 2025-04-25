import json
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from models import Base, File, User, Group, Permission
from models.file import FileStatus
from models.group_membership import GroupMembership
from models.claim import Claim
from models.item import Item
from utils.vocab_enums import GroupTypeEnum, GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum, PermissionAction, ResourceTypeEnum

print(">>> conftest.py LOADED <<<")


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
        # Drop all tables with CASCADE to handle dependencies
        conn.execute(text("DROP TABLE IF EXISTS file_labels CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS item_files CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS item_labels CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS rooms CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS claims CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS items CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS files CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS labels CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS group_memberships CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS permissions CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS groups CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS group_types CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS group_roles CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS group_identities CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS membership_statuses CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS resource_types CASCADE;"))
        
        # Now recreate all tables
        Base.metadata.create_all(conn)
        
        # Basic reference data setup
        # Group Types
        conn.execute(text("INSERT INTO group_types (id, name, description, is_active) VALUES ('household', 'Household', 'A household group', TRUE)"))
        conn.execute(text("INSERT INTO group_types (id, name, description, is_active) VALUES ('firm', 'Firm', 'A business firm', TRUE)"))
        conn.execute(text("INSERT INTO group_types (id, name, description, is_active) VALUES ('partner', 'Partner', 'A partner organization', TRUE)"))
        conn.execute(text("INSERT INTO group_types (id, name, description, is_active) VALUES ('other', 'Other', 'Other group type', TRUE)"))
        
        # Group Roles
        conn.execute(text("INSERT INTO group_roles (id, label, description, is_active) VALUES ('owner', 'Owner', 'Group owner', TRUE)"))
        conn.execute(text("INSERT INTO group_roles (id, label, description, is_active) VALUES ('editor', 'Editor', 'Can edit', TRUE)"))
        conn.execute(text("INSERT INTO group_roles (id, label, description, is_active) VALUES ('viewer', 'Viewer', 'View only', TRUE)"))
        
        # Group Identities
        conn.execute(text("INSERT INTO group_identities (id, label, description, is_active) VALUES ('homeowner', 'Homeowner', 'Primary homeowner', TRUE)"))
        conn.execute(text("INSERT INTO group_identities (id, label, description, is_active) VALUES ('adjuster', 'Adjuster', 'Insurance adjuster', TRUE)"))
        conn.execute(text("INSERT INTO group_identities (id, label, description, is_active) VALUES ('contractor', 'Contractor', 'Repair contractor', TRUE)"))
        
        # Membership Statuses
        conn.execute(text("INSERT INTO membership_statuses (id, label, description, is_active) VALUES ('active', 'Active', 'Active membership', TRUE)"))
        conn.execute(text("INSERT INTO membership_statuses (id, label, description, is_active) VALUES ('invited', 'Invited', 'Invited membership', FALSE)"))
        conn.execute(text("INSERT INTO membership_statuses (id, label, description, is_active) VALUES ('revoked', 'Revoked', 'Revoked membership', FALSE)"))
        
        # Resource Types
        conn.execute(text("INSERT INTO resource_types (id, label, description, is_active) VALUES ('claim', 'Claim', 'Insurance claim', TRUE)"))
        conn.execute(text("INSERT INTO resource_types (id, label, description, is_active) VALUES ('file', 'File', 'Uploaded file', TRUE)"))
        conn.execute(text("INSERT INTO resource_types (id, label, description, is_active) VALUES ('item', 'Item', 'Item within a claim', TRUE)"))

    # Create a new session for the test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def seed_user_and_group(test_db):
    """Create a test user and group for testing."""
    # Create a test user
    user_id = uuid.uuid4()
    cognito_sub = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        cognito_sub=cognito_sub,
        first_name="Test",
        last_name="User"
    )
    test_db.add(user)
    test_db.flush()
    
    # Create a test group
    group_id = uuid.uuid4()
    group = Group(
        id=group_id,
        name="Test Group",
        group_type_id=GroupTypeEnum.HOUSEHOLD.value,
        created_at=datetime.now(timezone.utc),
        created_by=user_id
    )
    test_db.add(group)
    test_db.flush()
    
    # Create membership for the user in the group
    membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    test_db.add(membership)
    
    # Add permission for the user to create claims in the group
    write_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=str(user_id),
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=None,  # Applies to all claims
        action=PermissionAction.WRITE,
        conditions=json.dumps({"group_id": str(group_id)}),
        group_id=group_id
    )
    test_db.add(write_permission)
    
    # Add permission for the user to read claims in the group
    read_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=str(user_id),
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=None,  # Applies to all claims
        action=PermissionAction.READ,
        conditions=json.dumps({"group_id": str(group_id)}),
        group_id=group_id
    )
    test_db.add(read_permission)
    
    test_db.commit()
    
    return {
        "user_id": user_id,
        "group_id": group_id,
        "user": user,
        "group": group
    }

@pytest.fixture
def create_resource_permission(test_db):
    """
    Create a permission for a specific resource.
    
    This fixture returns a function that can be used to create permissions for specific resources,
    making it easier to test the ACL system with different resource types.
    
    Args:
        user_id: The ID of the user to grant permission to
        resource_type: The type of resource (from ResourceTypeEnum)
        resource_id: The ID of the specific resource (or None for all resources of this type)
        action: The permission action (from PermissionAction)
        group_id: The group ID to associate with the permission
        conditions: Optional conditions for the permission (default: group_id condition)
        
    Returns:
        The created Permission object
    """
    def _create_permission(user_id, resource_type, resource_id, action, group_id, conditions=None):
        if conditions is None:
            conditions = {"group_id": str(group_id)}
            
        permission = Permission(
            id=uuid.uuid4(),
            subject_type="user",
            subject_id=str(user_id),
            resource_type_id=resource_type,
            resource_id=resource_id,
            action=action,
            conditions=json.dumps(conditions),
            group_id=group_id
        )
        test_db.add(permission)
        test_db.commit()
        return permission
        
    return _create_permission

@pytest.fixture
def seed_multiple_users_and_groups(test_db):
    """
    Create multiple users and groups with different permission configurations.
    
    This fixture is useful for testing complex ACL scenarios where multiple users
    have different levels of access to different resources.
    
    Returns:
        dict: A dictionary containing the created users, groups, and their relationships
    """
    # Create users
    owner_id = uuid.uuid4()
    editor_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    
    owner = User(
        id=owner_id,
        email="owner@example.com",
        cognito_sub=str(uuid.uuid4()),
        first_name="Owner",
        last_name="User"
    )
    
    editor = User(
        id=editor_id,
        email="editor@example.com",
        cognito_sub=str(uuid.uuid4()),
        first_name="Editor",
        last_name="User"
    )
    
    viewer = User(
        id=viewer_id,
        email="viewer@example.com",
        cognito_sub=str(uuid.uuid4()),
        first_name="Viewer",
        last_name="User"
    )
    
    test_db.add_all([owner, editor, viewer])
    test_db.flush()
    
    # Create a group
    group_id = uuid.uuid4()
    group = Group(
        id=group_id,
        name="Test ACL Group",
        group_type_id=GroupTypeEnum.HOUSEHOLD.value,
        created_at=datetime.now(timezone.utc),
        created_by=owner_id
    )
    test_db.add(group)
    test_db.flush()
    
    # Create memberships
    owner_membership = GroupMembership(
        user_id=owner_id,
        group_id=group_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    editor_membership = GroupMembership(
        user_id=editor_id,
        group_id=group_id,
        role_id=GroupRoleEnum.EDITOR.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    viewer_membership = GroupMembership(
        user_id=viewer_id,
        group_id=group_id,
        role_id=GroupRoleEnum.VIEWER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    test_db.add_all([owner_membership, editor_membership, viewer_membership])
    
    # Create permissions for each user based on their role
    
    # Owner: Full permissions (read, write, delete)
    for action in [PermissionAction.READ, PermissionAction.WRITE, PermissionAction.DELETE]:
        for resource_type in [ResourceTypeEnum.CLAIM.value, ResourceTypeEnum.FILE.value, ResourceTypeEnum.ITEM.value]:
            permission = Permission(
                id=uuid.uuid4(),
                subject_type="user",
                subject_id=str(owner_id),
                resource_type_id=resource_type,
                resource_id=None,  # Applies to all resources of this type
                action=action,
                conditions=json.dumps({"group_id": str(group_id)}),
                group_id=group_id
            )
            test_db.add(permission)
    
    # Editor: Read and write permissions, but no delete
    for action in [PermissionAction.READ, PermissionAction.WRITE]:
        for resource_type in [ResourceTypeEnum.CLAIM.value, ResourceTypeEnum.FILE.value, ResourceTypeEnum.ITEM.value]:
            permission = Permission(
                id=uuid.uuid4(),
                subject_type="user",
                subject_id=str(editor_id),
                resource_type_id=resource_type,
                resource_id=None,  # Applies to all resources of this type
                action=action,
                conditions=json.dumps({"group_id": str(group_id)}),
                group_id=group_id
            )
            test_db.add(permission)
    
    # Viewer: Read-only permissions
    for resource_type in [ResourceTypeEnum.CLAIM.value, ResourceTypeEnum.FILE.value, ResourceTypeEnum.ITEM.value]:
        permission = Permission(
            id=uuid.uuid4(),
            subject_type="user",
            subject_id=str(viewer_id),
            resource_type_id=resource_type,
            resource_id=None,  # Applies to all resources of this type
            action=PermissionAction.READ,
            conditions=json.dumps({"group_id": str(group_id)}),
            group_id=group_id
        )
        test_db.add(permission)
    
    test_db.commit()
    
    return {
        "group": group,
        "group_id": group_id,
        "owner": owner,
        "owner_id": owner_id,
        "editor": editor,
        "editor_id": editor_id,
        "viewer": viewer,
        "viewer_id": viewer_id
    }

@pytest.fixture
def create_jwt_token():
    """
    Create a valid JWT token for testing.
    
    Returns a function that takes a user's cognito_sub and generates a valid JWT token
    that can be used in the Authorization header.
    """
    def _create_token(cognito_sub):
        import base64
        import json
        
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        payload = base64.b64encode(json.dumps({"sub": cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        
        return f"{header}.{payload}.{signature}"
    
    return _create_token

# -----------------
# API GATEWAY MOCKS
# -----------------
@pytest.fixture
def api_gateway_event():
    """Creates a mock API Gateway event for testing"""

    def _event(http_method="GET", path_params=None, query_params=None, body=None, auth_user="user-123", group_id=None):
        """Generate an API event, allowing optional auth_user=None for unauthenticated tests"""
        # If group_id is not provided, generate a random one
        if group_id is None and auth_user:
            group_id = str(uuid.uuid4())
            
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

        # Mock Attribute Updates
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
def generate_jwt_token():
    """
    Generate a valid JWT token for testing.
    
    This fixture creates a properly structured JWT token that can be used
    in tests to bypass authentication checks.
    
    Returns:
        function: A function that takes a user_id and returns a valid JWT token
    """
    def _generate_token(user_id):
        import base64
        import json
        
        # Create a simple JWT with header, payload, and signature parts
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        
        # Ensure the UUID is in the correct format (no hyphens)
        if isinstance(user_id, str) and '-' in user_id:
            # Remove hyphens from the UUID string
            user_id = user_id.replace('-', '')
        
        payload = base64.b64encode(json.dumps({"sub": str(user_id)}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        
        # Join the parts with dots to form a valid JWT structure
        return f"{header}.{payload}.{signature}"
    
    return _generate_token

@pytest.fixture
def mock_auth_utils():
    """
    Mock the auth_utils.extract_user_id function to bypass JWT validation.
    
    This fixture patches the extract_user_id function to always return success
    and the provided user ID.
    """
    with patch("utils.auth_utils.extract_user_id") as mock_extract:
        def side_effect(event):
            # Extract the user ID from the event's authorizer claims or Authorization header
            user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
            
            # If not found in claims, try to get from the auth_user in the event (for our test fixtures)
            if not user_id and "auth_user" in event:
                user_id = event["auth_user"]
                
            if user_id:
                return True, user_id
            return False, {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}
            
        mock_extract.side_effect = side_effect
        yield mock_extract

@pytest.fixture
def auth_api_gateway_event(generate_jwt_token):
    """
    Create an API Gateway event with proper JWT authentication.
    
    This fixture enhances the basic api_gateway_event fixture by adding
    a valid JWT token in the Authorization header.
    """
    def _event(http_method="GET", path_params=None, query_params=None, body=None, auth_user="user-123", group_id=None):
        # If group_id is not provided, generate a random one
        if group_id is None and auth_user:
            group_id = str(uuid.uuid4())
            
        # Generate a JWT token for the auth_user
        token = generate_jwt_token(auth_user)
        
        event = {
            "httpMethod": http_method,
            "pathParameters": path_params or {},
            "queryStringParameters": query_params or {},
            "headers": {"Authorization": f"Bearer {token}"} if auth_user else {},
            "requestContext": {
                "authorizer": {"claims": {"sub": auth_user}} if auth_user else {}
            },
            "body": json.dumps(body) if isinstance(body, dict) else body,
            "auth_user": auth_user  # Add this for our mock_auth_utils fixture
        }
        return event

    return _event

# -----------------
# TEST DATA FIXTURES
# -----------------
@pytest.fixture
def seed_file(test_db, seed_user_and_group):
    """Inserts a test file into the database."""
    user_id = seed_user_and_group["user_id"]
    group_id = seed_user_and_group["group_id"]
    file_id = uuid.uuid4()
    
    # Create a file
    file = File(
        id=file_id,
        file_name="test_file.jpg",
        s3_key=f"files/{file_id}.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        status=FileStatus.PROCESSED,
        uploaded_by=user_id,
        group_id=group_id
    )
    test_db.add(file)
    test_db.commit()
    
    return {
        "file_id": file_id,
        "file": file,
        "user_id": user_id,
        "group_id": group_id
    }

@pytest.fixture
def seed_claim(test_db, seed_user_and_group):
    """Seeds a claim and returns its ID."""
    user_id = seed_user_and_group["user_id"]
    group_id = seed_user_and_group["group_id"]
    
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        title="Test Claim",
        description="This is a test claim",
        date_of_loss=datetime.now(timezone.utc),
        group_id=group_id,
        created_by=user_id
    )
    test_db.add(claim)
    test_db.commit()
    
    return {
        "claim_id": claim_id,
        "claim": claim,
        "user_id": user_id,
        "group_id": group_id
    }

@pytest.fixture
def seed_item(test_db, seed_claim):
    """Seeds a single item under a claim."""
    claim_id = seed_claim["claim_id"]
    group_id = seed_claim["group_id"]
    
    item_id = uuid.uuid4()
    item = Item(
        id=item_id,
        name="Test Item",
        description="This is a test item",
        quantity=1,
        value=100.00,
        claim_id=claim_id,
        group_id=group_id
    )
    test_db.add(item)
    test_db.commit()
    
    return {
        "item_id": item_id,
        "item": item,
        "claim_id": claim_id,
        "group_id": group_id
    }