import json
import boto3
import os
import uuid
from datetime import datetime, date
from botocore.exceptions import ClientError
from .model import Claim  # ✅ Import the Claim model
from ..utils import response as response

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
claims_table = dynamodb.Table(os.environ["CLAIMS_TABLE"])

def lambda_handler(event, context):
    """Handles creating, updating, and deleting claims"""
    http_method = event["httpMethod"]
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]

    if http_method == "POST":
        return create_claim(user_id, event["body"])
    elif http_method == "PUT":
        claim_id = event["pathParameters"]["id"]
        return update_claim(user_id, claim_id, event["body"])
    elif http_method == "DELETE":
        claim_id = event["pathParameters"]["id"]
        return delete_claim(user_id, claim_id)
    else:
        return response.api_response(405, message="Method Not Allowed")

def create_claim(user_id, body):
    """Create a new claim with validation"""
    try:
        data = json.loads(body)
        
        # ✅ Ensure loss_date is a string before passing to Pydantic
        if isinstance(data.get("loss_date"), date):
            data["loss_date"] = data["loss_date"].strftime("%Y-%m-%d")

        claim = Claim(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=data["title"],
            description=data.get("description"),
            loss_date=data["loss_date"],
            status="pending",
            created_at=datetime.utcnow().isoformat(),
        )

        claims_table.put_item(Item=claim.to_dynamodb_dict())
        return response.api_response(201, data={"id": claim.id})

    except ValueError as e:
        return response.api_response(400, message="Bad Request", error_details=str(e))
    except ClientError as e:
        return response.api_response(
            500,
            message="Internal Server Error",
            error_details=e.response['Error']['Message']
        )

def update_claim(user_id, claim_id, body):
    """Update an existing claim"""
    response = claims_table.get_item(Key={"id": claim_id})
    claim_data = response.get("Item")

    if not claim_data or claim_data["user_id"] != user_id:
        return response.api_response(403, message="Unauthorized")

    try:
        update_data = json.loads(body)
        claim = Claim(**{**claim_data, **update_data})

        claims_table.put_item(Item=claim.to_dynamodb_dict())
        return response.api_response(200, data={"message": "Claim updated"})
    
    except ValueError as e:
        return response.api_response(400, message="Bad Request", error_details=str(e))
    except ClientError as e:
        return response.api_response(
            500,
            message="Internal Server Error",
            error_details=e.response['Error']['Message']
        )

def delete_claim(user_id, claim_id):
    """Delete a claim"""
    claim_response = claims_table.get_item(Key={"id": claim_id})
    claim_data = claim_response.get("Item")

    if not claim_data or claim_data["user_id"] != user_id:
        return response.api_response(403, message="Unauthorized")

    try:
        claims_table.delete_item(Key={"id": claim_id})
        return response.api_response(200, data={"message": "Claim deleted"})
    
    except ClientError as e:
        return response.api_response(500, message="Internal Server Error", error_details=e.response['Error']['Message'])
