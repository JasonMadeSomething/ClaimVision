"""
Handler for user registration with AWS Cognito.

This function handles the first part of the registration process:
1. Validates user input
2. Registers the user with AWS Cognito
3. Sends a message to SQS for database registration
"""
import json
import logging
import os
import re
import boto3
import uuid
from utils.response import api_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_cognito_client() -> boto3.client:
    """
    Returns a boto3 client for AWS Cognito.
    
    Returns:
        boto3.client: Cognito client
    """
    return boto3.client('cognito-idp')

def get_sqs_client() -> boto3.client:
    """
    Returns a boto3 client for AWS SQS.
    
    Returns:
        boto3.client: SQS client
    """
    return boto3.client('sqs')

def is_valid_email(email: str) -> bool:
    """
    Validates email format.
    
    Args:
        email (str): Email address to validate.
        
    Returns:
        bool: True if email is valid, False otherwise.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_strong_password(password: str) -> bool:
    """
    Checks if the password meets complexity requirements.
    
    Args:
        password (str): Password to validate.
        
    Returns:
        bool: True if password is strong, False otherwise.
    """
    # At least 8 characters
    if len(password) < 8:
        return False
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return False
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return False
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True

def detect_missing_fields(body: dict) -> list:
    """
    Detects missing required fields in the request body.
    
    Args:
        body (dict): Request body.
        
    Returns:
        list: List of missing field names.
    """
    required_fields = ["username", "password", "email", "first_name", "last_name"]
    return [field for field in required_fields if not body.get(field)]

def send_to_registration_queue(email: str, password: str, first_name: str, last_name: str, user_sub: str, household_id: str) -> tuple:
    """
    Send user data to SQS queue for database registration.
    
    Args:
        email (str): User's email address.
        password (str): User's password.
        first_name (str): User's first name.
        last_name (str): User's last name.
        user_sub (str): User's Cognito sub (ID).
        household_id (str): Pre-generated household ID.
        
    Returns:
        tuple: (message_id, error) where message_id is the SQS message ID if successful,
               and error is an error message if the operation failed.
    """
    queue_url = os.environ.get('USER_REGISTRATION_QUEUE_URL')
    
    if not queue_url:
        logger.error("USER_REGISTRATION_QUEUE_URL environment variable not set")
        return None, "Registration queue URL not configured"

    try:
        sqs_client = boto3.client('sqs')
        message_body = {
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'user_id': user_sub,
            'household_id': household_id
        }
        
        sqs_response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        
        logger.info("Successfully sent message to SQS queue: %s", sqs_response.get('MessageId'))
        return sqs_response.get('MessageId'), None
    except (boto3.exceptions.Boto3Error, json.JSONDecodeError) as e:
        logger.error("Failed to send message to SQS queue: %s", str(e))
        return None, f"Failed to queue registration: {str(e)}"

def lambda_handler(event, context):
    """
    Lambda handler for user registration with Cognito
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract user data
        email = body.get('email')
        password = body.get('password')
        first_name = body.get('first_name')
        last_name = body.get('last_name')

        # Validate required fields
        if not all([email, password, first_name, last_name]):
            return api_response(
                status_code=400,
                error_details="Missing required fields: email, password, first_name, last_name"
            )
        
        # Validate email format
        if not is_valid_email(email):
            return api_response(
                status_code=400,
                error_details="Invalid email format"
            )
        
        # Validate password strength
        if not is_strong_password(password):
            return api_response(
                status_code=400,
                error_details="Password does not meet complexity requirements"
            )
        
        # Generate a household ID upfront
        household_id = str(uuid.uuid4())
        logger.info(f"Generated household ID: {household_id}")
        
        # Register user with Cognito
        cognito_client = get_cognito_client()
        
        try:
            cognito_response = cognito_client.sign_up(
                ClientId=os.environ.get('COGNITO_USER_POOL_CLIENT_ID'),
                Username=email,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'custom:household_id', 'Value': household_id}
                ]
            )
            
            user_sub = cognito_response.get('UserSub')
            logger.info("Successfully registered user with Cognito: %s", user_sub)
            
            # Send user data to SQS queue for database registration
            message_id, error = send_to_registration_queue(
                email, password, first_name, last_name, user_sub, household_id
            )
            
            if error:
                logger.error("Failed to send user data to SQS queue: %s", error)
                return api_response(
                    status_code=500,
                    error_details=f"User registered with Cognito but failed to queue database registration: {error}"
                )
            
            return api_response(
                status_code=200,
                success_message="User registration initiated successfully. Please check your email for verification code.",
                data={
                    "user_id": user_sub,
                    "household_id": household_id,
                    "message_id": message_id
                }
            )
            
        except cognito_client.exceptions.UsernameExistsException:
            logger.warning("Username already exists: %s", email)
            return api_response(
                status_code=400,
                error_details="An account with this email already exists"
            )
        except cognito_client.exceptions.InvalidPasswordException as e:
            logger.warning("Invalid password: %s", str(e))
            return api_response(
                status_code=400,
                error_details=f"Invalid password: {str(e)}"
            )
        except cognito_client.exceptions.UserLambdaValidationException as e:
            logger.warning("User validation failed: %s", str(e))
            return api_response(
                status_code=400,
                error_details=f"User validation failed: {str(e)}"
            )
        except Exception as e:
            logger.error("Cognito registration error: %s", str(e))
            return api_response(
                status_code=500,
                error_details=f"Failed to register with Cognito: {str(e)}"
            )
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return api_response(
            status_code=400,
            error_details="Invalid request format"
        )
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return api_response(
            status_code=500,
            error_details=f"Unexpected error: {str(e)}"
        )
