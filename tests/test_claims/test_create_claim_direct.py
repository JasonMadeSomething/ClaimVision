import json
import pytest
import base64
from unittest.mock import patch, MagicMock

from models.claim import Claim
from models.permissions import PermissionAction

# Import the lambda_handler function directly
from claims.create_claim import lambda_handler

def create_mock_jwt(user_id):
    """Create a mock JWT token with the correct structure."""
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

@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    mock_session = MagicMock()
    
    # Mock the query method to return a mock query object
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    
    # Mock the filter and first methods
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None  # Default to no results
    
    return mock_session

def test_create_claim_direct(mock_db_session, seed_user_and_group):
    """Test claim creation directly without going through the decorator."""
    # Get test data from the seed_user_and_group fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a mock JWT token
    mock_token = create_mock_jwt(user.cognito_sub)
    
    # Create a mock event with the necessary data and Authorization header
    event = {
        "body": json.dumps({
            "title": "Test Claim",
            "date_of_loss": "2024-01-10",
            "group_id": str(group_id)
        }),
        "headers": {
            "Authorization": f"Bearer {mock_token}"
        }
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Patch the auth_utils.get_authenticated_user function to return success and the user
    with patch("utils.auth_utils.get_authenticated_user") as mock_get_user:
        mock_get_user.return_value = (True, user)
        
        # Mock the has_permission function to return True
        with patch("claims.create_claim.has_permission") as mock_has_permission:
            mock_has_permission.return_value = True
            
            # Call the lambda handler directly with our mocked session
            response = lambda_handler(event, {}, db_session=mock_db_session)
            
            # Check the response
            assert response["statusCode"] == 201, f"Expected 201, got {response['statusCode']}: {response['body']}"
            
            # Verify that a claim was created
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            
            # Get the claim that was created
            claim_arg = mock_db_session.add.call_args[0][0]
            assert isinstance(claim_arg, Claim)
            assert claim_arg.title == "Test Claim"
            assert claim_arg.group_id == group_id
            
            # Verify that has_permission was called with the correct action
            mock_has_permission.assert_called_with(
                user, 
                action=PermissionAction.WRITE.value, 
                resource_type="claim", 
                group_id=group_id, 
                db=mock_db_session
            )

def test_create_claim_missing_fields_direct(mock_db_session, seed_user_and_group):
    """Test claim creation with missing fields."""
    user = seed_user_and_group["user"]
    
    # Create a mock JWT token
    mock_token = create_mock_jwt(user.cognito_sub)
    
    # Create a mock event with missing date_of_loss and Authorization header
    event = {
        "body": json.dumps({
            "title": "Test Claim"
            # Missing date_of_loss
        }),
        "headers": {
            "Authorization": f"Bearer {mock_token}"
        }
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Patch the auth_utils.get_authenticated_user function
    with patch("utils.auth_utils.get_authenticated_user") as mock_get_user:
        mock_get_user.return_value = (True, user)
        
        # Call the lambda handler directly
        response = lambda_handler(event, {}, db_session=mock_db_session)
        
        # Check the response
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error_details" in body
        assert "date_of_loss" in body["error_details"]
        
        # Verify that no claim was created
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

def test_create_claim_invalid_date_format_direct(mock_db_session, seed_user_and_group):
    """Test claim creation with invalid date format."""
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a mock JWT token
    mock_token = create_mock_jwt(user.cognito_sub)
    
    # Create a mock event with invalid date format and Authorization header
    event = {
        "body": json.dumps({
            "title": "Test Claim",
            "date_of_loss": "01/10/2024",  # Wrong format, should be YYYY-MM-DD
            "group_id": str(group_id)
        }),
        "headers": {
            "Authorization": f"Bearer {mock_token}"
        }
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Patch the auth_utils.get_authenticated_user function
    with patch("utils.auth_utils.get_authenticated_user") as mock_get_user:
        mock_get_user.return_value = (True, user)
        
        # Call the lambda handler directly
        response = lambda_handler(event, {}, db_session=mock_db_session)
        
        # Check the response
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error_details" in body
        assert "date format" in body["error_details"]
        
        # Verify that no claim was created
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

def test_create_claim_no_permission_direct(mock_db_session, seed_user_and_group):
    """Test claim creation when the user doesn't have permission."""
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a mock JWT token
    mock_token = create_mock_jwt(user.cognito_sub)
    
    # Create a mock event with Authorization header
    event = {
        "body": json.dumps({
            "title": "Test Claim",
            "date_of_loss": "2024-01-10",
            "group_id": str(group_id)
        }),
        "headers": {
            "Authorization": f"Bearer {mock_token}"
        }
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Patch the auth_utils.get_authenticated_user function
    with patch("utils.auth_utils.get_authenticated_user") as mock_get_user:
        mock_get_user.return_value = (True, user)
        
        # Mock the has_permission function to return False
        with patch("claims.create_claim.has_permission") as mock_has_permission:
            mock_has_permission.return_value = False
            
            # Call the lambda handler directly
            response = lambda_handler(event, {}, db_session=mock_db_session)
            
            # Check the response
            assert response["statusCode"] == 403
            body = json.loads(response["body"])
            assert "error_details" in body
            assert "permission" in body["error_details"].lower()
            
            # Verify that no claim was created
            mock_db_session.add.assert_not_called()
            mock_db_session.commit.assert_not_called()
            
            # Verify that has_permission was called with the correct action
            mock_has_permission.assert_called_with(
                user, 
                action=PermissionAction.WRITE.value, 
                resource_type="claim", 
                group_id=group_id, 
                db=mock_db_session
            )
