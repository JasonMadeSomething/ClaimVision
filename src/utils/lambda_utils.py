"""
Lambda Handler Utilities

This module provides standardized patterns for AWS Lambda handlers, including:
- Common error handling patterns
- Request validation
- Authentication and authorization flows
- Database session management
- S3 operations with proper error handling

These utilities help ensure consistent behavior across all Lambda functions
and reduce code duplication.
"""

import json
import inspect
import uuid
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TypeVar

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError

from database.database import get_db_session
from utils import response, auth_utils
from utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)

# Type variables for handler function
T = TypeVar('T')
HandlerFunction = Callable[..., Dict[str, Any]]


def standard_lambda_handler(
    requires_auth: bool = True,
    requires_body: bool = False,
    required_fields: Optional[List[str]] = None
) -> Callable[[HandlerFunction], HandlerFunction]:
    """
    Decorator for standardizing Lambda handlers with common error handling patterns.
    
    Args:
        requires_auth: Whether the endpoint requires authentication
        requires_body: Whether the endpoint requires a request body
        required_fields: List of required fields in the request body
        
    Returns:
        Decorated handler function with standardized error handling
    """
    def decorator(handler_func: HandlerFunction) -> HandlerFunction:
        @wraps(handler_func)
        def wrapper(event: Dict[str, Any], context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
            # Get function name for logging
            function_name = handler_func.__name__
            
            # Log request
            http_method = event.get('httpMethod', 'UNKNOWN')
            path = event.get('path', 'UNKNOWN')
            logger.info(f"Request started: {http_method} {path} -> {function_name}")
            
            # Initialize database session
            db_session = kwargs.get('db_session')
            session_created = False
            
            try:
                # Create a new session if one wasn't provided
                if db_session is None:
                    try:
                        db_session = get_db_session()
                        session_created = True
                        logger.debug(f"{function_name}: Created new database session")
                    except SQLAlchemyError as db_error:
                        logger.error(f"{function_name}: Failed to get database session: {str(db_error)}")
                        return response.api_response(500, error_details="Failed to establish database connection")
                
                user = None
                
                # Authenticate user if required
                if requires_auth:
                    logger.debug(f"{function_name}: Extracting user from Lambda Authorizer context")

                    auth_ctx = event.get("requestContext", {}).get("authorizer", {})
                    user_id = auth_ctx.get("user_id")
                    household_id = auth_ctx.get("household_id")
                    email = auth_ctx.get("email")

                    if not all([user_id, household_id]):
                        logger.warning(f"{function_name}: Missing required auth context fields")
                        return response.api_response(401, error_details="Unauthorized: Invalid token context")

                    # Load the user from the DB if needed
                    success, result = auth_utils.get_authenticated_user(db_session, user_id, event)
                    if not success:
                        logger.warning(f"{function_name}: User not found or unauthorized: {user_id}")
                        return result

                    user = result
                    logger.debug(f"{function_name}: User authenticated: {user.id}")
                
                # Process request body if required
                body_data = {}
                if requires_body:
                    logger.debug(f"{function_name}: Processing request body")
                    try:
                        body_data = json.loads(event.get("body", "{}"))
                    except json.JSONDecodeError:
                        logger.warning(f"{function_name}: Invalid JSON in request body")
                        return response.api_response(400, error_details="Invalid JSON in request body")
                
                    # Validate required fields
                    if required_fields:
                        missing = [field for field in required_fields if field not in body_data]
                        if missing:
                            logger.warning(f"{function_name}: Missing required fields: {missing}")
                            return response.api_response(
                                400, 
                                message="Bad Request",
                                error_details="Missing required fields", 
                                data={"missing_fields": missing}
                            )
                
                # Call the actual handler with extracted data
                try:
                    logger.debug(f"{function_name}: Calling handler function")
                    # Create a dictionary with all possible parameters
                    handler_params = {
                        'event': event,
                        'context': context,
                        'db_session': db_session,
                        'user': user,
                        'body': body_data
                    }
                    
                    # Add any additional kwargs
                    handler_params.update(kwargs)
                    
                    # Get the signature of the handler function to determine which parameters it accepts
                    sig = inspect.signature(handler_func)
                    
                    # Filter the parameters to only include those accepted by the handler
                    filtered_params = {}
                    for param_name, param in sig.parameters.items():
                        # Handle parameters with underscores (e.g., _event, _context)
                        # This allows handlers to use _event, _context to indicate they're not using these parameters
                        if param_name in handler_params:
                            filtered_params[param_name] = handler_params[param_name]
                        elif param_name == '_event' and 'event' in handler_params:
                            filtered_params[param_name] = handler_params['event']
                        elif param_name == '_context' and 'context' in handler_params:
                            filtered_params[param_name] = handler_params['context']
                        elif param.kind == inspect.Parameter.VAR_KEYWORD:  # **kwargs
                            # Include all remaining parameters if the handler accepts **kwargs
                            for k, v in handler_params.items():
                                if k not in filtered_params:
                                    filtered_params[k] = v
                    
                    # Call the handler with the appropriate parameters
                    logger.debug(f"{function_name}: Calling handler with parameters: {filtered_params.keys()}")
                    result = handler_func(**filtered_params)
                    
                    # Log response status code
                    status_code = result.get("statusCode", 0)
                    logger.info(f"Request completed: {http_method} {path} -> {function_name} (Status: {status_code})")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"{function_name}: Error calling handler function: {str(e)}")
                    
                    # Add more detailed error information for debugging
                    if "missing 1 required positional argument" in str(e):
                        # Extract the missing parameter name from the error message
                        import re
                        match = re.search(r"missing 1 required positional argument: '([^']+)'", str(e))
                        if match:
                            missing_param = match.group(1)
                            available_params = list(handler_params.keys())
                            logger.error(f"{function_name}: Missing parameter '{missing_param}'. Available parameters: {available_params}")
                            logger.error(f"{function_name}: Handler signature: {sig}")
                    
                    return response.api_response(500, error_details=f"Internal server error: {str(e)}")
                
            except SQLAlchemyError as db_error:
                logger.error(f"{function_name}: Database error: {str(db_error)}")
                return response.api_response(500, message="Database error", error_details=str(db_error))
            
            except Exception as e:
                logger.exception(f"{function_name}: Unexpected error in Lambda handler: {str(e)}")
                return response.api_response(500, message="Internal Server Error", error_details=str(e))
            
            finally:
                # Close database session if we created it
                if session_created and db_session is not None:
                    try:
                        db_session.close()
                        logger.debug(f"{function_name}: Closed database session")
                    except Exception as e:
                        logger.error(f"{function_name}: Error closing database session: {str(e)}")
            
        return wrapper
    return decorator


