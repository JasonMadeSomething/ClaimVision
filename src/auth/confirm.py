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
    Confirms a user's email using the verification code.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

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
        response = cognito_client.confirm_sign_up(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            Username=username,
            ConfirmationCode=confirmation_code
        )

        logger.info("User confirmed successfully")

        return response.api_response(200, message="User confirmed successfully. You can now log in.")

    except cognito_client.exceptions.CodeMismatchException:
        return response.api_response(400, message="Invalid confirmation code.")

    except cognito_client.exceptions.ExpiredCodeException:
        return response.api_response(400, message="Confirmation code expired. Please request a new one.")

    except cognito_client.exceptions.UserNotFoundException:
        return response.api_response(404, message="User not found.")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            response.api_response(500, message="An error occurred", error_details=str(e))
        }
