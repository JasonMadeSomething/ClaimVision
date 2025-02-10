import json
import boto3
import os
import logging

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
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Username and confirmation code are required."})
            }

        # Confirm the user's email
        response = cognito_client.confirm_sign_up(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            Username=username,
            ConfirmationCode=confirmation_code
        )

        logger.info("User confirmed successfully")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "User confirmed successfully. You can now log in."})
        }

    except cognito_client.exceptions.CodeMismatchException:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid confirmation code."})
        }
    except cognito_client.exceptions.ExpiredCodeException:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Confirmation code expired. Please request a new one."})
        }
    except cognito_client.exceptions.UserNotFoundException:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "User not found."})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "An error occurred", "error": str(e)})
        }
