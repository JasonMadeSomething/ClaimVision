import json
import uuid
import pytest
from datetime import datetime, timezone
import base64

from models.claim import Claim
from models.user import User
from models.group import Group
from models.group_membership import GroupMembership
from models.permissions import Permission
from utils.vocab_enums import GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum, GroupTypeEnum, ResourceTypeEnum, PermissionAction
from claims.create_claim import lambda_handler as create_claim_handler
from claims.update_claim import lambda_handler as update_claim_handler
from claims.delete_claim import lambda_handler as delete_claim_handler

# Add debug print to verify imports
print(f"Update handler: {update_claim_handler}")
print(f"Delete handler: {delete_claim_handler}")

@pytest.fixture
def setup_user_and_group(test_db):
    """Create a user and group for testing claim creator permissions"""
    # Create user
    user_id = uuid.uuid4()
    cognito_sub = str(uuid.uuid4())
    
    user = User(
        id=user_id,
        email="creator@example.com",
        cognito_sub=cognito_sub,
        first_name="Claim",
        last_name="Creator"
    )
    
    test_db.add(user)
    test_db.flush()
    
    # Create group
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
    
    # Create membership
    membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    test_db.add(membership)
    
    # Add permission for the user to create claims in the group
    claim_create_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=user_id,
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=None,  # No specific resource ID for creation permission
        action=PermissionAction.WRITE,
        conditions=json.dumps({"group_id": str(group_id)}),
        group_id=group_id
    )
    test_db.add(claim_create_permission)
    test_db.commit()
    
    return {
        "user": user,
        "user_id": user_id,
        "cognito_sub": cognito_sub,
        "group_id": group_id
    }

def create_jwt_token(cognito_sub):
    """Create a simple JWT token for testing"""
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
    payload = base64.b64encode(json.dumps({"sub": cognito_sub}).encode()).decode()
    signature = base64.b64encode(b"").decode()
    return f"{header}.{payload}.{signature}"

def test_claim_creator_has_update_permission(test_db, api_gateway_event, setup_user_and_group):
    """Test that a claim creator can update their own claim without explicit permission grants"""
    # Get test data
    user = setup_user_and_group["user"]
    group_id = setup_user_and_group["group_id"]
    cognito_sub = setup_user_and_group["cognito_sub"]
    
    print(f"\nTEST UPDATE: User ID: {user.id}, Cognito Sub: {cognito_sub}, Group ID: {group_id}")
    
    # Create JWT token
    token = create_jwt_token(cognito_sub)
    
    # Step 1: Create a claim
    create_event = api_gateway_event(
        http_method="POST",
        body=json.dumps({
            "title": "Test Claim",
            "description": "This is a test claim",
            "date_of_loss": "2024-01-15",
            "group_id": str(group_id)
        }),
        auth_user=cognito_sub
    )
    create_event["headers"]["Authorization"] = f"Bearer {token}"
    
    create_response = create_claim_handler(create_event, {})
    assert create_response["statusCode"] == 201
    
    create_body = json.loads(create_response["body"])
    claim_id = create_body["data"]["id"]
    print(f"Created claim with ID: {claim_id}")
    
    # Step 2: Verify the claim exists
    claim = test_db.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
    assert claim is not None
    assert claim.title == "Test Claim"
    
    # Step 3: Verify permissions were created
    permissions = test_db.query(Permission).filter(
        Permission.subject_type == "user",
        Permission.subject_id == user.id,
        Permission.resource_type_id == ResourceTypeEnum.CLAIM.value,
        Permission.resource_id == uuid.UUID(claim_id)
    ).all()
    
    # Convert enum objects to strings for comparison
    permission_action_values = [p.action.value if hasattr(p.action, 'value') else p.action for p in permissions]
    print(f"Permission values for claim {claim_id}: {permission_action_values}")
    assert "WRITE" in permission_action_values, "Creator should have WRITE permission"
    
    # Step 4: Update the claim without adding explicit permissions
    update_event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": claim_id},
        body=json.dumps({
            "title": "Updated Title",
            "description": "Updated description"
        }),
        auth_user=cognito_sub
    )
    update_event["headers"]["Authorization"] = f"Bearer {token}"
    
    print(f"Update event: {update_event}")
    update_response = update_claim_handler(update_event, {})
    print(f"Update response: {update_response}")
    
    # Verify update was successful
    assert update_response["statusCode"] == 200, f"Update failed with status {update_response['statusCode']}: {update_response.get('body')}"
    update_body = json.loads(update_response["body"])
    assert update_body["data"]["title"] == "Updated Title"
    
    # Verify the database was updated
    test_db.expire_all()  # Ensure we get fresh data from the database
    updated_claim = test_db.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
    print(f"Updated claim from DB: {updated_claim.title}")
    assert updated_claim.title == "Updated Title"
    assert updated_claim.description == "Updated description"

