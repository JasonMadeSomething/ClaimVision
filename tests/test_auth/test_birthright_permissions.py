"""Test birthright permissions for newly registered users.

This test ensures that when a user is created as the head of a household,
they automatically receive the necessary permissions to create and view claims.
"""
import json
import uuid
import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from models.user import User
from models.group import Group
from models.permissions import Permission, PermissionAction
from models.resource_types import ResourceType
from models.group_membership import GroupMembership
from utils.vocab_enums import MembershipStatusEnum, GroupRoleEnum, GroupIdentityEnum


@pytest.fixture
def setup_resource_types(test_db):
    """Create the necessary resource types for testing."""
    # Define resource types for claims, files, and items
    resource_types_data = [
        {
            "id": "claim",
            "label": "Claim",
            "description": "Insurance claim",
            "is_active": True
        },
        {
            "id": "file",
            "label": "File",
            "description": "File attachment",
            "is_active": True
        },
        {
            "id": "item",
            "label": "Item",
            "description": "Claim item",
            "is_active": True
        }
    ]
    
    resource_types = {}
    
    # Check if resource types already exist and create only if needed
    for rt_data in resource_types_data:
        existing = test_db.query(ResourceType).filter_by(id=rt_data["id"]).first()
        if existing:
            resource_types[existing.id] = existing
        else:
            new_rt = ResourceType(**rt_data)
            test_db.add(new_rt)
            resource_types[new_rt.id] = new_rt
    
    if resource_types:
        test_db.commit()
        
    return resource_types


@pytest.fixture
def mock_register_db(monkeypatch):
    """Mock the register_db module to avoid environment variable issues."""
    # Set up environment variables
    monkeypatch.setenv("COGNITO_UPDATE_QUEUE_URL", "https://mock-sqs-url")
    
    # Mock the SQS client
    with patch("boto3.client") as mock_boto:
        mock_sqs = mock_boto.return_value
        mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}
        
        # Import the handler only after patching
        from auth.register_db import lambda_handler as register_db_handler
        yield register_db_handler


def test_birthright_permissions_on_registration(test_db, mock_register_db):
    """Test that a user gets the correct birthright permissions when registered as a household head."""
    # Mock database session
    with patch("auth.register_db.get_db_session", return_value=test_db):
        # Generate a unique cognito_sub for testing
        cognito_sub = str(uuid.uuid4()).replace("-", "")
        
        # Create SQS event with a single record
        event = {
            "Records": [
                {
                    "messageId": "message1",
                    "body": json.dumps({
                        "cognito_sub": cognito_sub,
                        "email": "test@example.com",
                        "first_name": "John",
                        "last_name": "Doe"
                    })
                }
            ]
        }
        
        # Call the Lambda handler
        mock_register_db(event, None)
        
        # Verify user was created in database
        user = test_db.query(User).filter(User.cognito_sub == cognito_sub).first()
        assert user is not None, "User was not created"
        
        # Verify group was created
        memberships = test_db.query(GroupMembership).filter(GroupMembership.user_id == user.id).all()
        assert len(memberships) == 1, "User should have exactly one group membership"
        
        group_id = memberships[0].group_id
        group = test_db.query(Group).filter(Group.id == group_id).first()
        assert group is not None, "Group was not created"
        assert group.name == "John Doe's Household", "Group name is incorrect"
        
        # Verify membership status and role
        membership = memberships[0]
        assert membership.status_id == MembershipStatusEnum.ACTIVE, "Membership status should be ACTIVE"
        assert membership.role_id == GroupRoleEnum.OWNER, "User should have OWNER role"
        assert membership.identity_id == GroupIdentityEnum.HOMEOWNER, "User should have HOMEOWNER identity"
        
        # Verify permissions were created using raw SQL
        # This avoids SQLAlchemy's enum conversion issues
        from sqlalchemy import text
        
        # Check for permissions using raw SQL
        permission_query = text("""
            SELECT action 
            FROM permissions 
            WHERE subject_type = 'user' 
            AND subject_id = :user_id 
            AND resource_type_id = 'claim' 
            AND group_id = :group_id
        """)
        
        # Execute the query
        result = test_db.execute(permission_query, {"user_id": str(user.id), "group_id": str(group_id)}).fetchall()
        
        # Get all permission actions
        permission_actions = [row[0] for row in result]
        
        # Check if we have the right permissions
        assert "READ" in permission_actions, "User does not have READ permission for claims"
        assert "WRITE" in permission_actions, "User does not have WRITE permission for claims"


