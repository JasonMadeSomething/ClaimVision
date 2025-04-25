import json
import pytest
import uuid
import base64
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from models.claim import Claim
from models.user import User
from models.group import Group
from models.group_membership import GroupMembership
from models.permissions import Permission
from utils.vocab_enums import GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum, GroupTypeEnum, ResourceTypeEnum, PermissionAction
from claims.update_claim import lambda_handler

def test_update_claim_success(test_db, api_gateway_event, seed_user_and_group, create_jwt_token, create_resource_permission):
    """Test successful claim update"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a claim to update
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        group_id=group_id,
        title="Original Title",
        description="Original Description",
        date_of_loss=datetime(2024, 1, 1),
        created_by=user.id
    )
    test_db.add(claim)
    test_db.commit()
    
    # Add permission for the user to update this claim
    create_resource_permission(
        user_id=user.id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.WRITE,
        group_id=group_id
    )
    
    # Create a valid JWT token
    token = create_jwt_token(user.cognito_sub)
    
    # Create the event with updated claim data
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps({
            "title": "Updated Title",
            "description": "Updated Description"
        }),
        auth_user=user.cognito_sub
    )
    event["headers"]["Authorization"] = f"Bearer {token}"
    
    # Call the lambda handler
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    # Verify the response
    assert response["statusCode"] == 200
    assert body["data"]["title"] == "Updated Title"
    assert body["data"]["description"] == "Updated Description"
    
    # Verify the claim was updated in the database
    updated_claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
    assert updated_claim.title == "Updated Title"
    assert updated_claim.description == "Updated Description"

def test_update_claim_not_found(test_db, api_gateway_event, seed_user_and_group, create_jwt_token):
    """Test updating a non-existent claim"""
    # Get the user from the fixture
    user = seed_user_and_group["user"]
    
    # Generate a random claim ID that doesn't exist
    non_existent_claim_id = uuid.uuid4()
    
    # Create a valid JWT token
    token = create_jwt_token(user.cognito_sub)
    
    # Create the event with the non-existent claim ID
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(non_existent_claim_id)},
        body=json.dumps({
            "title": "Updated Title",
            "description": "Updated Description"
        }),
        auth_user=user.cognito_sub
    )
    event["headers"]["Authorization"] = f"Bearer {token}"
    
    # Call the lambda handler
    response = lambda_handler(event, {})
    
    # Verify the response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "not found" in body["error_details"].lower()

def test_update_claim_no_permission(test_db, api_gateway_event, seed_multiple_users_and_groups, create_jwt_token):
    """Test updating a claim without permission"""
    # Get users from the fixture
    owner = seed_multiple_users_and_groups["owner"]
    viewer = seed_multiple_users_and_groups["viewer"]
    group_id = seed_multiple_users_and_groups["group_id"]
    
    # Create a claim that only the owner should be able to update
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        group_id=group_id,
        title="Owner's Claim",
        description="This claim belongs to the owner",
        date_of_loss=datetime(2024, 1, 1),
        created_by=owner.id
    )
    test_db.add(claim)
    test_db.commit()
    
    # Create a valid JWT token for the viewer
    token = create_jwt_token(viewer.cognito_sub)
    
    # Create the event with the viewer trying to update the owner's claim
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps({
            "title": "Unauthorized Update",
            "description": "This update should be rejected"
        }),
        auth_user=viewer.cognito_sub
    )
    event["headers"]["Authorization"] = f"Bearer {token}"
    
    # Call the lambda handler
    response = lambda_handler(event, {})
    
    # Verify the response
    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert "permission" in body["error_details"].lower() or "access" in body["error_details"].lower()
    
    # Verify the claim was not updated in the database
    unchanged_claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
    assert unchanged_claim.title == "Owner's Claim"
    assert unchanged_claim.description == "This claim belongs to the owner"

def test_update_claim_invalid_data(test_db, api_gateway_event, seed_user_and_group, create_jwt_token, create_resource_permission):
    """Test updating a claim with invalid data"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a claim to update
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        group_id=group_id,
        title="Original Title",
        description="Original Description",
        date_of_loss=datetime(2024, 1, 1),
        created_by=user.id
    )
    test_db.add(claim)
    test_db.commit()
    
    # Add permission for the user to update this claim
    create_resource_permission(
        user_id=user.id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.WRITE,
        group_id=group_id
    )
    
    # Create a valid JWT token
    token = create_jwt_token(user.cognito_sub)
    
    # Create the event with invalid data (empty title)
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps({
            "title": "",  # Empty title is invalid
            "description": "Updated Description"
        }),
        auth_user=user.cognito_sub
    )
    event["headers"]["Authorization"] = f"Bearer {token}"
    
    # Call the lambda handler
    response = lambda_handler(event, {})
    
    # Verify the response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "title" in body["error_details"].lower()
    
    # Verify the claim was not updated in the database
    unchanged_claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
    assert unchanged_claim.title == "Original Title"

