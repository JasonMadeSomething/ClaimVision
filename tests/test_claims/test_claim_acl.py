import json
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from models.claim import Claim
from models.user import User
from models.group import Group
from models.group_membership import GroupMembership
from models.permissions import Permission
from utils.vocab_enums import GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum, GroupTypeEnum, ResourceTypeEnum, PermissionAction
from claims.get_claims import lambda_handler as get_claims_handler
from claims.get_claim import lambda_handler as get_claim_handler

@pytest.fixture
def setup_multiple_groups_and_users(test_db):
    """
    Create a complex test environment with multiple users and groups for ACL testing.
    
    This fixture creates:
    - Two users (user1 and user2)
    - Two groups (group1 and group2)
    - User1 is a member of group1 only
    - User2 is a member of group2 only
    - Claims in both groups
    
    Returns a dictionary with all created entities for use in tests.
    """
    # Create users
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    
    user1 = User(
        id=user1_id,
        email="user1@example.com",
        cognito_sub=str(uuid.uuid4()),
        first_name="User",
        last_name="One"
    )
    
    user2 = User(
        id=user2_id,
        email="user2@example.com",
        cognito_sub=str(uuid.uuid4()),
        first_name="User",
        last_name="Two"
    )
    
    test_db.add_all([user1, user2])
    test_db.flush()
    
    # Create groups
    group1_id = uuid.uuid4()
    group2_id = uuid.uuid4()
    
    group1 = Group(
        id=group1_id,
        name="Group One",
        group_type_id=GroupTypeEnum.HOUSEHOLD.value,
        created_at=datetime.now(timezone.utc),
        created_by=user1_id
    )
    
    group2 = Group(
        id=group2_id,
        name="Group Two",
        group_type_id=GroupTypeEnum.HOUSEHOLD.value,
        created_at=datetime.now(timezone.utc),
        created_by=user2_id
    )
    
    test_db.add_all([group1, group2])
    test_db.flush()
    
    # Create memberships
    membership1 = GroupMembership(
        user_id=user1_id,
        group_id=group1_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    membership2 = GroupMembership(
        user_id=user2_id,
        group_id=group2_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    
    test_db.add_all([membership1, membership2])
    test_db.flush()
    
    # Create claims in each group
    group1_claim1_id = uuid.uuid4()
    group1_claim2_id = uuid.uuid4()
    group2_claim1_id = uuid.uuid4()
    
    group1_claim1 = Claim(
        id=group1_claim1_id,
        group_id=group1_id,
        title="Group 1 Claim 1",
        description="First claim in group 1",
        date_of_loss=datetime(2024, 1, 1),
        created_by=user1_id
    )
    
    group1_claim2 = Claim(
        id=group1_claim2_id,
        group_id=group1_id,
        title="Group 1 Claim 2",
        description="Second claim in group 1",
        date_of_loss=datetime(2024, 1, 2),
        created_by=user1_id
    )
    
    group2_claim1 = Claim(
        id=group2_claim1_id,
        group_id=group2_id,
        title="Group 2 Claim 1",
        description="First claim in group 2",
        date_of_loss=datetime(2024, 1, 3),
        created_by=user2_id
    )
    
    test_db.add_all([group1_claim1, group1_claim2, group2_claim1])
    test_db.flush()
    
    # Add permissions for users to access claims in their own groups
    # User 1 permissions for group 1 claims
    for claim_id in [group1_claim1_id, group1_claim2_id]:
        for action in [PermissionAction.READ, PermissionAction.WRITE, PermissionAction.DELETE]:
            permission = Permission(
                id=uuid.uuid4(),
                subject_type="user",
                subject_id=user1_id,
                resource_type_id=ResourceTypeEnum.CLAIM.value,
                resource_id=claim_id,
                action=action,
                conditions=json.dumps({"group_id": str(group1_id)}),
                group_id=group1_id
            )
            test_db.add(permission)
    
    # User 2 permissions for group 2 claims
    for action in [PermissionAction.READ, PermissionAction.WRITE, PermissionAction.DELETE]:
        permission = Permission(
            id=uuid.uuid4(),
            subject_type="user",
            subject_id=user2_id,
            resource_type_id=ResourceTypeEnum.CLAIM.value,
            resource_id=group2_claim1_id,
            action=action,
            conditions=json.dumps({"group_id": str(group2_id)}),
            group_id=group2_id
        )
        test_db.add(permission)
    
    test_db.commit()
    
    return {
        "user1": user1,
        "user2": user2,
        "group1": group1,
        "group2": group2,
        "group1_claim1": group1_claim1,
        "group1_claim2": group1_claim2,
        "group2_claim1": group2_claim1,
        "user1_id": user1_id,
        "user2_id": user2_id,
        "group1_id": group1_id,
        "group2_id": group2_id,
        "group1_claim1_id": group1_claim1_id,
        "group1_claim2_id": group1_claim2_id,
        "group2_claim1_id": group2_claim1_id
    }

def test_user_can_only_see_own_group_claims(test_db, api_gateway_event, setup_multiple_groups_and_users, create_jwt_token):
    """Test that a user can only see claims from groups they belong to"""
    # Get test data
    user1 = setup_multiple_groups_and_users["user1"]
    user2 = setup_multiple_groups_and_users["user2"]
    
    # Create JWT tokens
    user1_token = create_jwt_token(user1.cognito_sub)
    user2_token = create_jwt_token(user2.cognito_sub)
    
    # User 1 gets claims
    user1_event = api_gateway_event(
        http_method="GET",
        auth_user=user1.cognito_sub
    )
    user1_event["headers"]["Authorization"] = f"Bearer {user1_token}"
    
    user1_response = get_claims_handler(user1_event, {})
    user1_body = json.loads(user1_response["body"])
    
    # User 2 gets claims
    user2_event = api_gateway_event(
        http_method="GET",
        auth_user=user2.cognito_sub
    )
    user2_event["headers"]["Authorization"] = f"Bearer {user2_token}"
    
    user2_response = get_claims_handler(user2_event, {})
    user2_body = json.loads(user2_response["body"])
    
    # Verify that user1 can only see group1 claims
    assert user1_response["statusCode"] == 200
    assert len(user1_body["data"]["results"]) == 2
    claim_titles = [claim["title"] for claim in user1_body["data"]["results"]]
    assert "Group 1 Claim 1" in claim_titles
    assert "Group 1 Claim 2" in claim_titles
    assert "Group 2 Claim 1" not in claim_titles
    
    # Verify that user2 can only see group2 claims
    assert user2_response["statusCode"] == 200
    assert len(user2_body["data"]["results"]) == 1
    claim_titles = [claim["title"] for claim in user2_body["data"]["results"]]
    assert "Group 2 Claim 1" in claim_titles
    assert "Group 1 Claim 1" not in claim_titles
    assert "Group 1 Claim 2" not in claim_titles

def test_cross_group_claim_access(test_db, api_gateway_event, setup_multiple_groups_and_users, create_jwt_token):
    """Test that a user can access a specific claim from another group if they have explicit permission"""
    # Get test data
    user1 = setup_multiple_groups_and_users["user1"]
    user2 = setup_multiple_groups_and_users["user2"]
    group1_id = setup_multiple_groups_and_users["group1_id"]
    group2_id = setup_multiple_groups_and_users["group2_id"]
    group1_claim1_id = setup_multiple_groups_and_users["group1_claim1_id"]
    group2_claim1_id = setup_multiple_groups_and_users["group2_claim1_id"]
    
    # Grant user2 access to group1_claim1 (simulating an invite)
    cross_group_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=user2.id,
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=group1_claim1_id,
        action=PermissionAction.READ,
        conditions=json.dumps({"invited": True}),
        group_id=group1_id
    )
    test_db.add(cross_group_permission)
    test_db.commit()
    
    # Create JWT tokens
    user2_token = create_jwt_token(user2.cognito_sub)
    
    # User 2 gets all claims
    user2_event = api_gateway_event(
        http_method="GET",
        auth_user=user2.cognito_sub
    )
    user2_event["headers"]["Authorization"] = f"Bearer {user2_token}"
    
    user2_response = get_claims_handler(user2_event, {})
    user2_body = json.loads(user2_response["body"])
    
    # Verify that user2 can see both their own claim and the shared claim
    assert user2_response["statusCode"] == 200
    assert len(user2_body["data"]["results"]) == 2
    claim_titles = [claim["title"] for claim in user2_body["data"]["results"]]
    assert "Group 1 Claim 1" in claim_titles  # The shared claim
    assert "Group 2 Claim 1" in claim_titles  # User2's own claim
    assert "Group 1 Claim 2" not in claim_titles  # Not shared with user2
    
    # Test that user2 can directly access the shared claim
    get_claim_event = api_gateway_event(
        http_method="GET",
        path_params={"claim_id": str(group1_claim1_id)},
        auth_user=user2.cognito_sub
    )
    get_claim_event["headers"]["Authorization"] = f"Bearer {user2_token}"
    
    get_claim_response = get_claim_handler(get_claim_event, {})
    get_claim_body = json.loads(get_claim_response["body"])
    
    # Verify user2 can access the specific claim
    assert get_claim_response["statusCode"] == 200
    assert get_claim_body["data"]["title"] == "Group 1 Claim 1"
    
    # Test that user2 cannot access a non-shared claim from group1
    get_unshared_claim_event = api_gateway_event(
        http_method="GET",
        path_params={"claim_id": str(setup_multiple_groups_and_users["group1_claim2_id"])},
        auth_user=user2.cognito_sub
    )
    get_unshared_claim_event["headers"]["Authorization"] = f"Bearer {user2_token}"
    
    get_unshared_claim_response = get_claim_handler(get_unshared_claim_event, {})
    
    # Verify user2 cannot access the non-shared claim
    assert get_unshared_claim_response["statusCode"] == 403

def test_claim_access_without_group_membership(test_db, api_gateway_event, setup_multiple_groups_and_users, create_jwt_token):
    """Test that a user can be granted access to a claim without being a member of the group"""
    # Get test data
    user1 = setup_multiple_groups_and_users["user1"]
    user2 = setup_multiple_groups_and_users["user2"]
    group1_id = setup_multiple_groups_and_users["group1_id"]
    group1_claim1_id = setup_multiple_groups_and_users["group1_claim1_id"]
    
    # Create a new user who isn't a member of any group
    external_user_id = uuid.uuid4()
    external_user = User(
        id=external_user_id,
        email="external@example.com",
        cognito_sub=str(uuid.uuid4()),
        first_name="External",
        last_name="User"
    )
    test_db.add(external_user)
    test_db.commit()
    
    # Grant the external user access to a specific claim
    external_permission = Permission(
        id=uuid.uuid4(),
        subject_type="user",
        subject_id=external_user_id,
        resource_type_id=ResourceTypeEnum.CLAIM.value,
        resource_id=group1_claim1_id,
        action=PermissionAction.READ,
        conditions=json.dumps({"external_access": True}),
        group_id=group1_id
    )
    test_db.add(external_permission)
    test_db.commit()
    
    # Create JWT token for external user
    external_token = create_jwt_token(external_user.cognito_sub)
    
    # External user tries to get all claims
    external_event = api_gateway_event(
        http_method="GET",
        auth_user=external_user.cognito_sub
    )
    external_event["headers"]["Authorization"] = f"Bearer {external_token}"
    
    external_response = get_claims_handler(external_event, {})
    external_body = json.loads(external_response["body"])
    
    # Verify that external user can see only the shared claim
    assert external_response["statusCode"] == 200
    assert len(external_body["data"]["results"]) == 1
    claim_titles = [claim["title"] for claim in external_body["data"]["results"]]
    assert "Group 1 Claim 1" in claim_titles
    
    # Test that external user can directly access the shared claim
    get_claim_event = api_gateway_event(
        http_method="GET",
        path_params={"claim_id": str(group1_claim1_id)},
        auth_user=external_user.cognito_sub
    )
    get_claim_event["headers"]["Authorization"] = f"Bearer {external_token}"
    
    get_claim_response = get_claim_handler(get_claim_event, {})
    get_claim_body = json.loads(get_claim_response["body"])
    
    # Verify external user can access the specific claim
    assert get_claim_response["statusCode"] == 200
    assert get_claim_body["data"]["title"] == "Group 1 Claim 1"

def test_permission_inheritance_does_not_apply(test_db, api_gateway_event, setup_multiple_groups_and_users, create_jwt_token):
    """Test that having permission on one claim doesn't automatically grant access to all claims in that group"""
    # Get test data
    user1 = setup_multiple_groups_and_users["user1"]
    user2 = setup_multiple_groups_and_users["user2"]
    group1_id = setup_multiple_groups_and_users["group1_id"]
    group1_claim2_id = setup_multiple_groups_and_users["group1_claim2_id"]
    
    # Grant user2 access to one specific claim in group1
    specific_claim_permission = Permission(
        id=uuid.uuid4(),
        group1_claim1_id = setup_multiple_groups_and_users["group1_claim1_id"]
        subject_type="user",
        subject_id=user2.id,
        resource_type_id=ResourceTypeEnum.CLAIM.value,  # Permission on a specific claim
        resource_id=group1_claim1_id,
        action=PermissionAction.READ,
        conditions=json.dumps({}),
        group_id=group1_id
    )
    test_db.add(specific_claim_permission)
    test_db.commit()
    
    # Create JWT token for user2
    user2_token = create_jwt_token(user2.cognito_sub)
    
    # User2 tries to get all claims
    user2_event = api_gateway_event(
        http_method="GET",
        auth_user=user2.cognito_sub
    )
    user2_event["headers"]["Authorization"] = f"Bearer {user2_token}"
    
    user2_response = get_claims_handler(user2_event, {})
    user2_body = json.loads(user2_response["body"])
    
    # Verify that user2 can see their own claim and the specific claim they have permission for
    assert user2_response["statusCode"] == 200
    claim_titles = [claim["title"] for claim in user2_body["data"]["results"]]
    assert "Group 2 Claim 1" in claim_titles  # User2's own claim
    assert "Group 1 Claim 1" in claim_titles  # The specific claim they have permission for
    assert "Group 1 Claim 2" not in claim_titles  # Should not have access to this claim
    
    # Test that user2 cannot directly access the other claim from group1
    get_claim_event = api_gateway_event(
        http_method="GET",
        path_params={"claim_id": str(group1_claim2_id)},
        auth_user=user2.cognito_sub
    )
    get_claim_event["headers"]["Authorization"] = f"Bearer {user2_token}"
    
    get_claim_response = get_claim_handler(get_claim_event, {})
    
    # Verify user2 cannot access the other claim
    assert get_claim_response["statusCode"] == 403
