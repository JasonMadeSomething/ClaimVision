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

def lambda_handler(event, _context):
    """
    Resends a confirmation code to a user.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Parse request body
        body = json.loads(event.get("body", "{}"))
        username = body.get("username")

        if not username:
            return response.api_response(400, message="Username is required.")

        # Resend confirmation code
        _cognito_response = cognito_client.resend_confirmation_code(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            Username=username
        )

        logger.info("Confirmation code resent successfully")

        return response.api_response(200, message="Confirmation code sent successfully. Check your email.")

    except cognito_client.exceptions.UserNotFoundException:
        return response.api_response(404, message="User not found.")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return response.api_response(
            500,
            message="An error occurred",
            error_details=str(e)
        )