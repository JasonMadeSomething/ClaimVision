import json
import boto3
import os
from utils import response

import logging
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito = boto3.client("cognito-idp")

# Read at runtime-safe scope to avoid import-time crashes
COGNITO_USER_POOL_CLIENT_ID = os.getenv("COGNITO_USER_POOL_CLIENT_ID")

def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")

    # Local helper to avoid logging PII
    def _mask_email(val):
        try:
            s = (val or "").strip()
            if "@" not in s or len(s) < 3:
                return "***"
            name, domain = s.split("@", 1)
            if len(name) <= 2:
                masked = name[:1] + "*" * max(len(name) - 1, 1)
            else:
                masked = name[:2] + "*" * max(len(name) - 4, 1) + name[-2:]
            return f"{masked}@{domain}"
        except Exception:
            return "***"

    email_for_log = "***"

    try:
        # Validate and parse request body
        if not isinstance(event, dict) or not event.get("body"):
            logger.warning(f"[{request_id}] Missing request body")
            return response.api_response(status_code=400, error_details="Invalid request: missing body")

        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            logger.warning(f"[{request_id}] Invalid JSON payload")
            return response.api_response(status_code=400, error_details="Invalid request: body must be valid JSON")

        email = str(body.get("email", "")).lower()
        password = body.get("password")
        email_for_log = _mask_email(email)

        if not email or not password:
            logger.warning(f"[{request_id}] Missing credentials for email={email_for_log}")
            return response.api_response(status_code=400, error_details="Email and password are required")

        if not COGNITO_USER_POOL_CLIENT_ID:
            logger.error(f"[{request_id}] Missing COGNITO_USER_POOL_CLIENT_ID environment variable")
            return response.api_response(status_code=500, error_details="Server misconfiguration")

        # Authenticate the user
        auth_response = cognito.initiate_auth(
            ClientId=COGNITO_USER_POOL_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
            },
        )

        tokens = auth_response.get("AuthenticationResult", {})
        if not tokens:
            logger.error(f"[{request_id}] Missing AuthenticationResult for email={email_for_log}")
            return response.api_response(status_code=500, error_details="Authentication failed")

        logger.info(f"[{request_id}] Successful authentication for email={email_for_log}")

        return response.api_response(
            status_code=200,
            data={
                "access_token": tokens["AccessToken"],
                "refresh_token": tokens["RefreshToken"],
                "id_token": tokens["IdToken"]
            })

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "ClientError")
        message = e.response.get("Error", {}).get("Message", str(e))

        # Default response
        status = 500
        user_message = "Authentication failed"

        if code in ("NotAuthorizedException", "UserNotFoundException"):
            status = 401
            user_message = "Invalid email or password"
        elif code in ("UserNotConfirmedException",):
            status = 403
            user_message = "User not confirmed"
        elif code in ("PasswordResetRequiredException",):
            status = 403
            user_message = "Password reset required"
        elif code in ("TooManyRequestsException", "ThrottlingException"):
            status = 429
            user_message = "Too many requests. Please try again later."
        elif code in ("InvalidParameterException",):
            status = 400
            user_message = "Invalid request parameters"

        logger.warning(f"[{request_id}] Cognito auth failed code={code} email={email_for_log}: {message}")
        return response.api_response(status_code=status, error_details=user_message)

    except Exception:
        logger.exception(f"[{request_id}] Unexpected error during login")
        return response.api_response(status_code=500, error_details="Internal server error")