def test_update_claim_partial(test_db, api_gateway_event, seed_user_and_group, create_jwt_token, create_resource_permission):
    """Test partial claim update (only updating some fields)"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a claim to update
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        group_id=group_id,
        title="Original Title",
        description="Original Description",
        date_of_loss=datetime(2024, 1, 1),
        created_by=user.id
    )
    test_db.add(claim)
    test_db.commit()
    
    # Add permission for the user to update this claim
    create_resource_permission(
        user_id=user.id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.WRITE,
        group_id=group_id
    )
    
    # Create a valid JWT token
    token = create_jwt_token(user.cognito_sub)
    
    # Create the event with only updating the title
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps({
            "title": "Updated Title Only"
            # No description update
        }),
        auth_user=user.cognito_sub
    )
    event["headers"]["Authorization"] = f"Bearer {token}"
    
    # Call the lambda handler
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    
    # Verify the response
    assert response["statusCode"] == 200
    assert body["data"]["title"] == "Updated Title Only"
    assert body["data"]["description"] == "Original Description"  # Description should remain unchanged
    
    # Verify the claim was partially updated in the database
    updated_claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
    assert updated_claim.title == "Updated Title Only"
    assert updated_claim.description == "Original Description"

def test_update_claim_malformed_json(test_db, api_gateway_event, seed_user_and_group, create_jwt_token):
    """Test updating a claim with malformed JSON in the request body"""
    # Get the user from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a claim to update
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        group_id=group_id,
        title="Original Title",
        description="Original Description",
        date_of_loss=datetime(2024, 1, 1),
        created_by=user.id
    )
    test_db.add(claim)
    test_db.commit()
    
    # Create a valid JWT token
    token = create_jwt_token(user.cognito_sub)
    
    # Create the event with malformed JSON
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        body="{title: 'Missing quotes', description: 'Invalid JSON'}",  # Malformed JSON
        auth_user=user.cognito_sub
    )
    event["headers"]["Authorization"] = f"Bearer {token}"
    
    # Call the lambda handler
    response = lambda_handler(event, {})
    
    # Verify the response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "json" in body["error_details"].lower()
    
    # Verify the claim was not updated in the database
    unchanged_claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
    assert unchanged_claim.title == "Original Title"

def test_update_claim_db_error(test_db, api_gateway_event, seed_user_and_group, create_jwt_token, create_resource_permission):
    """Test handling database errors during claim update"""
    # Get the user and group from the fixture
    user = seed_user_and_group["user"]
    group_id = seed_user_and_group["group_id"]
    
    # Create a claim to update
    claim_id = uuid.uuid4()
    claim = Claim(
        id=claim_id,
        group_id=group_id,
        title="Original Title",
        description="Original Description",
        date_of_loss=datetime(2024, 1, 1),
        created_by=user.id
    )
    test_db.add(claim)
    test_db.commit()
    
    # Add permission for the user to update this claim
    create_resource_permission(
        user_id=user.id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.WRITE,
        group_id=group_id
    )
    
    # Create a valid JWT token
    token = create_jwt_token(user.cognito_sub)
    
    # Create the event with updated claim data
    event = api_gateway_event(
        http_method="PUT",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps({
            "title": "Updated Title",
            "description": "Updated Description"
        }),
        auth_user=user.cognito_sub
    )
    event["headers"]["Authorization"] = f"Bearer {token}"
    
    # Patch the SQLAlchemy session commit method to raise an exception
    with patch('sqlalchemy.orm.session.Session.commit', side_effect=Exception("Test DB Error")):
        # Call the lambda handler
        response = lambda_handler(event, {})
        
        # Verify the response
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body["error_details"].lower()
        
        # Verify the claim was not updated in the database
        test_db.expire_all()  # Clear the session cache
        unchanged_claim = test_db.query(Claim).filter(Claim.id == claim_id).first()
        assert unchanged_claim.title == "Original Title"
        assert unchanged_claim.description == "Original Description"
