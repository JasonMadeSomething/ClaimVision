"""
Test the get_upload_url lambda function
"""
import json
import uuid
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from models import User, Claim, Group
from models.group_membership import GroupMembership
from files.get_upload_url import lambda_handler
from utils.vocab_enums import ResourceTypeEnum, PermissionAction, MembershipStatusEnum, GroupTypeEnum, GroupRoleEnum, GroupIdentityEnum

def test_get_upload_url_success(test_db, auth_api_gateway_event, create_resource_permission):
    """ Test a successful pre-signed URL generation """
    # Create a group, user, and claim
    group_id = uuid.uuid4()
    user_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    test_user = User(
        id=user_id, 
        email="test@example.com", 
        first_name="Test", 
        last_name="User", 
        cognito_sub="test-cognito-sub"
    )
    test_db.add(test_user)
    test_db.flush()
    
    test_group = Group(id=group_id, name="Test Group", group_type_id=GroupTypeEnum.HOUSEHOLD.value, created_by=user_id)
    test_membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        status_id=MembershipStatusEnum.ACTIVE.value,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value
    )
    test_claim = Claim(id=claim_id, group_id=group_id, title="Test Claim", created_by=user_id)
    test_db.add_all([test_group, test_membership, test_claim])
    test_db.commit()

    # Create permission for the user to write to the claim
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.WRITE,
        group_id=group_id
    )

    # Create a test file request payload
    upload_payload = {
        "files": [
            {"name": "test.jpg", "content_type": "image/jpeg"},
            {"name": "document.pdf", "content_type": "application/pdf"}
        ]
    }
    
    # Mock S3 client and presigned URL generation
    with patch("files.get_upload_url.get_s3_client") as mock_get_s3_client, \
         patch("files.get_upload_url.generate_presigned_upload_url") as mock_generate_url:
        
        mock_s3 = MagicMock()
        mock_get_s3_client.return_value = mock_s3
        
        # Mock the presigned URL generation to return test values
        mock_generate_url.side_effect = lambda **kwargs: {
            'url': f"https://test-bucket.s3.amazonaws.com/{kwargs['s3_key']}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...",
            'method': 'PUT',
            's3_key': kwargs['s3_key'],
            'bucket': kwargs['bucket_name'],
            'expires_in': 3600
        }
        
        event = auth_api_gateway_event(
            http_method="POST",
            path_params={"claim_id": str(claim_id)},
            body=json.dumps(upload_payload),
            auth_user="test-cognito-sub"
        )
        
        response = lambda_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])
        
        # Assertions
        assert response["statusCode"] == 200
        assert "data" in body
        assert "files" in body["data"]
        assert len(body["data"]["files"]) == 2
        
        # Check first file
        assert body["data"]["files"][0]["name"] == "test.jpg"
        assert body["data"]["files"][0]["status"] == "ready"
        assert "upload_url" in body["data"]["files"][0]
        assert "s3_key" in body["data"]["files"][0]
        assert body["data"]["files"][0]["method"] == "PUT"
        assert body["data"]["files"][0]["content_type"] == "image/jpeg"
        
        # Check second file
        assert body["data"]["files"][1]["name"] == "document.pdf"
        assert body["data"]["files"][1]["status"] == "ready"
        assert "upload_url" in body["data"]["files"][1]
        assert "s3_key" in body["data"]["files"][1]
        assert body["data"]["files"][1]["method"] == "PUT"
        assert body["data"]["files"][1]["content_type"] == "application/pdf"

def test_get_upload_url_no_permission(test_db, auth_api_gateway_event):
    """ Test getting upload URLs without permission (should return 403 Forbidden) """
    # Create a group, user, and claim
    group_id = uuid.uuid4()
    user_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    test_user = User(
        id=user_id, 
        email="test@example.com", 
        first_name="Test", 
        last_name="User", 
        cognito_sub="test-cognito-sub"
    )
    test_db.add(test_user)
    test_db.flush()
    
    test_group = Group(id=group_id, name="Test Group", group_type_id=GroupTypeEnum.HOUSEHOLD.value, created_by=user_id)
    test_membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        status_id=MembershipStatusEnum.ACTIVE.value,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value
    )
    test_claim = Claim(id=claim_id, group_id=group_id, title="Test Claim", created_by=user_id)
    test_db.add_all([test_group, test_membership, test_claim])
    test_db.commit()

    # No permission is created for the user to write to the claim

    # Create a test file request payload
    upload_payload = {
        "files": [{"name": "test.jpg", "content_type": "image/jpeg"}]
    }
    
    event = auth_api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps(upload_payload),
        auth_user="test-cognito-sub"
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 403
    assert "error_details" in body
    assert "You do not have permission to upload files to this claim" in body["error_details"]

def test_get_upload_url_claim_not_found(test_db, auth_api_gateway_event):
    """ Test getting upload URLs for a non-existent claim (should return 404 Not Found) """
    # Create a user but no claim
    group_id = uuid.uuid4()
    user_id = uuid.uuid4()
    nonexistent_claim_id = uuid.uuid4()

    test_user = User(
        id=user_id, 
        email="test@example.com", 
        first_name="Test", 
        last_name="User", 
        cognito_sub="test-cognito-sub"
    )
    test_db.add(test_user)
    test_db.flush()
    
    test_group = Group(id=group_id, name="Test Group", group_type_id=GroupTypeEnum.HOUSEHOLD.value, created_by=user_id)
    test_membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        status_id=MembershipStatusEnum.ACTIVE.value,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value
    )
    test_db.add_all([test_group, test_membership])
    test_db.commit()

    # Create a test file request payload
    upload_payload = {
        "files": [{"name": "test.jpg", "content_type": "image/jpeg"}]
    }
    
    event = auth_api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(nonexistent_claim_id)},
        body=json.dumps(upload_payload),
        auth_user="test-cognito-sub"
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 404
    assert "error_details" in body
    assert "Claim not found" in body["error_details"]

def test_get_upload_url_missing_files(test_db, auth_api_gateway_event, create_resource_permission):
    """ Test getting upload URLs with missing files data (should return 400 Bad Request) """
    # Create a group, user, and claim
    group_id = uuid.uuid4()
    user_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    test_user = User(
        id=user_id, 
        email="test@example.com", 
        first_name="Test", 
        last_name="User", 
        cognito_sub="test-cognito-sub"
    )
    test_db.add(test_user)
    test_db.flush()
    
    test_group = Group(id=group_id, name="Test Group", group_type_id=GroupTypeEnum.HOUSEHOLD.value, created_by=user_id)
    test_membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        status_id=MembershipStatusEnum.ACTIVE.value,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value
    )
    test_claim = Claim(id=claim_id, group_id=group_id, title="Test Claim", created_by=user_id)
    test_db.add_all([test_group, test_membership, test_claim])
    test_db.commit()

    # Create permission for the user to write to the claim
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.WRITE,
        group_id=group_id
    )

    # Create an empty payload
    upload_payload = {"files": []}
    
    event = auth_api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps(upload_payload),
        auth_user="test-cognito-sub"
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 400
    assert "error_details" in body
    assert "No files specified in request" in body["error_details"]