def extract_path_param(event: Dict[str, Any], param_name: str) -> Tuple[bool, Union[str, Dict[str, Any]]]:
    """
    Extract and validate a path parameter from the event.
    
    Args:
        event: API Gateway event
        param_name: Name of the path parameter
        
    Returns:
        Tuple containing success flag and either the parameter value or an error response
    """
    path_params = event.get("pathParameters") or {}
    param_value = path_params.get(param_name)
    
    if not param_value:
        logger.warning(f"Missing required path parameter: {param_name}")
        return False, response.api_response(
            400, 
            message="Bad Request", 
            error_details=f"Missing required path parameter: {param_name}"
        )
    
    return True, param_value


def extract_uuid_param(event: Dict[str, Any], param_name: str) -> Tuple[bool, Union[str, Dict[str, Any]]]:
    """
    Extract and validate a UUID path parameter from the event.
    
    Args:
        event: API Gateway event
        param_name: Name of the path parameter
        
    Returns:
        Tuple containing success flag and either the UUID string or an error response
    """
    # First extract the parameter as a string
    success, result = extract_path_param(event, param_name)
    if not success:
        return False, result
    
    param_value = result
    
    # Validate UUID format
    try:
        # Convert to UUID to validate format, but return the original string
        param_uuid = uuid.UUID(param_value)
        logger.debug("Valid UUID extracted for %s: %s" % (param_name, param_uuid))
        return True, param_value
    except ValueError:
        logger.warning("Invalid %s format: %s" % (param_name, param_value))
        
        # Create appropriate error message based on parameter name
        if param_name == "item_id":
            error_msg = "Invalid item_id format"
        elif param_name == "file_id":
            error_msg = "Invalid file_id format"
        elif param_name == "claim_id":
            error_msg = "Invalid claim_id format"
        elif param_name == "label_id":
            error_msg = "Invalid label_id format"
        elif param_name == "id":
            error_msg = "Invalid id format. Expected UUID."
        else:
            error_msg = f"Invalid {param_name} format"
        
        return False, response.api_response(
            400, 
            message="Bad Request", 
            error_details=error_msg
        )


