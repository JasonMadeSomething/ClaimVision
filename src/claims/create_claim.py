"""
Create Claim Handler

Handles the creation of a new claim for an authenticated user.
Ensures input validation, structured error handling, and standardized responses.

Example Usage:
    ```
    POST /claims
    {
        "title": "Lost Phone",
        "description": "Left in a taxi",
        "loss_date": "2024-02-01"
    }
    ```
"""

import os
import json
import uuid
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from claims.model import Claim  # ✅ Import the Claim model
from utils import response

# ✅ Initialize AWS resources
dynamodb = boto3.resource("dynamodb")
claims_table = dynamodb.Table(os.environ["CLAIMS_TABLE"])

# ✅ Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, _context):
    """
    Handles the creation of a new claim.

    Validates the request body, ensures required fields are present, and stores the new claim in DynamoDB.

    Args:
        event (dict): The API Gateway event payload.
        _context (dict): The AWS Lambda execution context (unused).

    Returns:
        dict: Standardized API response with claim ID if successful.
    """
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        body = parse_request_body(event)

        # ✅ Validate required fields
        missing_fields = [field for field in ["title", "loss_date"] if field not in body]
        if missing_fields:
            return response.api_response(400, missing_fields=missing_fields)

        # ✅ Ensure `loss_date` is formatted correctly
        if not is_valid_date(body["loss_date"]):
            return response.api_response(400, message="Invalid date format. Expected YYYY-MM-DD")

        # ✅ Create claim object
        claim = Claim(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=body["title"],
            description=body.get("description"),
            loss_date=body["loss_date"],
            status="pending",
            created_at=datetime.utcnow().isoformat(),
        )

        # ✅ Save to DynamoDB
        claims_table.put_item(Item=claim.to_dynamodb_dict())

        logger.info(f"Claim {claim.id} created successfully for user {user_id}")

        return response.api_response(201, data={"id": claim.id})

    except KeyError:
        return response.api_response(400, message="Invalid request: Missing authentication data")

    except json.JSONDecodeError:
        return response.api_response(400, message="Invalid JSON format in request body")

    except ClientError as e:
        logger.error(f"DynamoDB ClientError: {e}")
        return response.api_response(500, message="Internal Server Error", error_details=e.response["Error"]["Message"])

    except Exception as e:
        logger.exception("Unexpected error during claim creation")
        return response.api_response(500, message="Internal Server Error", error_details=str(e))


def parse_request_body(event):
    """
    Parses the request body and ensures it's a valid dictionary.

    Args:
        event (dict): API Gateway event.

    Returns:
        dict: Parsed request body.
    """
    body = json.loads(event.get("body") or "{}")
    if not isinstance(body, dict):
        raise json.JSONDecodeError("Request body must be a valid JSON object", "", 0)
    return body


def is_valid_date(date_str):
    """
    Validates if a string follows the YYYY-MM-DD date format.

    Args:
        date_str (str): The date string to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False
