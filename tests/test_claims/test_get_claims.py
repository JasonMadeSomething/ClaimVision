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

def test_get_claims_success(test_db, api_gateway_event, seed_user_and_group):
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
    
    # Add specific permissions for these claims
    for claim_id in [claim1_id, claim2_id]:
        claim_permission = Permission(
            id=uuid.uuid4(),
            subject_type="user",
            subject_id=user.id,
            resource_type_id=ResourceTypeEnum.CLAIM.value,
            resource_id=claim_id,
            action=PermissionAction.READ,
            conditions=json.dumps({"group_id": str(group_id)}),
            group_id=group_id
        )
        test_db.add(claim_permission)
    
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
    assert len(body["data"]) == 2
    claim_titles = [claim["title"] for claim in body["data"]]
    assert "Claim 1" in claim_titles
    assert "Claim 2" in claim_titles


def test_get_claims_empty(test_db, api_gateway_event, seed_user_and_group):
    """Test retrieving claims when the user has none"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]

    # Create a valid JWT token with the correct format
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"

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
    assert len(body["data"]) == 0


def test_get_claims_unauthorized(test_db, api_gateway_event):
    """Test retrieving claims with an unauthorized user"""
    # Create two users first
    authorized_user_id = uuid.uuid4()
    unauthorized_user_id = uuid.uuid4()
    authorized_cognito_sub = str(uuid.uuid4())
    unauthorized_cognito_sub = str(uuid.uuid4())

    authorized_user = User(
        id=authorized_user_id,
        email="authorized@example.com",
        first_name="Authorized",
        last_name="User",
        cognito_sub=authorized_cognito_sub
    )

    unauthorized_user = User(
        id=unauthorized_user_id,
        email="unauthorized@example.com",
        first_name="Unauthorized",
        last_name="User",
        cognito_sub=unauthorized_cognito_sub
    )

    test_db.add_all([authorized_user, unauthorized_user])
    test_db.commit()

    # Now create two separate groups with valid created_by values
    authorized_group_id = uuid.uuid4()
    unauthorized_group_id = uuid.uuid4()

    authorized_group = Group(
        id=authorized_group_id, 
        name="Authorized Group",
        group_type_id=GroupTypeEnum.HOUSEHOLD.value,
        created_at=datetime.now(timezone.utc),
        created_by=authorized_user_id
    )
    unauthorized_group = Group(
        id=unauthorized_group_id, 
        name="Unauthorized Group",
        group_type_id=GroupTypeEnum.HOUSEHOLD.value,
        created_at=datetime.now(timezone.utc),
        created_by=unauthorized_user_id
    )
    
    test_db.add_all([authorized_group, unauthorized_group])
    test_db.commit()
    
    # Create memberships
    auth_membership = GroupMembership(
        user_id=authorized_user_id,
        group_id=authorized_group_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    unauth_membership = GroupMembership(
        user_id=unauthorized_user_id,
        group_id=unauthorized_group_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    test_db.add_all([auth_membership, unauth_membership])
    test_db.commit()

    # Create claims in the authorized group
    claim1 = Claim(
        id=uuid.uuid4(), 
        group_id=authorized_group_id, 
        title="Auth Claim 1", 
        date_of_loss=datetime(2024, 1, 10),
        created_by=authorized_user_id
    )
    
    test_db.add(claim1)
    test_db.commit()
    
    # Create a valid JWT token for the unauthorized user
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    payload = base64.b64encode(json.dumps({"sub": unauthorized_cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"

    # The unauthorized user tries to access claims
    event = api_gateway_event(
        http_method="GET", 
        auth_user=unauthorized_cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    # The user should get a 200 response but with an empty list of claims
    # since they don't have access to the authorized group's claims
    assert response["statusCode"] == 200
    assert len(body["data"]) == 0


@pytest.mark.skip(reason="This test requires mocking the database session")
def test_get_claims_db_failure(api_gateway_event, seed_user_and_group):
    """Test handling a database connection failure"""
    # Get the user from the fixture
    user = seed_user_and_group["user"]

    # Create a valid JWT token
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"

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