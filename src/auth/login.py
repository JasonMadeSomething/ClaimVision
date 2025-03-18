import json
import boto3
import os
import jwt
from utils import response
from botocore.exceptions import ClientError

def get_cognito_client() -> boto3.client:
    """
    Get an AWS Cognito client for user authentication.

    Returns:
        boto3.client: A Cognito IDP client for handling authentication.
    """
    return boto3.client("cognito-idp", region_name=os.getenv("AWS_REGION", "us-east-1"))

def lambda_handler(event: dict, _context: dict) -> dict:
    """
    Handles user login using AWS Cognito.

    Args:
        event (dict): API Gateway event containing the request body.
        context (dict): Lambda execution context (unused).

    Returns:
        dict: API response with authentication tokens or an error message.
    """
    # Parse the request body
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return response.api_response(400, error_details="Invalid request format")
    
    # Validate required fields
    username = body.get("username")
    password = body.get("password")

    if not username or not password:
        missing_fields = []
        if not username:
            missing_fields.append("username")
        if not password:
            missing_fields.append("password")
        return response.api_response(400, missing_fields=missing_fields)
    
    # Get Cognito client
    cognito_client = get_cognito_client()
    
    # Authenticate with Cognito
    try:
        # Authenticate the user with Cognito
        cognito_response = cognito_client.initiate_auth(
            ClientId=os.getenv("COGNITO_USER_POOL_CLIENT_ID"),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            }
        )
        
        # Get the user's attributes including household_id
        user_id = None
        household_id = None
        
        try:
            # Extract user ID from the ID token
            id_token = cognito_response["AuthenticationResult"]["IdToken"]
            # Convert string token to bytes if needed
            if isinstance(id_token, str):
                id_token = id_token.encode('utf-8')
            decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            user_id = decoded_token.get("sub")
            
            # Get user attributes from Cognito
            if user_id:
                user_attributes = cognito_client.admin_get_user(
                    UserPoolId=os.getenv("COGNITO_USER_POOL_ID"),
                    Username=user_id
                )
                
                # Extract household_id from user attributes
                for attr in user_attributes.get("UserAttributes", []):
                    if attr["Name"] == "custom:household_id":
                        household_id = attr["Value"]
                        break
        except (jwt.PyJWTError, ClientError) as e:
            # Log the error but don't fail the login
            print(f"Error retrieving household_id: {str(e)}")
            
        # Extract authentication token
        response_data = {
            "access_token": cognito_response["AuthenticationResult"]["AccessToken"],
            "id_token": cognito_response["AuthenticationResult"]["IdToken"],
            "refresh_token": cognito_response["AuthenticationResult"]["RefreshToken"]
        }
        
        # Include user_id and household_id if available
        if user_id:
            response_data["user_id"] = user_id
        if household_id:
            response_data["household_id"] = household_id
            
        return response.api_response(200, data=response_data)
        
    except Exception as e:
        # Handle specific Cognito exceptions
        exception_type = type(e).__name__
        error_message = str(e)
        
        if exception_type == "NotAuthorizedException":
            return response.api_response(401, error_details=error_message)
        
        elif exception_type == "UserNotFoundException":
            return response.api_response(404, error_details=error_message)
        
        elif exception_type == "UserNotConfirmedException":
            return response.api_response(403, error_details=error_message)
        
        elif exception_type == "PasswordResetRequiredException":
            return response.api_response(403, error_details=error_message)
        
        elif exception_type == "TooManyRequestsException":
            return response.api_response(429, error_details=error_message)
        
        else:
            # Catch any other exceptions
            return response.api_response(500, error_details=error_message)