def test_claim_creator_has_delete_permission(test_db, api_gateway_event, setup_user_and_group):
    """Test that a claim creator can delete their own claim without explicit permission grants"""
    # Get test data
    user = setup_user_and_group["user"]
    group_id = setup_user_and_group["group_id"]
    cognito_sub = setup_user_and_group["cognito_sub"]
    
    print(f"\nTEST DELETE: User ID: {user.id}, Cognito Sub: {cognito_sub}, Group ID: {group_id}")
    
    # Create JWT token
    token = create_jwt_token(cognito_sub)
    
    # Step 1: Create a claim
    create_event = api_gateway_event(
        http_method="POST",
        body=json.dumps({
            "title": "Test Claim for Deletion",
            "description": "This claim will be deleted",
            "date_of_loss": "2024-01-15",
            "group_id": str(group_id)
        }),
        auth_user=cognito_sub
    )
    create_event["headers"]["Authorization"] = f"Bearer {token}"
    
    create_response = create_claim_handler(create_event, {})
    assert create_response["statusCode"] == 201
    
    create_body = json.loads(create_response["body"])
    claim_id = create_body["data"]["id"]
    print(f"Created claim with ID: {claim_id}")
    
    # Step 2: Verify the claim exists
    claim = test_db.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
    assert claim is not None
    assert claim.title == "Test Claim for Deletion"
    
    # Step 3: Verify permissions were created
    permissions = test_db.query(Permission).filter(
        Permission.subject_type == "user",
        Permission.subject_id == user.id,
        Permission.resource_type_id == ResourceTypeEnum.CLAIM.value,
        Permission.resource_id == uuid.UUID(claim_id)
    ).all()
    
    # Convert enum objects to strings for comparison
    permission_action_values = [p.action.value if hasattr(p.action, 'value') else p.action for p in permissions]
    print(f"Permission values for claim {claim_id}: {permission_action_values}")
    assert "DELETE" in permission_action_values, "Creator should have DELETE permission"
    
    # Step 4: Delete the claim without adding explicit permissions
    delete_event = api_gateway_event(
        http_method="DELETE",
        path_params={"claim_id": claim_id},
        auth_user=cognito_sub
    )
    delete_event["headers"]["Authorization"] = f"Bearer {token}"
    
    print(f"Delete event: {delete_event}")
    delete_response = delete_claim_handler(delete_event, {})
    print(f"Delete response: {delete_response}")
    
    # Verify delete was successful
    assert delete_response["statusCode"] == 200, f"Delete failed with status {delete_response['statusCode']}: {delete_response.get('body')}"
    delete_body = json.loads(delete_response["body"])
    assert "deleted successfully" in delete_body["message"]
    
    # Verify the claim was soft-deleted in the database
    test_db.expire_all()  # Ensure we get fresh data from the database
    deleted_claim = test_db.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
    print(f"Deleted claim from DB: {deleted_claim}, deleted flag: {getattr(deleted_claim, 'deleted', None)}")
    assert deleted_claim is not None, "Claim should still exist in the database (soft delete)"
    assert deleted_claim.deleted is True, "Claim should be marked as deleted"
    assert deleted_claim.deleted_at is not None, "Claim should have a deleted_at timestamp"

def test_claim_creator_permissions_are_created(test_db, api_gateway_event, setup_user_and_group):
    """Test that permissions are actually created for the claim creator"""
    # Get test data
    user = setup_user_and_group["user"]
    user_id = setup_user_and_group["user_id"]
    group_id = setup_user_and_group["group_id"]
    cognito_sub = setup_user_and_group["cognito_sub"]
    
    # Create JWT token
    token = create_jwt_token(cognito_sub)
    
    # Create a claim
    create_event = api_gateway_event(
        http_method="POST",
        body=json.dumps({
            "title": "Permission Test Claim",
            "description": "Testing permission creation",
            "date_of_loss": "2024-01-15",
            "group_id": str(group_id)
        }),
        auth_user=cognito_sub
    )
    create_event["headers"]["Authorization"] = f"Bearer {token}"
    
    create_response = create_claim_handler(create_event, {})
    assert create_response["statusCode"] == 201
    
    create_body = json.loads(create_response["body"])
    claim_id = create_body["data"]["id"]
    
    # Check that permissions were created in the database
    permissions = test_db.query(Permission).filter(
        Permission.subject_type == "user",
        Permission.subject_id == user_id,
        Permission.resource_type_id == ResourceTypeEnum.CLAIM.value,
        Permission.resource_id == uuid.UUID(claim_id)
    ).all()
    
    print(f"Found {len(permissions)} permissions for user {user_id} on claim {claim_id}")
    for p in permissions:
        print(f"Permission: {p.action}, resource_type_id: {p.resource_type_id}, resource_id: {p.resource_id}")
    
    # Verify we have READ, WRITE, and DELETE permissions
    # Convert enum objects to strings for comparison
    permission_action_values = [p.action.value if hasattr(p.action, 'value') else p.action for p in permissions]
    print(f"Permission action values: {permission_action_values}")
    
    # Check string values instead of enum objects
    assert "READ" in permission_action_values
    assert "WRITE" in permission_action_values
    assert "DELETE" in permission_action_values
