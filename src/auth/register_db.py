"""
Handler for user database registration.

This function handles the second part of the registration process:
1. Receives messages from SQS
2. Creates a new user and household in the database using the pre-generated household ID
"""
import json
import boto3
import uuid
from sqlalchemy.exc import OperationalError
from utils.logging_utils import get_logger
from utils import response as api_response
from models.user import User
from models.household import Household
from database.database import get_db_session
from sqlalchemy.orm import Session

logger = get_logger(__name__)

def get_cognito_client() -> boto3.client:
    """
    Get an AWS Cognito client for user authentication.
    
    Returns:
        boto3.client: Cognito IDP client for handling authentication.
    """
    return boto3.client("cognito-idp", region_name="us-east-1")

def get_sqs_client() -> boto3.client:
    """
    Get an AWS SQS client for sending messages.
    
    Returns:
        boto3.client: SQS client for sending messages.
    """
    return boto3.client("sqs", region_name="us-east-1")

def process_registration_message(message_body: dict) -> dict:
    """
    Process a registration message from SQS.
    
    Args:
        message_body (dict): The message body from SQS.
    
    Returns:
        dict: A response indicating success or failure.
    """
    user_id = message_body.get("user_id")
    email = message_body.get("email")
    first_name = message_body.get("first_name")
    last_name = message_body.get("last_name")
    household_id = message_body.get("household_id")
    
    if not user_id or not email or not first_name or not last_name or not household_id:
        return {
            "success": False,
            "error": "Missing required fields in message"
        }
    
    db: Session | None = None
    
    try:
        logger.info("Attempting to connect to database...")
        db = get_db_session()
        logger.info("Database connection successful")
        
        # Convert household_id string to UUID
        household_uuid = uuid.UUID(household_id)
        
        logger.info("Creating household in database with pre-generated ID: %s", household_id)
        household = Household(id=household_uuid, name=f"{first_name}'s Household")
        db.add(household)
        db.flush()
        logger.info("Household created with ID: %s", household.id)
        
        logger.info("Creating user in database...")
        user = User(
            id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            household_id=household.id,
        )
        db.add(user)
        logger.info("Committing changes to database...")
        db.commit()
        logger.info("Database commit successful")
        
        # Convert UUID to string to ensure JSON serialization works
        result = {
            "success": True,
            "user_id": user_id,
            "household_id": str(household.id)  # Convert UUID to string
        }
        
        return result
    
    except OperationalError as e:
        if db is not None:
            db.rollback()
        logger.error("Database operation failed: %s", str(e))
        return {
            "success": False,
            "error": f"Database operation failed: {str(e)}"
        }
    except Exception as e:
        if db is not None:
            db.rollback()
        logger.error("Error during database registration: %s", str(e))
        return {
            "success": False,
            "error": f"Error during database registration: {str(e)}"
        }
    finally:
        if db is not None:
            db.close()

def lambda_handler(event: dict, _context: dict) -> dict:
    """
    Handles SQS messages for user database registration.
    
    Args:
        event (dict): SQS event containing messages.
        _context (dict): Lambda execution context (unused).
    
    Returns:
        dict: Response indicating success or failure of processing.
    """
    logger.info("Received event: %s", json.dumps(event))
    
    if "Records" not in event:
        return api_response.api_response(400, error_details="No SQS records found in event")
    
    results = []
    
    for record in event["Records"]:
        try:
            message_body = json.loads(record["body"])
            logger.info("Processing message: %s", json.dumps(message_body))
            
            result = process_registration_message(message_body)
            results.append(result)
            
            if not result["success"]:
                logger.error("Failed to process message: %s", result['error'])
        except json.JSONDecodeError:
            logger.error("Failed to parse message body as JSON")
            results.append({
                "success": False,
                "error": "Invalid message format"
            })
        except Exception as e:
            logger.error("Unexpected error processing message: %s", str(e))
            results.append({
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            })
    
    success_count = sum(1 for result in results if result["success"])
    failure_count = len(results) - success_count
    
    return api_response.api_response(
        200,
        success_message=f"Processed {len(results)} messages: {success_count} succeeded, {failure_count} failed",
        data={"results": results}
    )
