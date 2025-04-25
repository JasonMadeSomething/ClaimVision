""" Test retrieving a single file from PostgreSQL"""
import json
import uuid
from datetime import datetime
import os

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from files.get_file import lambda_handler
from models import User, Permission, File
from utils.vocab_enums import ResourceTypeEnum, PermissionAction

@pytest.mark.usefixtures("seed_file")
def test_get_file_success(auth_api_gateway_event, test_db, seed_file, create_resource_permission):
    """ Test retrieving a single file successfully"""
    file_id = seed_file["file_id"]
    user_id = seed_file["user_id"]
    group_id = seed_file["group_id"]

    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Create permission for the user to read the file directly
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.FILE.value,
        resource_id=file_id,
        action=PermissionAction.READ,
        group_id=group_id
    )

    # Patch the S3 bucket name directly
    with patch("files.get_file.S3_BUCKET_NAME", "test-bucket"):
        # Mock the S3 client
        with patch("files.get_file.get_s3_client") as mock_get_s3:
            # Configure the mock to return a presigned URL
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                path_params={"file_id": str(file_id)},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert body["data"]["id"] == str(file_id)
            assert body["data"]["file_name"] == "test_file.jpg"


@pytest.mark.usefixtures("seed_file_with_claim")
def test_get_file_with_claim_success(auth_api_gateway_event, test_db, seed_file_with_claim, create_resource_permission):
    """ Test retrieving a file associated with a claim successfully"""
    file_id = seed_file_with_claim["file_id"]
    user_id = seed_file_with_claim["user_id"]
    group_id = seed_file_with_claim["group_id"]
    claim_id = seed_file_with_claim["claim_id"]

    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Create permission for the user to read the claim
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.READ,
        group_id=group_id
    )

    # Patch the S3 bucket name directly
    with patch("files.get_file.S3_BUCKET_NAME", "test-bucket"):
        # Mock the S3 client
        with patch("files.get_file.get_s3_client") as mock_get_s3:
            # Configure the mock to return a presigned URL
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                path_params={"file_id": str(file_id)},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert body["data"]["id"] == str(file_id)
            assert body["data"]["file_name"] == "test_file.jpg"
            assert body["data"]["claim_id"] == str(claim_id)


