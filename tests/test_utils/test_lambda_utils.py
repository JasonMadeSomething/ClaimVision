import json
import pytest
import uuid
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from utils import response
from models import User

# Test fixtures and helper functions
@pytest.fixture
def mock_event():
    """Create a mock API Gateway event."""
    return {
        "pathParameters": {"id": str(uuid.uuid4())},
        "body": json.dumps({"test_field": "test_value"}),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": str(uuid.uuid4())
                }
            }
        }
    }

@pytest.fixture
def mock_context():
    """Create a mock Lambda context."""
    return {}

@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    return MagicMock()

@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()
    return User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id
    )

# Test handler functions with different configurations
def handler_no_auth(event, context, db_session=None, **kwargs):
    """Test handler that doesn't require authentication."""
    return response.api_response(200, message="Success", data={"auth_required": False})

def handler_with_auth(event, context, db_session=None, user=None, **kwargs):
    """Test handler that requires authentication."""
    return response.api_response(200, message="Success", data={"user_id": str(user.id) if user else "no_user"})

def handler_with_body(event, context, db_session=None, user=None, body=None, **kwargs):
    """Test handler that requires a request body."""
    return response.api_response(200, message="Success", data=body)

def handler_with_required_fields(event, context, db_session=None, user=None, body=None, **kwargs):
    """Test handler that requires specific fields in the request body."""
    return response.api_response(200, message="Success", data=body)

def handler_minimal_params(event, **kwargs):
    """Test handler that only uses minimal parameters."""
    return response.api_response(200, message="Success", data={"minimal": True})

def handler_raises_error(**kwargs):
    """Test handler that raises an unexpected error."""
    raise ValueError("Test error")

