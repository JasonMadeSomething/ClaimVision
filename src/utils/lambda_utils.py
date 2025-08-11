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
import re

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
                    logger.debug(f"{function_name}: Extracting user ID from token")
                    success, user_id_or_response = auth_utils.extract_user_id(event)
                    if not success:
                        return user_id_or_response

                    success, user_or_response = auth_utils.get_authenticated_user(db_session, user_id_or_response)
                    if not success:
                        return user_or_response

                    user = user_or_response
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


def enhanced_lambda_handler(
    requires_auth: bool = True,
    requires_body: bool = False,
    required_fields: Optional[List[str]] = None,
    path_params: Optional[List[str]] = None,
    permissions: Optional[Dict[str, Any]] = None,
    validation_schema: Optional[Dict[str, Dict[str, Any]]] = None,
    auto_load_resources: Optional[Dict[str, str]] = None
) -> Callable[[HandlerFunction], HandlerFunction]:
    """
    Enhanced decorator for Lambda handlers with advanced features.
    
    Args:
        requires_auth: Whether the endpoint requires authentication
        requires_body: Whether the endpoint requires a request body  
        required_fields: List of required fields in the request body
        path_params: List of path parameters to auto-extract and validate as UUIDs
        permissions: Permission configuration {'resource_type': str, 'action': str, 'path_param': str}
        validation_schema: Body field validation {'field': {'type': type, 'max_length': int, 'min': num}}
        auto_load_resources: Resource loading config {'param_name': 'ModelClass'}
        
    Returns:
        Decorated handler function with enhanced capabilities
    """
    def decorator(handler_func: HandlerFunction) -> HandlerFunction:
        @wraps(handler_func)
        def wrapper(event: Dict[str, Any], context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
            function_name = handler_func.__name__
            
            # Log request
            http_method = event.get('httpMethod', 'UNKNOWN')
            path = event.get('path', 'UNKNOWN')
            logger.info(f"Request started: {http_method} {path} -> {function_name}")
            
            # Initialize database session
            db_session = kwargs.get('db_session')
            session_created = False
            
            try:
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
                    logger.debug(f"{function_name}: Extracting user ID from token")
                    success, user_id_or_response = auth_utils.extract_user_id(event)
                    if not success:
                        return user_id_or_response

                    success, user_or_response = auth_utils.get_authenticated_user(db_session, user_id_or_response)
                    if not success:
                        return user_or_response

                    user = user_or_response
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
                    
                    # Apply validation schema if provided
                    if validation_schema:
                        validation_error = _validate_body(body_data, validation_schema)
                        if validation_error:
                            return validation_error
                
                # Auto-extract path parameters
                extracted_params = {}
                if path_params:
                    for param_name in path_params:
                        success, result = extract_uuid_param(event, param_name)
                        if not success:
                            return result
                        extracted_params[param_name] = result
                
                # Auto-load resources if configured
                loaded_resources = {}
                if auto_load_resources and extracted_params:
                    for param_name, model_class_name in auto_load_resources.items():
                        if param_name in extracted_params:
                            resource = _load_resource(db_session, model_class_name, extracted_params[param_name])
                            if not resource:
                                return response.api_response(404, error_details=f'{model_class_name} not found')
                            loaded_resources[param_name.replace('_id', '')] = resource
                
                # Check permissions using existing access control system
                if permissions and requires_auth and user:
                    permission_error = _check_permissions(
                        user, permissions, extracted_params, loaded_resources, db_session
                    )
                    if permission_error:
                        return permission_error
                
                # Prepare handler parameters
                handler_params = {
                    'event': event,
                    'context': context,
                    'db_session': db_session,
                    'user': user,
                    'body': body_data
                }
                
                # Add extracted parameters
                if extracted_params:
                    handler_params['path_params'] = extracted_params
                
                # Add loaded resources
                if loaded_resources:
                    handler_params['resources'] = loaded_resources
                
                # Add any additional kwargs
                handler_params.update(kwargs)
                
                # Get handler signature and filter parameters
                sig = inspect.signature(handler_func)
                filtered_params = {}
                for param_name, param in sig.parameters.items():
                    if param_name in handler_params:
                        filtered_params[param_name] = handler_params[param_name]
                    elif param_name == '_event' and 'event' in handler_params:
                        filtered_params[param_name] = handler_params['event']
                    elif param_name == '_context' and 'context' in handler_params:
                        filtered_params[param_name] = handler_params['context']
                    elif param.kind == inspect.Parameter.VAR_KEYWORD:
                        for k, v in handler_params.items():
                            if k not in filtered_params:
                                filtered_params[k] = v
                
                # Call the handler
                logger.debug(f"{function_name}: Calling handler with parameters: {filtered_params.keys()}")
                result = handler_func(**filtered_params)
                
                # Log response status
                status_code = result.get("statusCode", 0)
                logger.info(f"Request completed: {http_method} {path} -> {function_name} (Status: {status_code})")
                
                return result
                
            except SQLAlchemyError as db_error:
                logger.error(f"{function_name}: Database error: {str(db_error)}")
                return response.api_response(500, message="Database error", error_details=str(db_error))
            
            except Exception as e:
                logger.exception(f"{function_name}: Unexpected error in Lambda handler: {str(e)}")
                return response.api_response(500, message="Internal Server Error", error_details=str(e))
            
            finally:
                if session_created and db_session is not None:
                    try:
                        db_session.close()
                        logger.debug(f"{function_name}: Closed database session")
                    except Exception as e:
                        logger.error(f"{function_name}: Error closing database session: {str(e)}")
            
        return wrapper
    return decorator


def _validate_body(body: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Validate request body against schema."""
    errors = []
    
    for field_name, field_schema in schema.items():
        value = body.get(field_name)
        
        # Check required fields (if value is None and no default)
        if value is None and 'default' not in field_schema:
            if field_schema.get('required', True):
                errors.append(f"Field '{field_name}' is required")
            continue
        
        if value is not None:
            # Type validation
            expected_type = field_schema.get('type')
            if expected_type and not isinstance(value, expected_type):
                errors.append(f"Field '{field_name}' must be of type {expected_type.__name__}")
                continue
            
            # String length validation
            if isinstance(value, str):
                max_length = field_schema.get('max_length')
                if max_length and len(value) > max_length:
                    errors.append(f"Field '{field_name}' exceeds maximum length of {max_length}")
                
                min_length = field_schema.get('min_length', 0)
                if len(value) < min_length:
                    errors.append(f"Field '{field_name}' must be at least {min_length} characters")
            
            # Numeric validation
            if isinstance(value, (int, float)):
                min_val = field_schema.get('min')
                if min_val is not None and value < min_val:
                    errors.append(f"Field '{field_name}' must be at least {min_val}")
                
                max_val = field_schema.get('max')
                if max_val is not None and value > max_val:
                    errors.append(f"Field '{field_name}' must be at most {max_val}")
            
            # Pattern validation for strings
            pattern = field_schema.get('pattern')
            if pattern and isinstance(value, str):
                if not re.match(pattern, value):
                    errors.append(f"Field '{field_name}' does not match required pattern")
    
    if errors:
        return response.api_response(400, 
            message="Validation failed", 
            error_details="Request validation failed", 
            data={"validation_errors": errors}
        )
    
    return None


def _load_resource(db_session, model_class_name: str, resource_id: str):
    """Load a resource by ID using the model class name."""
    # Import models dynamically to avoid circular imports
    from models.claim import Claim
    from models.item import Item
    from models.file import File
    from models.room import Room
    from models.label import Label
    from models.user import User
    
    model_map = {
        'Claim': Claim,
        'Item': Item, 
        'File': File,
        'Room': Room,
        'Label': Label,
        'User': User
    }
    
    model_class = model_map.get(model_class_name)
    if not model_class:
        logger.warning(f"Unknown model class: {model_class_name}")
        return None
    
    try:
        resource_uuid = uuid.UUID(resource_id)
        return db_session.query(model_class).filter(model_class.id == resource_uuid).first()
    except (ValueError, SQLAlchemyError) as e:
        logger.warning(f"Failed to load {model_class_name} with ID {resource_id}: {str(e)}")
        return None


def _check_permissions(user, permissions: Dict[str, Any], extracted_params: Dict[str, str], 
                      loaded_resources: Dict[str, Any], db_session) -> Optional[Dict[str, Any]]:
    """Check permissions using the existing access control system."""
    from utils.access_control import has_permission
    from utils.vocab_enums import ResourceTypeEnum, PermissionAction
    
    resource_type = permissions.get('resource_type')
    action = permissions.get('action') 
    path_param = permissions.get('path_param')
    
    if not all([resource_type, action, path_param]):
        logger.warning(f"Incomplete permission configuration: {permissions}")
        return None
    
    # Get resource ID from extracted params
    resource_id = extracted_params.get(path_param)
    if not resource_id:
        logger.warning(f"Path parameter {path_param} not found for permission check")
        return response.api_response(400, error_details=f"Missing {path_param} parameter")
    
    try:
        resource_uuid = uuid.UUID(resource_id)
        
        # Map string values to enums
        resource_type_enum = getattr(ResourceTypeEnum, resource_type.upper()).value
        action_enum = getattr(PermissionAction, action.upper())
        
        # Use existing access control system exactly as-is
        if not has_permission(
            user=user,
            action=action_enum,
            resource_type=resource_type_enum,
            db=db_session,
            resource_id=resource_uuid
        ):
            return response.api_response(403, 
                error_details=f'You do not have permission to {action.lower()} this {resource_type.lower()}.')
    
    except (ValueError, AttributeError) as e:
        logger.error(f"Permission check failed: {str(e)}")
        return response.api_response(500, error_details="Permission validation error")
    
    return None


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


@s3_operation
def generate_presigned_upload_url(s3_client, bucket_name: str, s3_key: str, content_type: str = None, expiration: int = 3600) -> dict:
    """
    Generate a pre-signed URL for uploading a file to S3 with proper error handling.
    
    Args:
        s3_client: The boto3 S3 client
        bucket_name: S3 bucket name
        s3_key: The S3 object key
        content_type: The content type of the file being uploaded
        expiration: Time in seconds before the URL expires
        
    Returns:
        dict: Contains the pre-signed URL and any additional fields needed for the upload
    """
    try:
        logger.debug(f"Generating presigned PUT URL for bucket: {bucket_name}, key: {s3_key}")
        
        params = {
            'Bucket': bucket_name,
            'Key': s3_key
        }
        
        if content_type:
            params['ContentType'] = content_type
        
        url = s3_client.generate_presigned_url(
            'put_object',
            Params=params,
            ExpiresIn=expiration,
            HttpMethod='PUT'
        )
        
        logger.debug("Presigned PUT URL generated successfully")
        
        return {
            'url': url,
            'method': 'PUT',
            's3_key': s3_key,
            'bucket': bucket_name,
            'expires_in': expiration
        }
    except ClientError as e:
        logger.error(f"Failed to generate presigned PUT URL: {str(e)}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error generating presigned PUT URL: {str(e)}")
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
