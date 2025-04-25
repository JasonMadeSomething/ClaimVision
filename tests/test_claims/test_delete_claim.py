import json
import uuid
import pytest
import base64
from unittest.mock import patch, MagicMock
from claims.delete_claim import lambda_handler
from models.claim import Claim
from models.group import Group
from models.user import User
from models.group_membership import GroupMembership
from models.permissions import Permission
from utils.vocab_enums import GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum, GroupTypeEnum, ResourceTypeEnum, PermissionAction
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

def test_delete_claim_success(test_db, api_gateway_event, seed_user_and_group):
    """ Test successful claim deletion"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a valid JWT token with the correct format
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    # Use the exact cognito_sub value
    payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"
    
    # Create a claim in the group
    claim_id = uuid.uuid4()
    test_claim = Claim(
        id=claim_id, 
        group_id=group_id, 
        title="Valid Claim", 
        date_of_loss=datetime(2024, 1, 10),
        created_by=user.id
    )
    
    test_db.add(test_claim)
    test_db.flush()
    
    # Add specific permission for this claim
    claim_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=user.id,
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,  # Specific claim ID
        action=PermissionAction.DELETE,
        conditions=json.dumps({"group_id": str(group_id)}),
        group_id=group_id
    )
    test_db.add(claim_permission)
    test_db.commit()

    event = api_gateway_event(
        http_method="DELETE", 
        path_params={"claim_id": str(claim_id)}, 
        auth_user=user.cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "Claim deleted successfully" in body["message"]

def test_delete_claim_unauthorized(test_db, api_gateway_event):
    """ Test deleting a claim that belongs to another user"""
    # Create two users first
    authorized_user_id = uuid.uuid4()
    unauthorized_user_id = uuid.uuid4()
    authorized_cognito_sub = str(uuid.uuid4())  # Use a proper UUID format without prefix
    unauthorized_cognito_sub = str(uuid.uuid4())  # Use a proper UUID format without prefix

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

    # Now create a claim in the authorized group
    claim_id = uuid.uuid4()
    test_claim = Claim(
        id=claim_id, 
        group_id=authorized_group_id, 
        title="Valid Claim", 
        date_of_loss=datetime(2024, 1, 10),
        created_by=authorized_user_id
    )

    test_db.add(test_claim)
    
    # Add specific permission for this claim for the authorized user
    claim_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=authorized_user_id,
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.DELETE,
        conditions=json.dumps({"group_id": str(authorized_group_id)}),
        group_id=authorized_group_id
    )
    test_db.add(claim_permission)
    test_db.commit()

    # Create a valid JWT token with the correct format for the unauthorized user
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    # Use the exact cognito_sub value
    payload = base64.b64encode(json.dumps({"sub": unauthorized_cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"

    # The unauthorized user tries to delete the claim
    event = api_gateway_event(
        http_method="DELETE", 
        path_params={"claim_id": str(claim_id)}, 
        auth_user=unauthorized_cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 403  # Access denied
    assert "access" in body["error_details"].lower()

def test_delete_claim_not_found(test_db, api_gateway_event, seed_user_and_group):
    """ Test deleting a non-existent claim"""
    # Get the user from the fixture
    user = seed_user_and_group["user"]
    
    # Create a valid JWT token with the correct format
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    # Use the exact cognito_sub value
    payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"

    # Attempt to delete a claim that doesn't exist
    event = api_gateway_event(
        http_method="DELETE", 
        path_params={"claim_id": str(uuid.uuid4())}, 
        auth_user=user.cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert "Claim not found" in body["error_details"]

def test_delete_claim_invalid_id(test_db, api_gateway_event, seed_user_and_group):
    """ Test deleting a claim with an invalid UUID"""
    # Get the user from the fixture
    user = seed_user_and_group["user"]
    
    # Create a valid JWT token with the correct format
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    # Use the exact cognito_sub value
    payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"
    
    # Use a completely invalid format for claim_id that will trigger the 400 error
    event = api_gateway_event(
        http_method="DELETE", 
        path_params={"claim_id": "abc"}, 
        auth_user=user.cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    # Call the lambda handler directly with the invalid UUID
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    # The extract_uuid_param function should return a 400 status code for invalid UUIDs
    assert response["statusCode"] == 400
    assert "Invalid claim_id format" in body["error_details"]

def test_delete_claim_db_failure(test_db, api_gateway_event, seed_user_and_group):
    """ Test handling a database failure during claim deletion"""
    # Get the user from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a valid JWT token with the correct format
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    # Use the exact cognito_sub value
    payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    valid_token = f"{header}.{payload}.{signature}"
    
    # Create a claim in the group
    claim_id = uuid.uuid4()
    test_claim = Claim(
        id=claim_id, 
        group_id=group_id, 
        title="Valid Claim", 
        date_of_loss=datetime(2024, 1, 10),
        created_by=user.id
    )
    
    test_db.add(test_claim)
    test_db.flush()
    
    # Add specific permission for this claim
    claim_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=user.id,
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,  # Specific claim ID
        action=PermissionAction.DELETE,
        conditions=json.dumps({"group_id": str(group_id)}),
        group_id=group_id
    )
    test_db.add(claim_permission)
    test_db.commit()
    
    # Create the event first
    event = api_gateway_event(
        http_method="DELETE", 
        path_params={"claim_id": str(claim_id)}, 
        auth_user=user.cognito_sub
    )
    
    # Replace the placeholder token with a valid JWT token
    event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
    # Use a different approach - patch the commit method directly
    with patch.object(test_db, 'commit') as mock_commit:
        mock_commit.side_effect = SQLAlchemyError("Database error during commit")
        
        # Call the lambda handler with the test_db that has the patched commit method
        response = lambda_handler(event, {}, db_session=test_db, user=user)
        body = json.loads(response["body"])
    
    assert response["statusCode"] == 500
    assert "Failed to delete claim" in body["error_details"]