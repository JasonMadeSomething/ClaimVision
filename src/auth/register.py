import json
import boto3
import os
import logging
from ..utils import response as response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialize Cognito client
cognito_client = boto3.client("cognito-idp", region_name="us-east-1")

# Get Cognito User Pool Client ID from environment variable
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

def lambda_handler(event, context):
    """
    Handles user registration using AWS Cognito.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Parse request body
        body = json.loads(event.get("body", "{}"))
        username = body.get("username")
        password = body.get("password")
        email = body.get("email")

        if not username or not password or not email:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Username, email, and password are required."})
            }

        # Register user in Cognito
        cognito_response = cognito_client.sign_up(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            Username=username,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}]
        )

        logger.info("User registration successful")

        return response.api_response(201, message="User registered successfully. Please confirm your email.")

    except cognito_client.exceptions.UsernameExistsException:
        return response.api_response(409, message="User already exists.")

    except cognito_client.exceptions.InvalidPasswordException as e:
        return response.api_response(400, message="Password does not meet requirements.", error_details=str(e))

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return response.api_response(500, message="An error occurred", error_details=str(e)) 
        
