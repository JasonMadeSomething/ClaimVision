"""
Authentication and Authorization Utilities

This module provides common functions for user authentication, authorization,
and parameter validation used across Lambda functions.
"""

from utils.logging_utils import get_logger
import uuid
from typing import Tuple, Optional, Union
from sqlalchemy.orm import Session
import jwt
from models import User
from utils import response

# Configure logging
logger = get_logger(__name__)

def extract_user_id(event: dict) -> Tuple[bool, Union[str, dict]]:
    auth_header = event.get("headers", {}).get("authorization") or event.get("headers", {}).get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return False, response.api_response(401, error_details="Unauthorized: Missing or malformed Authorization header")

    token = auth_header.split(" ")[1]

    try:
        # You should ideally cache the JWKS or use a known secret if you're not verifying.
        decoded = jwt.decode(token, options={"verify_signature": False})
        sub = decoded.get("sub")
        if not sub:
            return False, response.api_response(401, error_details="Unauthorized: Missing user identifier")
        return True, str(uuid.UUID(sub))
    except Exception as e:
        logger.error(f"JWT decode failed: {str(e)}")
        return False, response.api_response(401, error_details="Unauthorized: Invalid token")


def extract_resource_id(event: dict, param_name: str) -> Tuple[bool, Union[str, dict]]:
    """
    Extract and validate a resource ID from path parameters.
    
    Parameters:
        event (dict): API Gateway event with path parameters
        param_name (str): Name of the path parameter to extract
        
    Returns:
        Tuple[bool, Union[str, dict]]: 
            - Success flag (True if valid resource ID was extracted)
            - Either the validated resource ID string or an API response dict on error
    """
    resource_id = event.get("pathParameters", {}).get(param_name)
    if not resource_id:
        return False, response.api_response(400, error_details=f"{param_name} is required.")
    
    try:
        # Validate UUID format
        resource_uuid = uuid.UUID(resource_id)
        return True, str(resource_uuid)
    except ValueError:
        return False, response.api_response(400, error_details=f"Invalid {param_name} format. Expected UUID.")

def get_authenticated_user(db: Session, user_id: str, event: dict = None) -> Tuple[bool, Union[User, dict]]:
    """
    Load user by Cognito sub.
    """
    try:
        user = db.query(User).filter(User.cognito_sub == user_id).first()
        if not user:
            return False, response.api_response(404, error_details="User not found.")
        return True, user
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return False, response.api_response(500, error_details="Failed to load user.")

def get_authenticated_user_direct(db, user_id):
    """
    Get the authenticated user directly without returning a tuple.
    
    This is a convenience wrapper around get_authenticated_user.
    
    Parameters:
        db (Session): Database session
        user_id (str): User ID to look up
        
    Returns:
        User: User object if found
        
    Raises:
        Exception: If user not found or other error occurs
    """
    success, result = get_authenticated_user(db, user_id)
    if not success:
        raise Exception(f"Failed to get user: {result}")
    return result