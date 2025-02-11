import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
from .model import Claim  # ✅ Import the Claim model

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
claims_table = dynamodb.Table(os.environ["CLAIMS_TABLE"])

def lambda_handler(event, context):
    """Handles fetching all claims or claims within a date range"""
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]

    query_params = event.get("queryStringParameters", {})
    start_date = query_params.get("start_date")  # Expected format: YYYY-MM-DD
    end_date = query_params.get("end_date")  # Expected format: YYYY-MM-DD

    return get_claims(user_id, start_date, end_date)

def get_claims(user_id, start_date=None, end_date=None):
    """Fetch claims for a user, optionally filtered by date range"""

    try:
        # Query all claims by user_id
        response = claims_table.query(
            IndexName="UserIdIndex",
            KeyConditionExpression="user_id = :user_id",
            ExpressionAttributeValues={":user_id": user_id}
        )

        claims_data = response.get("Items", [])

        # Convert to Claim objects
        claims = [Claim(**claim) for claim in claims_data]

        # Convert loss_date back to `date` objects for filtering
        for claim in claims:
            claim.loss_date = datetime.strptime(claim.loss_date, "%Y-%m-%d").date()

        # Apply date range filtering in Python
        if start_date or end_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

            claims = [
                claim for claim in claims
                if (not start_date or claim.loss_date >= start_date) and
                   (not end_date or claim.loss_date <= end_date)
            ]

        # Convert loss_date back to string before returning (avoid serialization error)
        for claim in claims:
            claim.loss_date = claim.loss_date.strftime("%Y-%m-%d")

        return {"statusCode": 200, "body": json.dumps([claim.dict() for claim in claims])}

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": e.response['Error']['Message']})}
    except ValueError:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid date format. Use YYYY-MM-DD"})}