# Actual test cases
class TestStandardLambdaHandler:
    """Test cases for the standard_lambda_handler decorator."""

    def test_no_auth_required(self, mock_event, mock_context):
        """Test a handler that doesn't require authentication."""
        decorated_handler = standard_lambda_handler(requires_auth=False)(handler_no_auth)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["data"]["auth_required"] is False

    @patch("utils.auth_utils.extract_user_id")
    @patch("utils.auth_utils.get_authenticated_user")
    def test_auth_required_success(self, mock_get_user, mock_extract_id, mock_event, mock_context, mock_user):
        """Test a handler that requires authentication - success case."""
        # Mock successful authentication
        mock_extract_id.return_value = (True, str(mock_user.id))
        mock_get_user.return_value = (True, mock_user)
        
        decorated_handler = standard_lambda_handler(requires_auth=True)(handler_with_auth)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["data"]["user_id"] == str(mock_user.id)

    @patch("utils.auth_utils.extract_user_id")
    def test_auth_required_missing_token(self, mock_extract_id, mock_event, mock_context):
        """Test a handler that requires authentication but no token is provided."""
        # Mock failed token extraction
        mock_extract_id.return_value = (False, "Missing token")
        
        decorated_handler = standard_lambda_handler(requires_auth=True)(handler_with_auth)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 401
        body = json.loads(result["body"])
        assert "Unauthorized" in body["message"]

    @patch("utils.auth_utils.extract_user_id")
    @patch("utils.auth_utils.get_authenticated_user")
    def test_auth_required_invalid_user(self, mock_get_user, mock_extract_id, mock_event, mock_context):
        """Test a handler that requires authentication but user is not found."""
        # Mock successful token extraction but failed user lookup
        mock_extract_id.return_value = (True, str(uuid.uuid4()))
        mock_get_user.return_value = (False, response.api_response(401, error_details="User not found"))
        
        decorated_handler = standard_lambda_handler(requires_auth=True)(handler_with_auth)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 401
        body = json.loads(result["body"])
        assert "User not found" in body["error_details"]

    def test_body_required_success(self, mock_event, mock_context):
        """Test a handler that requires a request body - success case."""
        decorated_handler = standard_lambda_handler(requires_auth=False, requires_body=True)(handler_with_body)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["data"]["test_field"] == "test_value"

    def test_body_required_invalid_json(self, mock_event, mock_context):
        """Test a handler that requires a request body but invalid JSON is provided."""
        # Corrupt the JSON in the event body
        mock_event["body"] = "{"  # Invalid JSON
        
        decorated_handler = standard_lambda_handler(requires_auth=False, requires_body=True)(handler_with_body)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid JSON" in body["error_details"]

    def test_required_fields_success(self, mock_event, mock_context):
        """Test a handler that requires specific fields in the request body - success case."""
        decorated_handler = standard_lambda_handler(
            requires_auth=False, 
            requires_body=True,
            required_fields=["test_field"]
        )(handler_with_required_fields)
        
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["data"]["test_field"] == "test_value"

    def test_required_fields_missing(self, mock_event, mock_context):
        """Test a handler that requires specific fields but they are missing from the request body."""
        # Set body with missing required field
        mock_event["body"] = json.dumps({"other_field": "other_value"})
    
        decorated_handler = standard_lambda_handler(
            requires_auth=False,
            requires_body=True,
            required_fields=["test_field"]
        )(handler_with_required_fields)
    
        result = decorated_handler(mock_event, mock_context)
    
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error_details" in body
        assert "Missing required fields" in body["error_details"]
        assert "missing_fields" in body["data"]
        assert "test_field" in body["data"]["missing_fields"]

    @patch("utils.lambda_utils.get_db_session")
    def test_database_session_creation(self, mock_get_db, mock_event, mock_context):
        """Test that a database session is created if none is provided."""
        # Mock the database session
        mock_session = MagicMock()
        mock_get_db.return_value = mock_session
        
        # Ensure we don't pass a db_session to force creation of a new one
        decorated_handler = standard_lambda_handler(requires_auth=False)(handler_no_auth)
        
        # Call without providing a db_session
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 200
        # Verify that the session was created and closed
        mock_get_db.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("utils.lambda_utils.get_db_session")
    def test_database_error(self, mock_get_db, mock_event, mock_context):
        """Test handling of database connection errors."""
        # Mock a database error
        mock_get_db.side_effect = SQLAlchemyError("Database connection error")
        
        decorated_handler = standard_lambda_handler(requires_auth=False)(handler_no_auth)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 500
        assert "Failed to establish database connection" in json.loads(result["body"])["error_details"]

    def test_unexpected_error(self, mock_event, mock_context):
        """Test handling of unexpected errors in the handler function."""
        decorated_handler = standard_lambda_handler(requires_auth=False)(handler_raises_error)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "Internal Server Error" in body["message"]
        assert "Test error" in body["error_details"]

    def test_parameter_inspection(self, mock_event, mock_context):
        """Test that the decorator correctly inspects and passes only the parameters the handler accepts."""
        decorated_handler = standard_lambda_handler(requires_auth=False)(handler_minimal_params)
        result = decorated_handler(mock_event, mock_context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["data"]["minimal"] is True


class TestExtractUuidParam:
    """Test cases for the extract_uuid_param function."""

    def test_valid_uuid(self, mock_event):
        """Test extracting a valid UUID parameter."""
        uuid_str = mock_event["pathParameters"]["id"]
        success, result = extract_uuid_param(mock_event, "id")
        
        assert success is True
        assert result == uuid_str

    def test_missing_path_params(self):
        """Test handling of missing path parameters."""
        event = {}  # No pathParameters
        success, result = extract_uuid_param(event, "id")
        
        assert success is False
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required path parameter" in body["error_details"]

    def test_missing_param(self):
        """Test handling of a missing specific parameter."""
        event = {"pathParameters": {}}  # Empty pathParameters
        success, result = extract_uuid_param(event, "id")
        
        assert success is False
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required path parameter" in body["error_details"]

    def test_invalid_uuid(self):
        """Test handling of an invalid UUID format."""
        event = {"pathParameters": {"id": "not-a-uuid"}}
        success, result = extract_uuid_param(event, "id")
        
        assert success is False
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid" in body["error_details"]
