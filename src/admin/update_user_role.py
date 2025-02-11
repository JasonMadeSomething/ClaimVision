import json
import boto3
import os

cognito_client = boto3.client("cognito-idp")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")

def lambda_handler(event, context):
    """Modify a user's Cognito group (Admin Only)"""

    # Get claims from event
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = claims.get("cognito:groups", "").split(",") if claims.get("cognito:groups") else []
    
    if "admin" not in groups:
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    try:
        body = json.loads(event.get("body", "{}"))
        username = event["pathParameters"]["username"]
        action = body.get("action")  # "add" or "remove"
        role = body.get("role")  # Role name (e.g., "admin", "moderator")

        if action not in ["add", "remove"] or not role:
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid request parameters"})}

        if action == "add":
            cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName=role
            )
        elif action == "remove":
            cognito_client.admin_remove_user_from_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName=role
            )

        return {"statusCode": 200, "body": json.dumps({"message": f"User '{username}' {action}{"d" if action == "remove" else "ed"} to '{role}'"})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
