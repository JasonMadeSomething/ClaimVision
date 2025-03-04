import os
import json
import logging
import boto3
import botocore.exceptions
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialize Cognito client
cognito_client = boto3.client("cognito-idp", region_name="us-east-1")

# Get Cognito User Pool Client ID from environment variable
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

def lambda_handler(event, _context):
    """
    Confirms a user's email using the verification code.
    """
    try:

        # Parse request body
        body = json.loads(event.get("body", "{}"))
        username = body.get("username")
        confirmation_code = body.get("code")

        if not username or not confirmation_code:
            missingfields = []
            if not username:
                missingfields.append("username")
            if not confirmation_code:
                missingfields.append("confirmation_code")
            return response.api_response(400, missing_fields=missingfields)

        # Confirm the user's email
        _cognito_response = cognito_client.confirm_sign_up(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            Username=username,
            ConfirmationCode=confirmation_code
        )

        logger.info("User confirmed successfully")
        print(_cognito_response)
        return response.api_response(
            200,
            message="User confirmed successfully. You can now log in."
        )

    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        
        if error_code == "CodeMismatchException":
            return response.api_response(400, error_details="Invalid confirmation code.")
        
        if error_code == "ExpiredCodeException":
            return response.api_response(400, error_details="Confirmation code expired. Please request a new one.")

        if error_code == "UserNotFoundException":
            return response.api_response(404, message="User not found.")

        logger.error(f"Unexpected Cognito error: {error_code} - {e}")
        return response.api_response(500, error_details="Internal server error")
    except Exception as e:
        logger.error("Error during confirmation: %s", str(e))
        return response.api_response(
            500,
            message="Internal server error",
            error_details=str(e)
        )
