import json
import pytest
import base64
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from claims.get_claims import lambda_handler
from models.claim import Claim
from models.group import Group
from models.user import User
from models.group_membership import GroupMembership
from models.permissions import Permission
from utils.vocab_enums import GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum, GroupTypeEnum, ResourceTypeEnum, PermissionAction
from sqlalchemy.exc import SQLAlchemyError

def test_get_claims_success(test_db, api_gateway_event, seed_user_and_group, create_resource_permission):
    """Test retrieving claims successfully for a user's group"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]

    # Create a valid JWT token with the correct format
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    # Use the exact cognito_sub value
    payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"

    # Create test claims with the valid group_id
    claim1_id = uuid.uuid4()
    claim2_id = uuid.uuid4()
    
    claim1 = Claim(
        id=claim1_id, 
        group_id=group_id, 
        title="Claim 1", 
        date_of_loss=datetime(2024, 1, 10),
        created_by=user.id
    )
    claim2 = Claim(
        id=claim2_id, 
        group_id=group_id, 
        title="Claim 2", 
        date_of_loss=datetime(2024, 1, 11),
        created_by=user.id
    )
    
    test_db.add_all([claim1, claim2])
    test_db.flush()
    
    # Add specific permissions for these claims using the create_resource_permission fixture
    for claim_id in [claim1_id, claim2_id]:
        create_resource_permission(
            user_id=user.id,
            resource_type=ResourceTypeEnum.CLAIM.value,
            resource_id=claim_id,
            action=PermissionAction.READ,
            group_id=group_id
        )
    
    test_db.commit()

    # Create the event with proper authentication
    event = api_gateway_event(
        http_method="GET",
        auth_user=user.cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["results"]) == 2
    claim_titles = [claim["title"] for claim in body["data"]["results"]]
    assert "Claim 1" in claim_titles
    assert "Claim 2" in claim_titles


def test_get_claims_empty(test_db, api_gateway_event, seed_user_and_group, create_jwt_token):
    """Test retrieving claims when the user has none"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    
    # Create a valid JWT token using the fixture
    valid_token = create_jwt_token(user.cognito_sub)

    # Create the event with proper authentication
    event = api_gateway_event(
        http_method="GET",
        auth_user=user.cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert len(body["data"]["results"]) == 0


def test_get_claims_unauthorized(test_db, api_gateway_event, seed_multiple_users_and_groups, create_jwt_token, create_resource_permission):
    """Test retrieving claims with an unauthorized user"""
    # Get users from the fixture
    owner = seed_multiple_users_and_groups["owner"]
    viewer = seed_multiple_users_and_groups["viewer"]
    group_id = seed_multiple_users_and_groups["group_id"]
    
    # Create a claim that only the owner can access
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        group_id=group_id,
        title="Owner Only Claim",
        date_of_loss=datetime(2024, 1, 10),
        created_by=owner.id
    )
    
    test_db.add(claim)
    test_db.flush()
    
    # Add specific permission only for the owner
    create_resource_permission(
        user_id=owner.id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.READ,
        group_id=group_id
    )
    
    # Create a valid JWT token for the viewer
    viewer_token = create_jwt_token(viewer.cognito_sub)
    
    # The viewer tries to access claims
    event = api_gateway_event(
        http_method="GET",
        auth_user=viewer.cognito_sub
    )
    
    # Replace the placeholder token with the viewer's token
    event["headers"]["Authorization"] = f"Bearer {viewer_token}"
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    # The viewer should get a 200 response but with an empty list of claims
    # since they don't have access to the owner's claim
    assert response["statusCode"] == 200
    assert len(body["data"]["results"]) == 0


@pytest.mark.skip(reason="This test requires mocking the database session")
def test_get_claims_db_failure(api_gateway_event, seed_user_and_group, create_jwt_token):
    """Test handling a database connection failure"""
    # Get the user from the fixture
    user = seed_user_and_group["user"]

    # Create a valid JWT token
    valid_token = create_jwt_token(user.cognito_sub)

    # Create the event with proper authentication
    event = api_gateway_event(
        http_method="GET",
        auth_user=user.cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    # Mock the database session to raise an exception
    with patch('claims.get_claims.db_session.query', side_effect=SQLAlchemyError("Test DB Error")):
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 500
        assert "database error" in body["error_details"].lower()