import json
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from database.database import get_db_session
from models import File, User
from utils import response

logger = logging.getLogger()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "test-bucket")

def get_s3_client():
    """Returns an S3 client instance (supports mocking in tests)."""
    return boto3.client("s3")

def generate_presigned_url(s3_client, s3_key: str, expiration: int = 600) -> str:
    """
    Generate a pre-signed URL for accessing a file in S3.
    
    Args:
        s3_client: The mocked or real S3 client.
        s3_key (str): The S3 object key.
        expiration (int): Time in seconds before the URL expires.

    Returns:
        str: A pre-signed S3 URL.
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expiration
        )
        return url
    except (BotoCoreError, ClientError) as e:
        logger.error("Error generating pre-signed URL: %s", str(e))
        return None

def lambda_handler(event, _context, db_session: Session = None):
    """
    Retrieves a paginated list of files for the authenticated user's household.

    Parameters:
        event (dict): API Gateway event payload containing authentication and query parameters.
        _context (dict): AWS Lambda context (unused).
        db_session (Session, optional): SQLAlchemy session, for testing purposes.

    Returns:
        dict: Standardized API response.
    """
    db = db_session if db_session else get_db_session()

    try:
        # Get authenticated user ID from JWT claims
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(401, error_details="Authentication required")

        # Validate query parameters
        query_params = event.get("queryStringParameters") or {}
        try:
            limit = int(query_params.get("limit", 10))
            offset = int(query_params.get("offset", 0))
            if limit <= 0 or offset < 0:
                return response.api_response(400, error_details="Invalid pagination parameters",
                                            data={
                                                "details": "Limit must be positive and offset cannot be negative"
                                            })
        except ValueError:
            return response.api_response(400, error_details="Invalid pagination parameters",
                                        data={
                                            "details": "Limit and offset must be valid integers"
                                        })

        # Fetch user to get household_id
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return response.api_response(404, error_details="User not found")

        # Query files based on user's household_id with pagination
        files_query = db.query(File).filter_by(
            household_id=user.household_id
        ).order_by(File.file_name).limit(limit).offset(offset)

        files = files_query.all()
        files_data = []
        for file in files:
            signed_url = generate_presigned_url(get_s3_client(), file.s3_key)
            file_data = file.to_dict()
            file_data["signed_url"] = signed_url if signed_url else None
            files_data.append(file_data)

        return response.api_response(
            200,
            success_message="Files retrieved successfully",
            data={
                "files": files_data,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "count": len(files_data)
                }
            }
        )

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details="Database connection failed")

    except Exception as e:
        logger.exception("Unexpected error retrieving files")
        return response.api_response(500, error_details="Internal server error")

    finally:
        if db_session is None:
            db.close()