def s3_operation(func: Callable) -> Callable:
    """
    Decorator for handling S3 operations with proper error handling.
    
    Args:
        func: Function that performs S3 operations
        
    Returns:
        Decorated function with standardized error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.debug(f"Starting S3 operation: {func.__name__}")
            result = func(*args, **kwargs)
            logger.debug(f"S3 operation completed: {func.__name__}")
            return result
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"S3 client error in {func.__name__}: {error_code} - {error_message}")
            
            if error_code == 'NoSuchKey':
                return response.api_response(404, message="File not found", error_details=error_message)
            elif error_code == 'AccessDenied':
                return response.api_response(403, message="Access denied", error_details=error_message)
            else:
                return response.api_response(500, message="S3 operation failed", error_details=error_message)
        except BotoCoreError as e:
            logger.error(f"Boto core error in {func.__name__}: {str(e)}")
            return response.api_response(500, message="S3 operation failed", error_details=str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in S3 operation {func.__name__}: {str(e)}")
            return response.api_response(500, message="S3 operation failed", error_details=str(e))
    
    return wrapper


@s3_operation
def generate_presigned_url(s3_client, bucket_name: str, s3_key: str, expiration: int = 600) -> Optional[str]:
    """
    Generate a pre-signed URL for accessing a file in S3 with proper error handling.
    
    Args:
        s3_client: The boto3 S3 client
        bucket_name: S3 bucket name
        s3_key: The S3 object key
        expiration: Time in seconds before the URL expires
        
    Returns:
        Pre-signed URL or None if an error occurred
    """
    try:
        logger.debug("Generating presigned URL for bucket: %s, key: %s" % (bucket_name, s3_key))
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )
        logger.debug("Presigned URL generated successfully")
        return url
    except ClientError as e:
        logger.error("Failed to generate presigned URL: %s" % str(e))
        return None
    except Exception as e:
        logger.exception("Unexpected error generating presigned URL: %s" % str(e))
        return None


def get_s3_client():
    """
    Get a boto3 S3 client with standardized configuration.
    
    Returns:
        Configured S3 client
    """
    try:
        return boto3.client('s3')
    except Exception as e:
        logger.error(f"Failed to create S3 client: {str(e)}")
        raise


def get_sqs_client():
    """
    Get a boto3 SQS client with standardized configuration.
    
    Returns:
        Configured SQS client
    """
    try:
        # Set a timeout for SQS operations to avoid hanging
        from botocore.config import Config
        return boto3.client('sqs', config=Config(
            connect_timeout=5,
            read_timeout=5,
            retries={'max_attempts': 2}
        ))
    except Exception as e:
        logger.error(f"Failed to create SQS client: {str(e)}")
        raise


def get_rekognition_client():
    """
    Get a boto3 Rekognition client with standardized configuration.
    
    Returns:
        Configured Rekognition client
    """
    try:
        return boto3.client('rekognition')
    except Exception as e:
        logger.error(f"Failed to create Rekognition client: {str(e)}")
        raise
