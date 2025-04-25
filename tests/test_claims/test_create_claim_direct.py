import json
import pytest
import base64
from unittest.mock import patch, MagicMock

from models.claim import Claim
from models.permissions import PermissionAction

# Import the lambda_handler function directly
from claims.create_claim import lambda_handler

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

def test_create_claim_direct(mock_db_session, seed_user_and_group, create_jwt_token):
    """Test claim creation directly without going through the decorator."""
    # Get test data from the seed_user_and_group fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a mock JWT token using the fixture
    mock_token = create_jwt_token(user.cognito_sub)
    
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
            
            # Create mock resource types
            mock_claim_type = MagicMock()
            mock_claim_type.id = "claim"
            
            mock_file_type = MagicMock()
            mock_file_type.id = "file"
            
            mock_item_type = MagicMock()
            mock_item_type.id = "item"
            
            # Set up resource types dictionary
            resource_types_dict = {
                "claim": mock_claim_type,
                "file": mock_file_type,
                "item": mock_item_type
            }
            
            # Mock the db_session.query for ResourceType
            def mock_query_side_effect(*args):
                if args and args[0].__name__ == "ResourceType":
                    mock_query = MagicMock()
                    mock_filter = MagicMock()
                    mock_query.filter.return_value = mock_filter
                    mock_filter.all.return_value = [mock_claim_type, mock_file_type, mock_item_type]
                    return mock_query
                return mock_db_session.query.return_value
            
            mock_db_session.query.side_effect = mock_query_side_effect
            
            # Call the lambda handler directly with our mocked session
            response = lambda_handler(event, {}, db_session=mock_db_session)
            
            # Check the response
            assert response["statusCode"] == 201, f"Expected 201, got {response['statusCode']}: {response['body']}"
            
            # Verify that a claim was created
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called()
            
            # Get the claim that was created
            claim_arg = None
            for call in mock_db_session.add.call_args_list:
                arg = call[0][0]
                if isinstance(arg, Claim):
                    claim_arg = arg
                    break
                    
            assert claim_arg is not None
            assert claim_arg.title == "Test Claim"
            assert claim_arg.group_id == group_id
            
            # Verify that has_permission was called with the correct action
            mock_has_permission.assert_called_with(
                user, 
                action=PermissionAction.WRITE, 
                resource_type="claim", 
                group_id=group_id, 
                db=mock_db_session
            )

def test_create_claim_missing_fields_direct(mock_db_session, seed_user_and_group, create_jwt_token):
    """Test claim creation with missing fields."""
    user = seed_user_and_group["user"]
    
    # Create a mock JWT token using the fixture
    mock_token = create_jwt_token(user.cognito_sub)
    
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
        assert "missing_fields" in body["data"]
        assert "date_of_loss" in body["data"]["missing_fields"]
        
        # Verify that no claim was created
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

def test_create_claim_invalid_date_format_direct(mock_db_session, seed_user_and_group, create_jwt_token):
    """Test claim creation with invalid date format."""
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a mock JWT token using the fixture
    mock_token = create_jwt_token(user.cognito_sub)
    
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

def test_create_claim_no_permission_direct(mock_db_session, seed_user_and_group, create_jwt_token):
    """Test claim creation when the user doesn't have permission."""
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a mock JWT token using the fixture
    mock_token = create_jwt_token(user.cognito_sub)
    
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
                action=PermissionAction.WRITE, 
                resource_type="claim", 
                group_id=group_id, 
                db=mock_db_session
            )
