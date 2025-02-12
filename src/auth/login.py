import json
import boto3
import os
from ..utils import response as response
# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name=os.getenv("AWS_REGION", "us-east-1"))

# Get environment variables
USER_POOL_CLIENT_ID = os.getenv("COGNITO_USER_POOL_CLIENT_ID")

def lambda_handler(event, context):
    """
    Handles user login using AWS Cognito.
    Expects `username` and `password` in the request body.
    """
    try:
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
            ClientId=USER_POOL_CLIENT_ID,
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
        return {
            response.api_response(401, message="Invalid username or password")
        }
    except cognito_client.exceptions.UserNotFoundException:
        return {
            response.api_response(404, message="User does not exist.")
        }
    except Exception as e:
        return {
            response.api_response(500, message="An error occurred", error_details=str(e))
        }
