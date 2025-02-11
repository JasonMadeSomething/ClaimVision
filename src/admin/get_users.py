import json
import boto3
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito_client = boto3.client("cognito-idp")

USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

def lambda_handler(event, context):
    """Fetch all users from Cognito (Admin Only)"""

    logger.info("Received event: %s", json.dumps(event))  # Log full event

    # Extract user claims
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    logger.info("Extracted claims: %s", claims)  # Log claims

    groups = claims.get("cognito:groups", "").split(",") if claims.get("cognito:groups") else []
    logger.info("User groups: %s", groups)  # Log user groups

    if "admin" not in groups:
        logger.warning("Unauthorized access attempt by user: %s", claims.get("username"))
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    if not USER_POOL_ID:
        logger.error("COGNITO_USER_POOL_ID is not set in environment variables.")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error: Missing User Pool ID"})}

    try:
        # Fetch users from Cognito
        response = cognito_client.list_users(UserPoolId=USER_POOL_ID)
        logger.info("Cognito list_users response: %s", response)  # Log raw response

        users = [
            {
                "username": user["Username"],
                "email": next((attr["Value"] for attr in user["Attributes"] if attr["Name"] == "email"), None),
                "status": user["UserStatus"],
                "created_at": user["UserCreateDate"].isoformat()
            }
            for user in response.get("Users", [])
        ]

        return {"statusCode": 200, "body": json.dumps(users)}

    except cognito_client.exceptions.NotAuthorizedException as e:
        logger.error("Cognito authorization error: %s", str(e))
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized: " + str(e)})}

    except cognito_client.exceptions.ResourceNotFoundException as e:
        logger.error("Cognito resource not found: %s", str(e))
        return {"statusCode": 404, "body": json.dumps({"error": "User pool not found: " + str(e)})}

    except Exception as e:
        logger.exception("Unhandled exception occurred")  # Logs full stack trace
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
