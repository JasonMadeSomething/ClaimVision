import json
import boto3
import uuid
from os import environ
from datetime import datetime
from pydantic import ValidationError
from models import Claim  # ✅ Import the Claim model
from boto3.dynamodb.conditions import Key

# Initialize AWS resources
dynamodb = boto3.resource("dynamodb")
claims_table = dynamodb.Table(environ["CLAIMS_TABLE"])

def get_user_id(event):
    """Extract user ID from Cognito authentication token"""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    return claims.get("sub")

def lambda_handler(event, context):
    """Main Lambda function router"""
    method = event["httpMethod"]
    path = event.get("pathParameters", {})

    user_id = get_user_id(event)

    if method == "GET" and not path:
        return get_claims(user_id)
    elif method == "GET" and "id" in path:
        return get_claim_by_id(user_id, path["id"])
    elif method == "POST":
        return create_claim(user_id, event["body"])
    elif method == "PUT" and "id" in path:
        return update_claim(user_id, path["id"], event["body"])
    elif method == "DELETE" and "id" in path:
        return delete_claim(user_id, path["id"])

    return {"statusCode": 400, "body": json.dumps({"error": "Invalid request"})}

### ✅ CRUD OPERATIONS BELOW ###

def get_claims(user_id):
    """Retrieve all claims for a user"""
    response = claims_table.query(
        IndexName="UserIdIndex",
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return {"statusCode": 200, "body": json.dumps(response["Items"])}

def get_claim_by_id(user_id, claim_id):
    """Retrieve a specific claim by ID"""
    response = claims_table.get_item(Key={"id": claim_id})
    claim = response.get("Item")

    if not claim or claim["user_id"] != user_id:
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    return {"statusCode": 200, "body": json.dumps(claim)}

def create_claim(user_id, body):
    """Create a new claim with validation"""
    try:
        data = json.loads(body)
        claim = Claim(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=data["title"],
            description=data.get("description"),
            loss_date=data["loss_date"],
            status="pending",
            created_at=datetime.utcnow().isoformat(),
        )

        claims_table.put_item(Item=claim.dict())
        return {"statusCode": 201, "body": json.dumps({"id": claim.id})}
    
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"error": e.errors()})}

def update_claim(user_id, claim_id, body):
    """Update an existing claim"""
    response = claims_table.get_item(Key={"id": claim_id})
    claim_data = response.get("Item")

    if not claim_data or claim_data["user_id"] != user_id:
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    try:
        update_data = json.loads(body)
        claim = Claim(**{**claim_data, **update_data})  # Merge existing data with new data
        
        claims_table.put_item(Item=claim.dict())
        return {"statusCode": 200, "body": json.dumps({"message": "Claim updated"})}
    
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"error": e.errors()})}

def delete_claim(user_id, claim_id):
    """Delete a claim"""
    response = claims_table.get_item(Key={"id": claim_id})
    claim = response.get("Item")

    if not claim or claim["user_id"] != user_id:
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    claims_table.delete_item(Key={"id": claim_id})
    return {"statusCode": 200, "body": json.dumps({"message": "Claim deleted"})}
