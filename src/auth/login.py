import json
import boto3
import os
from utils import response

cognito = boto3.client("cognito-idp")

COGNITO_USER_POOL_CLIENT_ID = os.environ["COGNITO_USER_POOL_CLIENT_ID"]

def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])
        email = body["email"].lower()
        password = body["password"]

        # Authenticate the user
        auth_response = cognito.initiate_auth(
            ClientId=COGNITO_USER_POOL_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
            },
        )

        tokens = auth_response["AuthenticationResult"]

        return response.api_response(
            status_code=200,
            data={
                "access_token": tokens["AccessToken"],
                "refresh_token": tokens["RefreshToken"],
                "id_token": tokens["IdToken"]
            })

    except Exception as e:
        return response.api_response(status_code=401, error_details=f"Authentication failed: {str(e)}")