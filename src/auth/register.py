"""
Handler for user registration using AWS Cognito.

This function handles user registration by verifying the provided username and password.
If the username is already registered, it returns a 400 Bad Request response.
Otherwise, it creates a new user in the database and registers them in AWS Cognito.
"""
import os
import json
import logging
import re
import boto3
from sqlalchemy.exc import OperationalError
from utils import response
from models import User, Household
from database.database import get_db_session
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def get_cognito_client() -> boto3.client:
    """
    Get an AWS Cognito client for user authentication.
    
    Returns:
        boto3.client: Cognito IDP client for handling authentication.
    """
    return boto3.client("cognito-idp", region_name="us-east-1")

def is_valid_email(email: str) -> bool:
    """
    Validate email format using regex.
    
    Args:
        email (str): The email address to validate.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?$"
    return bool(re.match(email_regex, email))

def is_strong_password(password: str) -> bool:
    """
    Validate password strength before calling Cognito.
    
    Args:
        password (str): The password to validate.
    
    Returns:
        bool: True if strong, False otherwise.
    """
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
        and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def detect_missing_fields(body: dict) -> list[str]:
    """
    Detect missing required fields in the request body.
    
    Args:
        body (dict): The request body.
    
    Returns:
        list[str]: A list of missing field names.
    """
    required_fields = ["username", "password", "email", "first_name", "last_name"]
    return [field for field in required_fields if not body.get(field)]

def lambda_handler(event: dict, _context: dict) -> dict:
    """
    Handles user registration using AWS Cognito.
    
    Args:
        event (dict): API Gateway event containing the request body.
        _context (dict): Lambda execution context (unused).
    
    Returns:
        dict: API response indicating success or failure of registration.
    """
    cognito_client = get_cognito_client()
    db: Session | None = None
    try:
        logger.info("Received event: %s", json.dumps(event))
        body = json.loads(event.get("body", "{}"))
        
        missing_fields = detect_missing_fields(body)
        if missing_fields:
            return response.api_response(400, missing_fields=missing_fields)
        
        if not is_strong_password(body["password"]):
            return response.api_response(400, error_details="Weak password")
        
        if not is_valid_email(body["email"]):
            return response.api_response(400, error_details="Invalid email format.")
        
        try:
            db = get_db_session()
        except OperationalError:
            logger.error("❌ Database connection failed.")
            return response.api_response(500, error_details="Database connection failed. Please try again later.")
        
        logger.info("Attempting Cognito Sign-Up")
        cognito_response = cognito_client.sign_up(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            Username=body["username"],
            Password=body["password"],
            UserAttributes=[
                {"Name": "email", "Value": body["email"]},
                {"Name": "given_name", "Value": body["first_name"]},
                {"Name": "family_name", "Value": body["last_name"]},
            ]
        )
        user_id = cognito_response["UserSub"]
        
        household = Household(name=f"{body['first_name']}'s Household")
        db.add(household)
        db.flush()
        
        user = User(
            id=user_id,
            email=body["email"],
            first_name=body["first_name"],
            last_name=body["last_name"],
            household_id=household.id,
        )
        db.add(user)
        db.commit()
        
        try:
            cognito_client.admin_update_user_attributes(
                UserPoolId=os.getenv("COGNITO_USER_POOL_ID"),
                Username=user_id,
                UserAttributes=[{"Name": "custom:household_id", "Value": household.id}]
            )
        except Exception as e:
            logger.error("❌ Failed to update Cognito attributes: %s", str(e))
        
        return response.api_response(201, message="User registered successfully. Please confirm your email.")
    
    except cognito_client.exceptions.UsernameExistsException:
        return response.api_response(409, error_details="User already exists.")
    except cognito_client.exceptions.InvalidPasswordException as e:
        return response.api_response(400, error_details=str(e))
    except cognito_client.exceptions.InternalErrorException as e:
        return response.api_response(500, error_details="Cognito is currently unavailable. Please try again later.")
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.error("Error during registration: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
    finally:
        if db is not None:
            db.close()