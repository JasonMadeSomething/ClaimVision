"""Test retrieving files for a user"""
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock
import os

from files.get_files import lambda_handler
from models import User, Permission, File, Claim
from utils.vocab_enums import ResourceTypeEnum, PermissionAction


@pytest.mark.usefixtures("seed_files")
def test_get_files_success(auth_api_gateway_event, test_db, seed_files, create_resource_permission):
    """Test retrieving files successfully."""
    user_id = seed_files["user_id"]
    group_id = seed_files["group_id"]
    file_ids = seed_files["file_ids"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create permissions for the user to read each file
    for file_id in file_ids:
        create_resource_permission(
            user_id=user_id,
            resource_type=ResourceTypeEnum.FILE.value,
            resource_id=file_id,
            action=PermissionAction.READ,
            group_id=group_id
        )

    # Patch the S3 bucket name directly
    with patch("files.get_files.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_files.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                query_params={"limit": "10"},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert "message" in body
            assert body["message"] == "OK"
            assert len(body["data"]["files"]) == 5


@pytest.mark.usefixtures("seed_files")
def test_get_files_pagination(auth_api_gateway_event, test_db, seed_files, create_resource_permission):
    """Test retrieving files with pagination."""
    user_id = seed_files["user_id"]
    group_id = seed_files["group_id"]
    file_ids = seed_files["file_ids"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create permissions for the user to read each file
    for file_id in file_ids:
        create_resource_permission(
            user_id=user_id,
            resource_type=ResourceTypeEnum.FILE.value,
            resource_id=file_id,
            action=PermissionAction.READ,
            group_id=group_id
        )

    # Patch the S3 bucket name directly
    with patch("files.get_files.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_files.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                query_params={"limit": "2", "offset": "0"},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert "message" in body
            assert len(body["data"]["files"]) == 2


def test_get_files_empty(auth_api_gateway_event, test_db, seed_user_and_group):
    """Test retrieving files when none exist."""
    user_id = seed_user_and_group["user_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    # Patch the S3 bucket name directly
    with patch("files.get_files.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_files.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            
            event = auth_api_gateway_event(
                http_method="GET",
                query_params={"limit": "10"},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert "message" in body
            assert len(body["data"]["files"]) == 0


@pytest.mark.usefixtures("seed_files")
def test_get_files_invalid_limit(auth_api_gateway_event, test_db, seed_files):
    """Test retrieving files with an invalid limit parameter (should return 400 Bad Request)"""
    user_id = seed_files["user_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub

    event = auth_api_gateway_event(
        http_method="GET",
        query_params={"limit": "invalid"},
        auth_user=cognito_sub,
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "error_details" in body
    assert body["error_details"] == "Invalid pagination parameters"


@pytest.mark.usefixtures("seed_files")
def test_get_files_s3_failure(auth_api_gateway_event, test_db, seed_files, create_resource_permission):
    """Test failure when S3 fails to generate signed URLs."""
    user_id = seed_files["user_id"]
    group_id = seed_files["group_id"]
    file_ids = seed_files["file_ids"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create permissions for the user to read each file
    for file_id in file_ids:
        create_resource_permission(
            user_id=user_id,
            resource_type=ResourceTypeEnum.FILE.value,
            resource_id=file_id,
            action=PermissionAction.READ,
            group_id=group_id
        )

    # Patch the S3 bucket name but make the client fail
    with patch("files.get_files.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_files.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.side_effect = Exception("S3 error")
            
            event = auth_api_gateway_event(
                http_method="GET",
                query_params={"limit": "10"},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert "warning" in body["data"]
            assert body["data"]["warning"] == "Some file URLs could not be generated"


@pytest.mark.usefixtures("seed_files_with_claim")
def test_get_files_by_claim(auth_api_gateway_event, test_db, seed_files_with_claim, create_resource_permission):
    """Test retrieving files for a specific claim."""
    user_id = seed_files_with_claim["user_id"]
    group_id = seed_files_with_claim["group_id"]
    claim_id = seed_files_with_claim["claim_id"]
    
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
    with patch("files.get_files.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_files.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                path_params={"claim_id": str(claim_id)},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert len(body["data"]["files"]) > 0
            # Check that all files are associated with the claim
            for file in body["data"]["files"]:
                assert file["claim_id"] == str(claim_id)


@pytest.mark.usefixtures("seed_files_with_claim")
def test_get_files_claim_no_permission(auth_api_gateway_event, test_db, seed_files_with_claim, seed_user_and_group):
    """Test retrieving files for a claim without permission."""
    claim_id = seed_files_with_claim["claim_id"]
    
    # Use a different user who doesn't have permission
    user_id = seed_user_and_group["user_id"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # No permission is created for this user to access the claim

    event = auth_api_gateway_event(
        http_method="GET",
        path_params={"claim_id": str(claim_id)},
        auth_user=cognito_sub,
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 403
    assert "You do not have permission to access this claim" in body["error_details"]


@pytest.mark.usefixtures("seed_files")
def test_get_files_specific_ids(auth_api_gateway_event, test_db, seed_files, create_resource_permission):
    """Test retrieving specific files by IDs."""
    user_id = seed_files["user_id"]
    group_id = seed_files["group_id"]
    file_ids = seed_files["file_ids"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create permissions for the user to read each file
    for file_id in file_ids:
        create_resource_permission(
            user_id=user_id,
            resource_type=ResourceTypeEnum.FILE.value,
            resource_id=file_id,
            action=PermissionAction.READ,
            group_id=group_id
        )

    # Select two specific file IDs
    specific_ids = [str(file_ids[0]), str(file_ids[1])]
    
    # Patch the S3 bucket name directly
    with patch("files.get_files.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_files.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                query_params={"ids": f"{specific_ids[0]},{specific_ids[1]}"},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            assert len(body["data"]["files"]) == 2
            # Check that the returned files match the requested IDs
            returned_ids = [file["id"] for file in body["data"]["files"]]
            assert set(returned_ids) == set(specific_ids)


@pytest.mark.usefixtures("seed_files")
def test_get_files_mixed_permissions(auth_api_gateway_event, test_db, seed_files, create_resource_permission):
    """Test retrieving files with mixed permissions (some accessible, some not)."""
    user_id = seed_files["user_id"]
    group_id = seed_files["group_id"]
    file_ids = seed_files["file_ids"]
    
    # Get the user's cognito_sub for authentication
    user = test_db.query(User).filter(User.id == user_id).first()
    cognito_sub = user.cognito_sub
    
    # Create permissions for only some of the files
    accessible_files = file_ids[:2]  # Only first two files
    for file_id in accessible_files:
        create_resource_permission(
            user_id=user_id,
            resource_type=ResourceTypeEnum.FILE.value,
            resource_id=file_id,
            action=PermissionAction.READ,
            group_id=group_id
        )

    # Patch the S3 bucket name directly
    with patch("files.get_files.S3_BUCKET_NAME", "test-bucket"):
        with patch("files.get_files.get_s3_client") as mock_get_s3:
            mock_s3_client = MagicMock()
            mock_get_s3.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://signed-url.com/file"
            
            event = auth_api_gateway_event(
                http_method="GET",
                query_params={"limit": "10"},
                auth_user=cognito_sub,
            )

            response = lambda_handler(event, {}, db_session=test_db)
            body = json.loads(response["body"])

            assert response["statusCode"] == 200
            # Should only return files with permissions
            assert len(body["data"]["files"]) == len(accessible_files)
            # Check that only accessible files are returned
            returned_ids = [file["id"] for file in body["data"]["files"]]
            assert set(returned_ids) == set([str(file_id) for file_id in accessible_files])