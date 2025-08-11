import boto3
import os
import uuid
import json
from utils import response

sqs = boto3.client("sqs")
cognito = boto3.client("cognito-idp")
USER_REGISTRATION_QUEUE_URL = os.environ["USER_REGISTRATION_QUEUE_URL"]
COGNITO_USER_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        email = body["email"].lower()
        password = body["password"]
        first_name = body.get("first_name") or "New"
        last_name = body.get("last_name") or "User"

        # Create user in Cognito
        cognito.sign_up(
            ClientId=os.environ["COGNITO_USER_POOL_CLIENT_ID"],
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
            ],
        )

        # Use AdminGetUser to retrieve Cognito sub
        describe = cognito.admin_get_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=email
        )

        sub = next(attr["Value"] for attr in describe["UserAttributes"] if attr["Name"] == "sub")

        # Queue user creation in DB
        sqs.send_message(
            QueueUrl=USER_REGISTRATION_QUEUE_URL,
            MessageBody=json.dumps({
                "cognito_sub": sub,
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            })
        )

        return response.api_response(
            status_code=200,
            success_message="Registration initiated",
            data={"cognito_sub": sub},
            event=event,
        )

    except Exception as e:
        return response.api_response(status_code=500, error_details=str(e), event=event)