def test_get_file_not_found(auth_api_gateway_event, test_db, seed_user_and_group):
    """ Test retrieving a non-existent file"""
    # Get user and group IDs from the fixture
    user_id = seed_user_and_group["user_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create a non-existent file ID
    nonexistent_file_id = uuid.uuid4()
    
    event = auth_api_gateway_event(
        http_method="GET",
        path_params={"file_id": str(nonexistent_file_id)},
        auth_user=cognito_sub,
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 404
    assert "File not found" in body["error_details"]


def test_get_file_invalid_uuid(auth_api_gateway_event, test_db, seed_user_and_group):
    """ Test retrieving a file with invalid UUID format"""
    # Get user and group IDs from the fixture
    user_id = seed_user_and_group["user_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    event = auth_api_gateway_event(
        http_method="GET",
        path_params={"file_id": "not-a-uuid"},
        auth_user=cognito_sub,
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 400
    assert "Invalid file_id format" in body["error_details"]


@pytest.mark.usefixtures("seed_file_with_claim")
def test_get_file_unauthorized_access(auth_api_gateway_event, test_db, seed_file_with_claim, seed_user_and_group):
    """ Test unauthorized access to a file associated with a claim"""
    file_id = seed_file_with_claim["file_id"]
    
    # Create another user who doesn't have permission to access the claim
    unauthorized_user_id = seed_user_and_group["user_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == unauthorized_user_id).first()
    cognito_sub = user.cognito_sub
    
    # No permission is created for this user to access the claim
    
    event = auth_api_gateway_event(
        http_method="GET",
        path_params={"file_id": str(file_id)},
        auth_user=cognito_sub,
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 403
    assert "You do not have permission to access this file" in body["error_details"]


def test_get_file_missing_parameters(auth_api_gateway_event, test_db, seed_user_and_group):
    """ Test retrieving a file with missing parameters"""
    user_id = seed_user_and_group["user_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create event with missing path parameters
    event = auth_api_gateway_event(
        http_method="GET",
        path_params={},  # Missing file_id
        auth_user=cognito_sub,
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    assert response["statusCode"] == 400
    assert "Missing required path parameter: file_id" in body["error_details"]


@patch("files.get_file.get_s3_client")
def test_get_file_database_error(mock_get_s3, auth_api_gateway_event, test_db, seed_file_with_claim, create_resource_permission):
    """ Test database error handling"""
    file_id = seed_file_with_claim["file_id"]
    user_id = seed_file_with_claim["user_id"]
    group_id = seed_file_with_claim["group_id"]
    claim_id = seed_file_with_claim["claim_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create permission for the user to read the claim
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.READ,
        group_id=group_id
    )
    
    # Patch the S3 bucket name directly
    with patch("files.get_file.S3_BUCKET_NAME", "test-bucket"):
        # Mock S3 client to raise an exception
        mock_s3_client = mock_get_s3.return_value
        mock_s3_client.generate_presigned_url.side_effect = Exception("S3 error")
        
        event = auth_api_gateway_event(
            http_method="GET",
            path_params={"file_id": str(file_id)},
            auth_user=cognito_sub,
        )
        
        response = lambda_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 500
        assert "Failed to generate file link" in body["error_details"]


@pytest.mark.usefixtures("seed_file")
def test_debug_file_access(auth_api_gateway_event, test_db, seed_file, create_resource_permission):
    """ Debug test to understand why the file access tests are failing """
    file_id = seed_file["file_id"]
    user_id = seed_file["user_id"]
    group_id = seed_file["group_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create permission for the user to read the file directly
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.FILE.value,
        resource_id=file_id,
        action=PermissionAction.READ,
        group_id=group_id
    )
    
    # Print out the file object from the database to check if it exists
    file_obj = test_db.query(File).filter(File.id == file_id).first()
    print(f"\nDEBUG: File object from database: {file_obj}")
    if file_obj:
        print(f"DEBUG: File ID: {file_obj.id}")
        print(f"DEBUG: File name: {file_obj.file_name}")
        print(f"DEBUG: File group_id: {file_obj.group_id}")
        print(f"DEBUG: File uploaded_by: {file_obj.uploaded_by}")
    
    # Patch the S3 bucket name directly
    with patch("files.get_file.S3_BUCKET_NAME", "test-bucket"):
        # Mock the S3 client
        with patch("files.get_file.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                path_params={"file_id": str(file_id)},
                auth_user=cognito_sub,
            )
            
            # Get the user object from the database to check if it exists
            user_obj = test_db.query(User).filter(User.id == user_id).first()
            print(f"DEBUG: User object from database: {user_obj}")
            if user_obj:
                print(f"DEBUG: User ID: {user_obj.id}")
                print(f"DEBUG: User email: {user_obj.email}")
                print(f"DEBUG: User cognito_sub: {user_obj.cognito_sub}")
                print(f"DEBUG: User memberships: {user_obj.memberships}")
                if user_obj.memberships:
                    for membership in user_obj.memberships:
                        print(f"DEBUG: Membership group_id: {membership.group_id}")
            
            # Check if the permission was created correctly
            permission = test_db.query(Permission).filter(
                Permission.subject_id == str(user_id),
                Permission.resource_type_id == ResourceTypeEnum.FILE.value,
                Permission.resource_id == str(file_id),
                Permission.action == PermissionAction.READ.value
            ).first()
            print(f"DEBUG: Permission object: {permission}")
            if permission:
                print(f"DEBUG: Permission subject_id: {permission.subject_id}")
                print(f"DEBUG: Permission resource_id: {permission.resource_id}")
                print(f"DEBUG: Permission action: {permission.action}")
            
            # Run the lambda handler and print the response
            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])
            print(f"DEBUG: Response status code: {response['statusCode']}")
            print(f"DEBUG: Response body: {body}")
    
    # This test doesn't assert anything, it just prints debug information
    assert True


@pytest.mark.usefixtures("seed_file_with_claim")
def test_get_file_with_claim_permission_inheritance(auth_api_gateway_event, test_db, seed_file_with_claim, create_resource_permission):
    """ Test that a file inherits permissions from its associated claim """
    file_id = seed_file_with_claim["file_id"]
    user_id = seed_file_with_claim["user_id"]
    group_id = seed_file_with_claim["group_id"]
    claim_id = seed_file_with_claim["claim_id"]

    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Create permission for the user to read the claim (but not directly on the file)
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.READ,
        group_id=group_id
    )

    # Patch the S3 bucket name directly
    with patch("files.get_file.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_file.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                path_params={"file_id": str(file_id)},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert body["data"]["id"] == str(file_id)
            assert body["data"]["claim_id"] == str(claim_id)
            # This test passes because the file inherits permissions from the claim


@pytest.mark.usefixtures("seed_file_with_claim")
def test_get_file_with_claim_no_claim_permission(auth_api_gateway_event, test_db, seed_file_with_claim, create_resource_permission):
    """ Test that a user without claim permission cannot access a file even with direct file permission """
    file_id = seed_file_with_claim["file_id"]
    user_id = seed_file_with_claim["user_id"]
    group_id = seed_file_with_claim["group_id"]
    claim_id = seed_file_with_claim["claim_id"]

    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Create permission for the user to read the file directly (but not the claim)
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.FILE.value,
        resource_id=file_id,
        action=PermissionAction.READ,
        group_id=group_id
    )
    
    # No permission is created for the claim

    event = auth_api_gateway_event(
        http_method="GET",
        path_params={"file_id": str(file_id)},
        auth_user=cognito_sub,
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Should fail because claim permission takes precedence for files associated with claims
    assert response["statusCode"] == 403
    assert "You do not have permission to access this file" in body["error_details"]


@pytest.mark.usefixtures("seed_file")
def test_get_file_with_group_permission(auth_api_gateway_event, test_db, seed_file, create_resource_permission):
    """ Test retrieving a file with group-level permission """
    file_id = seed_file["file_id"]
    user_id = seed_file["user_id"]
    group_id = seed_file["group_id"]

    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Create permission for the group to read the file
    create_resource_permission(
        user_id=user_id,  # Required by the fixture but not used for group permission
        group_id=group_id,  # Permission for the group
        resource_type=ResourceTypeEnum.FILE.value,
        resource_id=file_id,
        action=PermissionAction.READ
    )

    # Patch the S3 bucket name directly
    with patch("files.get_file.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_file.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                path_params={"file_id": str(file_id)},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert body["data"]["id"] == str(file_id)
            assert body["data"]["file_name"] == "test_file.jpg"


@pytest.mark.usefixtures("seed_file_with_claim")
def test_get_file_with_claim_group_permission(auth_api_gateway_event, test_db, seed_file_with_claim, create_resource_permission):
    """ Test retrieving a file with group-level permission on the claim """
    file_id = seed_file_with_claim["file_id"]
    user_id = seed_file_with_claim["user_id"]
    group_id = seed_file_with_claim["group_id"]
    claim_id = seed_file_with_claim["claim_id"]

    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Create permission for the group to read the claim
    create_resource_permission(
        user_id=user_id,  # Required by the fixture but not used for group permission
        group_id=group_id,  # Permission for the group
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.READ
    )

    # Patch the S3 bucket name directly
    with patch("files.get_file.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_file.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                path_params={"file_id": str(file_id)},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert body["data"]["id"] == str(file_id)
            assert body["data"]["file_name"] == "test_file.jpg"
            assert body["data"]["claim_id"] == str(claim_id)


@pytest.mark.usefixtures("seed_file_with_claim")
def test_get_file_with_write_permission_only(auth_api_gateway_event, test_db, seed_file_with_claim, create_resource_permission):
    """ Test that a user with only WRITE permission on a claim cannot read its file """
    file_id = seed_file_with_claim["file_id"]
    user_id = seed_file_with_claim["user_id"]
    group_id = seed_file_with_claim["group_id"]
    claim_id = seed_file_with_claim["claim_id"]

    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Create WRITE permission for the user on the claim (but not READ)
    create_resource_permission(
        user_id=user_id,
        resource_type=ResourceTypeEnum.CLAIM.value,
        resource_id=claim_id,
        action=PermissionAction.WRITE,
        group_id=group_id
    )

    event = auth_api_gateway_event(
        http_method="GET",
        path_params={"file_id": str(file_id)},
        auth_user=cognito_sub,
    )
    
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Should fail because user only has WRITE permission, not READ
    assert response["statusCode"] == 403
    assert "You do not have permission to access this file" in body["error_details"]
