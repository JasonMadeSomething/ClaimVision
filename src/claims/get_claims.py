import json
import os
import boto3
from utils import response as response


def get_claims_table():
    """
    Returns the claims table.

    Returns:
        boto3.resource("dynamodb").Table: The claims table.
    """
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.environ["CLAIMS_TABLE"])  # Update for your environment

def lambda_handler(event, context):
    """Handle retrieving claims for a user with optional filtering by date range."""
    try:
        print("Event received:", json.dumps(event))  # Debugging output

        # Extract user_id from Cognito claims
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        print(f"Authenticated User ID: {user_id}")

        # Get query parameters (if provided)
        query_params = event.get("queryStringParameters", {}) or {}
        start_date = query_params.get("start_date")
        end_date = query_params.get("end_date")

        # Query claims based on user_id and optional date range
        return get_user_claims(user_id, start_date, end_date)

    except Exception as e:
        print("Error:", str(e))
        return response.api_response(500, message="An error occurred", error_details=str(e))

def get_user_claims(user_id, start_date=None, end_date=None):
    """Fetch claims for the authenticated user, with optional date filtering."""
    try:
        claims_table = get_claims_table()
        # Query claims using UserIdIndex
        response = claims_table.query(
            IndexName="UserIdIndex",  # Make sure this GSI exists
            KeyConditionExpression="user_id = :user_id",
            ExpressionAttributeValues={":user_id": user_id}
        )

        claims = response.get("Items", [])

        # Filter by date range if provided
        if start_date and end_date:
            claims = [
                claim for claim in claims
                if start_date <= claim["loss_date"] <= end_date
            ]

        return response.api_response(200, data=claims)

    except Exception as e:
        return response.api_response(500, message="An error occurred", error_details=str(e))
