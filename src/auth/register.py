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
from utils import response
from models import User, Household
from database.database import get_db_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def get_cognito_client():
    """Get Cognito client with current region."""
    return boto3.client("cognito-idp", region_name="us-east-1")

def is_valid_email(email):
    """✅ Improved regex check for valid email format."""
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?$"
    return bool(re.match(email_regex, email))

def detect_missing_fields(body):
    """✅ Detect missing fields in the request body."""
    missing_fields = []
    if not body.get("username"):
        missing_fields.append("username")
    if not body.get("password"):
        missing_fields.append("password")
    if not body.get("email"):
        missing_fields.append("email")
    if not body.get("first_name"):
        missing_fields.append("first_name")
    if not body.get("last_name"):
        missing_fields.append("last_name")
    return missing_fields

def lambda_handler(event, _context):
    """
    Handles user registration using AWS Cognito.
    """
    db = None
    try:
        logger.info("Received event: %s", json.dumps(event))

        # ✅ Step 1: Parse Request
        body = json.loads(event.get("body", "{}"))
        username = body.get("username")
        password = body.get("password")
        email = body.get("email")
        first_name = body.get("first_name")  # ✅ Capture first name
        last_name = body.get("last_name")  # ✅ Capture last name

        missing_fields = detect_missing_fields(body)
        if missing_fields:
            return response.api_response(400, missing_fields=missing_fields)

        if not is_valid_email(email):
            logger.error("Registration failed. Invalid email format: %s", email)
            return response.api_response(400, error_details="Invalid email format.")

        # ✅ Step 2: Register User in Cognito
        cognito_client = get_cognito_client()
        logger.info("Attempting Cognito Sign-Up")
        cognito_response = cognito_client.sign_up(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            Username=username,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "given_name", "Value": first_name},  # ✅ Use Cognito's built-in first name
                {"Name": "family_name", "Value": last_name}  # ✅ Use Cognito's built-in last name
            ]
        )
        user_id = cognito_response["UserSub"]
        logger.info("Cognito User Registered: %s", user_id)

        # ✅ Step 3: Get Database Session
        db = get_db_session()
        logger.info("Acquired database session")

        # ✅ Step 4: Create a Default Household using `first_name`
        household = Household(name=f"{first_name}'s Household")  # ✅ Use first name directly
        db.add(household)
        db.flush()  # Get the household ID
        logger.info("Household Created: ID=%s", household.id)

        # ✅ Step 5: Create the User in PostgreSQL
        user = User(
            id=user_id,
            email=email,
            full_name=f"{first_name} {last_name}",  # ✅ Store full name
            first_name=first_name,  # ✅ Store first name separately
            last_name=last_name,  # ✅ Store last name separately
            household_id=household.id
        )
        db.add(user)
        db.commit()
        logger.info("User Inserted in DB: ID=%s, Household=%s", user.id, user.household_id)

        logger.info("✅ User registration successful")
        return response.api_response(
            201,
            message="User registered successfully. Please confirm your email."
        )

    except cognito_client.exceptions.UsernameExistsException:
        logger.error("Cognito: Username already exists")
        return response.api_response(409, error_details="User already exists.")

    except cognito_client.exceptions.InvalidPasswordException as e:
        return response.api_response(400, error_details=str(e))

    except cognito_client.exceptions.InternalErrorException as e:
        logger.error("Cognito Internal Error: %s", str(e))
        return response.api_response(
            status_code=500,
            error_details="Cognito is currently unavailable. Please try again later."
        )

    except Exception as e:
        if db is not None:
            db.rollback()
        logger.error("Error during registration: %s", str(e))
        return response.api_response(500, error_details="Internal server error")

    finally:
        if db is not None:
            db.close()