def test_birthright_permissions_scope(test_db, mock_register_db, setup_resource_types):
    """Test that birthright permissions are properly scoped to the user's group."""
    # Mock database session
    with patch("auth.register_db.get_db_session", return_value=test_db):
        # Create two users in different households
        user1_cognito_sub = str(uuid.uuid4()).replace("-", "")
        user2_cognito_sub = str(uuid.uuid4()).replace("-", "")
        
        # Create first user
        event1 = {
            "Records": [
                {
                    "messageId": "message1",
                    "body": json.dumps({
                        "cognito_sub": user1_cognito_sub,
                        "email": "user1@example.com",
                        "first_name": "User",
                        "last_name": "One"
                    })
                }
            ]
        }
        
        # Create second user
        event2 = {
            "Records": [
                {
                    "messageId": "message2",
                    "body": json.dumps({
                        "cognito_sub": user2_cognito_sub,
                        "email": "user2@example.com",
                        "first_name": "User",
                        "last_name": "Two"
                    })
                }
            ]
        }
        
        # Register both users
        mock_register_db(event1, None)
        mock_register_db(event2, None)
        
        # Get user objects
        user1 = test_db.query(User).filter(User.cognito_sub == user1_cognito_sub).first()
        user2 = test_db.query(User).filter(User.cognito_sub == user2_cognito_sub).first()
        
        # Get group IDs
        user1_memberships = test_db.query(GroupMembership).filter(GroupMembership.user_id == user1.id).all()
        user2_memberships = test_db.query(GroupMembership).filter(GroupMembership.user_id == user2.id).all()
        
        user1_group_id = user1_memberships[0].group_id
        user2_group_id = user2_memberships[0].group_id
        
        # Verify permissions are scoped to the correct groups using raw SQL
        from sqlalchemy import text
        
        # Check for User 1's permissions in their own group
        permission_query = text("""
            SELECT action 
            FROM permissions 
            WHERE subject_type = 'user' 
            AND subject_id = :user_id 
            AND resource_type_id = 'claim' 
            AND group_id = :group_id
        """)
        
        # Check User 1's permissions in their own group
        user1_permissions = test_db.execute(
            permission_query, 
            {"user_id": str(user1.id), "group_id": str(user1_group_id)}
        ).fetchall()
        
        # Check User 1's permissions in User 2's group (should be none)
        user1_in_user2_group = test_db.execute(
            permission_query, 
            {"user_id": str(user1.id), "group_id": str(user2_group_id)}
        ).fetchall()
        
        # Check User 2's permissions in their own group
        user2_permissions = test_db.execute(
            permission_query, 
            {"user_id": str(user2.id), "group_id": str(user2_group_id)}
        ).fetchall()
        
        # Check User 2's permissions in User 1's group (should be none)
        user2_in_user1_group = test_db.execute(
            permission_query, 
            {"user_id": str(user2.id), "group_id": str(user1_group_id)}
        ).fetchall()
        
        # Get permission actions
        user1_actions = [row[0] for row in user1_permissions]
        user2_actions = [row[0] for row in user2_permissions]
        
        # Verify each user has permissions in their own group
        assert "READ" in user1_actions, "User 1 should have READ permission in their own group"
        assert "WRITE" in user1_actions, "User 1 should have WRITE permission in their own group"
        assert "READ" in user2_actions, "User 2 should have READ permission in their own group"
        assert "WRITE" in user2_actions, "User 2 should have WRITE permission in their own group"
        
        # Verify users don't have permissions in each other's groups
        assert len(user1_in_user2_group) == 0, "User 1 should not have permissions in User 2's group"
        assert len(user2_in_user1_group) == 0, "User 2 should not have permissions in User 1's group"


def test_multiple_permission_actions(test_db, setup_resource_types):
    """Test that multiple permission actions can be assigned to a user."""
    # Create a test user
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        cognito_sub=str(uuid.uuid4()).replace("-", ""),
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    test_db.add(user)
    test_db.flush()  # Ensure user is in the database before referencing it
    
    # Create a test group
    group_id = uuid.uuid4()
    group = Group(
        id=group_id,
        name="Test Group",
        group_type_id="household",
        created_by=user_id,
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(group)
    
    # Create membership
    membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        status_id=MembershipStatusEnum.ACTIVE,
        role_id=GroupRoleEnum.OWNER,
        identity_id=GroupIdentityEnum.HOMEOWNER
    )
    test_db.add(membership)
    
    # Create permissions with multiple actions
    for action in [PermissionAction.READ, PermissionAction.WRITE, PermissionAction.DELETE, PermissionAction.EXPORT]:
        permission = Permission(
            subject_id=user_id,
            subject_type="user",
            action=action,
            resource_type_id="claim",
            group_id=group_id,
            created_by=user_id,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(permission)
    
    test_db.commit()
    
    # Verify all permissions were created using raw SQL
    from sqlalchemy import text
    
    # Check for permissions using raw SQL
    permission_query = text("""
        SELECT action 
        FROM permissions 
        WHERE subject_type = 'user' 
        AND subject_id = :user_id 
        AND resource_type_id = 'claim' 
        AND group_id = :group_id
    """)
    
    # Execute the query
    result = test_db.execute(permission_query, {"user_id": str(user_id), "group_id": str(group_id)}).fetchall()
    
    # Get all permission actions
    permission_actions = [row[0] for row in result]
    
    # Check if we have all the right permissions
    assert "READ" in permission_actions, "User should have READ permission"
    assert "WRITE" in permission_actions, "User should have WRITE permission"
    assert "DELETE" in permission_actions, "User should have DELETE permission"
    assert "EXPORT" in permission_actions, "User should have EXPORT permission"
