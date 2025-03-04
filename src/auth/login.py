import json
import boto3
import os
from utils import response

def get_cognito_client():
    """Get Cognito client with current region."""
    return boto3.client("cognito-idp", region_name=os.getenv("AWS_REGION", "us-east-1"))

def lambda_handler(event, context):
    """
    Handles user login using AWS Cognito.
    Expects `username` and `password` in the request body.
    """
    cognito_client = get_cognito_client()
    try:
        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError:
            return response.api_response(400, message="Invalid request format")
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        username = body.get("username")
        password = body.get("password")

        if not username or not password:
            missing_fields = []
            if not username:
                missing_fields.append("username")
            if not password:
                missing_fields.append("password")
            return response.api_response(400, missing_fields=missing_fields)
        
        # Authenticate the user with Cognito
        cognito_response = cognito_client.initiate_auth(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            }
        )

        # Extract authentication token
        return response.api_response(200, message="Login successful", data={
                "access_token": cognito_response["AuthenticationResult"]["AccessToken"],
                "id_token": cognito_response["AuthenticationResult"]["IdToken"],
                "refresh_token": cognito_response["AuthenticationResult"]["RefreshToken"]
            })
        

    except cognito_client.exceptions.NotAuthorizedException:
        return response.api_response(401, message="Invalid username or password")
       
    except cognito_client.exceptions.InternalErrorException:
        return response.api_response(500, message="Cognito is currently unavailable. Please try again later.")
    except cognito_client.exceptions.UserNotFoundException:
        return response.api_response(404, message="User does not exist.")
    except cognito_client.exceptions.UserNotConfirmedException:
        return response.api_response(403, message="User is not confirmed. Please check your email.")

    except cognito_client.exceptions.TooManyRequestsException:
        return response.api_response(429, message="Too many failed login attempts. Please try again later.")

    except cognito_client.exceptions.PasswordResetRequiredException:
        return response.api_response(403, message="Password reset required before login.")

    except Exception as e:
        return response.api_response(500, message="An error occurred", error_details=str(e))
