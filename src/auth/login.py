import json
import boto3
import os

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
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Username and password are required."})
            }

        # Authenticate the user with Cognito
        response = cognito_client.initiate_auth(
            ClientId=USER_POOL_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            }
        )

        # Extract authentication token
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Login successful",
                "access_token": response["AuthenticationResult"]["AccessToken"],
                "id_token": response["AuthenticationResult"]["IdToken"],
                "refresh_token": response["AuthenticationResult"]["RefreshToken"]
            })
        }

    except cognito_client.exceptions.NotAuthorizedException:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Invalid username or password."})
        }
    except cognito_client.exceptions.UserNotFoundException:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "User does not exist."})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "An error occurred", "error": str(e)})
        }
