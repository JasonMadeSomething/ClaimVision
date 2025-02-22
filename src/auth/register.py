import json
import boto3
import os
import logging
from utils import response as response
from models import User, Household
from database.database import get_db_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def get_cognito_client():
    """Get Cognito client with current region."""
    
    return boto3.client("cognito-idp", region_name="us-east-1")

# Get Cognito User Pool Client ID from environment variable

def lambda_handler(event, context):
    """
    Handles user registration using AWS Cognito.
    """
    db = None
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # ✅ Step 1: Parse Request
        body = json.loads(event.get("body", "{}"))
        username = body.get("username")
        password = body.get("password")
        email = body.get("email")
        first_name = body.get("first_name", "Unknown")  # ✅ Capture first name
        last_name = body.get("last_name", "User")  # ✅ Capture last name

        if not username or not password or not email:
            logger.error("Missing required fields")
            return response.api_response(400, message="Username, email, and password are required.")

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
        logger.info(f"✅ Cognito User Registered: {user_id}")

        # ✅ Step 3: Get Database Session
        db = get_db_session()
        logger.info("Acquired database session")

        # ✅ Step 4: Create a Default Household using `first_name`
        household = Household(name=f"{first_name}'s Household")  # ✅ Use first name directly
        db.add(household)
        db.flush()  # Get the household ID
        logger.info(f"✅ Household Created: ID={household.id}")

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
        logger.info(f"✅ User Inserted in DB: ID={user.id}, Household={user.household_id}")

        logger.info("✅ User registration successful")
        return response.api_response(201, message="User registered successfully. Please confirm your email.")

    except cognito_client.exceptions.UsernameExistsException:
        logger.error("Cognito: Username already exists")
        return response.api_response(409, message="User already exists.")

    except cognito_client.exceptions.InvalidPasswordException as e:
        return response.api_response(400, message=str(e))

    except Exception as e:
        if db is not None:
            db.rollback()
        logger.error(f"❌ Error during registration: {str(e)}")
        return response.api_response(500, message="Internal server error")

    finally:
        if db is not None:
            db.close()
