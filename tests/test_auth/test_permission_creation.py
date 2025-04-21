"""Test permission creation directly.

This test focuses on creating permissions directly without relying on the register_db implementation.
"""
import pytest
from datetime import datetime, timezone
import uuid

from models.user import User
from models.group import Group
from models.permissions import Permission, PermissionAction
from models.resource_types import ResourceType
from models.group_membership import GroupMembership
from utils.vocab_enums import MembershipStatusEnum, GroupRoleEnum, GroupIdentityEnum, ResourceTypeEnum


@pytest.fixture
def setup_test_data(test_db):
    """Create test data for permission testing."""
    # Create a user
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        cognito_sub=str(user_id).replace('-', ''),
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    test_db.add(user)
    test_db.commit()  # Commit the user first
    
    # Create a group
    group_id = uuid.uuid4()
    group = Group(
        id=group_id,
        name="Test Group",
        group_type_id="household",
        created_by=user_id,
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(group)
    
    # Create a membership
    membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value
    )
    test_db.add(membership)
    
    # Create or get resource types
    resource_types = {}
    for rt_id, label, desc in [
        (ResourceTypeEnum.CLAIM.value, "Claim", "Insurance claim"),
        (ResourceTypeEnum.FILE.value, "File", "File attachment"),
        (ResourceTypeEnum.ITEM.value, "Item", "Claim item")
    ]:
        existing = test_db.query(ResourceType).filter_by(id=rt_id).first()
        if existing:
            resource_types[rt_id] = existing
        else:
            new_rt = ResourceType(
                id=rt_id,
                label=label,
                description=desc,
                is_active=True
            )
            test_db.add(new_rt)
            resource_types[rt_id] = new_rt
    
    test_db.commit()
    
    return {
        "user": user,
        "user_id": user_id,
        "group": group,
        "group_id": group_id,
        "resource_types": resource_types
    }


def test_create_permission_with_enum_value(test_db, setup_test_data):
    """Test creating a permission using the enum value."""
    user_id = setup_test_data["user_id"]
    group_id = setup_test_data["group_id"]
    claim_resource = setup_test_data["resource_types"][ResourceTypeEnum.CLAIM.value]
    
    # Create permission using the enum value
    permission = Permission(
        subject_id=user_id,
        subject_type="user",
        action=PermissionAction.WRITE.value,  # Using the enum value
        resource_type_id=claim_resource.id,
        group_id=group_id,
        created_by=user_id,
        created_at=datetime.now(timezone.utc)
    )
    
    test_db.add(permission)
    test_db.commit()
    
    # Query the permission back
    saved_permission = test_db.query(Permission).filter(
        Permission.subject_id == user_id,
        Permission.resource_type_id == claim_resource.id
    ).first()
    
    # Verify the permission was saved correctly
    assert saved_permission is not None
    assert saved_permission.action.value == PermissionAction.WRITE.value


def test_create_permission_with_enum_object(test_db, setup_test_data):
    """Test creating a permission using the enum object."""
    user_id = setup_test_data["user_id"]
    group_id = setup_test_data["group_id"]
    claim_resource = setup_test_data["resource_types"][ResourceTypeEnum.CLAIM.value]
    
    # Create permission using the enum object
    permission = Permission(
        subject_id=user_id,
        subject_type="user",
        action=PermissionAction.READ,  # Using the enum object
        resource_type_id=claim_resource.id,
        group_id=group_id,
        created_by=user_id,
        created_at=datetime.now(timezone.utc)
    )
    
    test_db.add(permission)
    test_db.commit()
    
    # Query the permission back
    saved_permission = test_db.query(Permission).filter(
        Permission.subject_id == user_id,
        Permission.resource_type_id == claim_resource.id,
        Permission.action == PermissionAction.READ
    ).first()
    
    # Verify the permission was saved correctly
    assert saved_permission is not None
    assert saved_permission.action == PermissionAction.READ
