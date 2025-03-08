from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from botocore.errorfactory import ClientError
from botocore.exceptions import BotoCoreError
import boto3
import uuid
import logging
import os
from models import File, User
from database.database import get_db_session
from utils import response

logger = logging.getLogger()

def get_s3_client() -> boto3.client:
    return boto3.client('s3')

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def generate_presigned_url(s3_key: str, expiration: int = 600) -> str:
    """
    Generate a pre-signed URL for accessing a file in S3.
    
    Args:
        s3_key (str): The S3 object key.
        expiration (int): Time in seconds before the URL expires.

    Returns:
        str: A pre-signed S3 URL.
    """
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expiration
        )
        return url
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Error generating pre-signed URL: {str(e)}")
        return None


def lambda_handler(event, _context, db_session: Session = None):
    db = db_session if db_session else get_db_session()

    try:
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        file_id = event.get("pathParameters", {}).get("id")

        # Validate UUID formats
        try:
            user_uuid = uuid.UUID(user_id)
            file_uuid = uuid.UUID(file_id)
        except ValueError:
            return response.api_response(400, error_details="Invalid UUID format")

        # Retrieve user first for ownership validation
        user = db.query(User).filter_by(id=user_uuid).first()
        if not user:
            return response.api_response(404, error_details="User not found")

        # Retrieve the file, ensuring it belongs to user's household
        file_data = db.query(File).filter(
            File.id == file_uuid,
            File.household_id == user.household_id
        ).first()

        if not file_data:
            return response.api_response(404, error_details="File not found")
        
        signed_url = generate_presigned_url(file_data.s3_key)
        if not signed_url:
            return response.api_response(500, message="Failed to generate file link.")

        return response.api_response(
            200,
            data={
                **file_data.to_dict(),
                "url": signed_url
            }
        )

    except SQLAlchemyError as e:
        logging.error(f"Database error occurred: {e}")
        return response.api_response(500, error_details=str(e))

    except Exception as e:
        logging.exception("Unexpected error during file retrieval")
        return response.api_response(500, error_details=str(e))

    finally:
        if db_session is None:
            db.close()
