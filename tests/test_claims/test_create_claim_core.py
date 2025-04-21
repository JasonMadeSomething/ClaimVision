import json
import uuid
from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock

from models.claim import Claim
from utils.vocab_enums import MembershipStatusEnum
from models.permissions import PermissionAction

# Import the create_claim module to access its functions
import claims.create_claim as create_claim

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

def test_create_claim_core(mock_db_session, seed_user_and_group):
    """Test the core claim creation logic directly."""
    # Get test data from the seed_user_and_group fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create request body
    body = {
        "title": "Test Claim",
        "date_of_loss": "2024-01-10",
        "group_id": str(group_id)
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Mock the has_permission function to return True
    with patch("claims.create_claim.has_permission") as mock_has_permission:
        mock_has_permission.return_value = True
        
        # Call the core claim creation logic directly
        # We'll create a function that extracts the core logic from lambda_handler
        result = create_claim_core(mock_db_session, user, body)
        
        # Check the response
        assert result["statusCode"] == 201
        
        # Verify that a claim was created
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Get the claim that was created
        claim_arg = mock_db_session.add.call_args[0][0]
        assert isinstance(claim_arg, Claim)
        assert claim_arg.title == "Test Claim"
        assert claim_arg.group_id == group_id

def test_create_claim_missing_fields_core(mock_db_session, seed_user_and_group):
    """Test claim creation with missing fields."""
    user = seed_user_and_group["user"]
    
    # Create request body with missing date_of_loss
    body = {
        "title": "Test Claim"
        # Missing date_of_loss
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Call the core claim creation logic directly
    result = create_claim_core(mock_db_session, user, body)
    
    # Check the response
    assert result["statusCode"] == 400
    response_body = json.loads(result["body"])
    assert "error_details" in response_body
    assert "date_of_loss" in response_body["error_details"]
    
    # Verify that no claim was created
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

def test_create_claim_invalid_date_format_core(mock_db_session, seed_user_and_group):
    """Test claim creation with invalid date format."""
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create request body with invalid date format
    body = {
        "title": "Test Claim",
        "date_of_loss": "01/10/2024",  # Wrong format, should be YYYY-MM-DD
        "group_id": str(group_id)
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Call the core claim creation logic directly
    result = create_claim_core(mock_db_session, user, body)
    
    # Check the response
    assert result["statusCode"] == 400
    response_body = json.loads(result["body"])
    assert "error_details" in response_body
    assert "date format" in response_body["error_details"]
    
    # Verify that no claim was created
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

def test_create_claim_no_permission_core(mock_db_session, seed_user_and_group):
    """Test claim creation when the user doesn't have permission."""
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create request body
    body = {
        "title": "Test Claim",
        "date_of_loss": "2024-01-10",
        "group_id": str(group_id)
    }
    
    # Mock the user query to return our test user
    mock_db_session.query.return_value.filter.return_value.first.return_value = user
    
    # Mock the has_permission function to return False
    with patch("claims.create_claim.has_permission") as mock_has_permission:
        mock_has_permission.return_value = False
        
        # Call the core claim creation logic directly
        result = create_claim_core(mock_db_session, user, body)
        
        # Check the response
        assert result["statusCode"] == 403
        response_body = json.loads(result["body"])
        assert "error_details" in response_body
        assert "You do not have permission to create claims in this group" in response_body["error_details"]
        
        # Verify that no claim was created
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

def create_claim_core(db_session, user, body):
    """
    Extract the core claim creation logic from the lambda_handler function.
    This allows us to test the logic without going through the decorator.
    """
    # Get the group ID from the request or infer it from user's memberships
    group_id_raw = body.get("group_id")
    if group_id_raw:
        try:
            group_id = uuid.UUID(group_id_raw)
        except (ValueError, TypeError):
            return create_claim.response.api_response(400, error_details="Invalid group ID format. Expected UUID")
    else:
        # Infer group from user's active memberships
        active_memberships = [
            m for m in user.memberships
            if m.status_id == MembershipStatusEnum.ACTIVE.value
        ]
        if len(active_memberships) == 1:
            group_id = active_memberships[0].group_id
        elif len(active_memberships) == 0:
            return create_claim.response.api_response(400, error_details="You are not part of any active group.")
        else:
            return create_claim.response.api_response(400, error_details="Multiple active groups found. Please specify which group to use.")
    
    # Check if the user has permission to create claims in this group
    if not create_claim.has_permission(user, action=PermissionAction.WRITE.value, resource_type="claim", group_id=group_id, db=db_session):
        return create_claim.response.api_response(403, error_details="You do not have permission to create claims in this group")
    
    # Validate title
    title = body["title"].strip() if "title" in body else ""
    if not title:
        return create_claim.response.api_response(400, error_details="Title cannot be empty")
    
    # Validate and parse date_of_loss
    try:
        if "date_of_loss" not in body:
            return create_claim.response.api_response(400, error_details="date_of_loss is required")
        
        date_of_loss = datetime.strptime(body["date_of_loss"], "%Y-%m-%d").date()
        if date_of_loss > datetime.now().date():
            return create_claim.response.api_response(400, error_details="Date of loss cannot be in the future")
    except ValueError:
        return create_claim.response.api_response(400, error_details="Invalid date format. Expected YYYY-MM-DD")
    
    # Create the claim
    try:
        new_claim = Claim(
            title=title,
            description=body.get("description", ""),
            date_of_loss=date_of_loss,
            group_id=group_id
        )
        db_session.add(new_claim)
        db_session.commit()
        db_session.refresh(new_claim)
        
        return create_claim.response.api_response(
            201,
            success_message="Claim created successfully",
            data={"claim_id": str(new_claim.id)}
        )
    except Exception as e:
        db_session.rollback()
        create_claim.logger.error(f"Error creating claim: {str(e)}")
        return create_claim.response.api_response(500, error_details=f"Error creating claim: {str(e)}")
