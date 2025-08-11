#TODO: Delete this file once I confirm it's not used
"""
Lambda handler for file uploads to the ClaimVision system.

This module handles the initial receipt of file uploads and sends them to an SQS queue
for asynchronous processing. This makes the upload process non-blocking for users.
"""
import os
import uuid
import json
import base64
from datetime import datetime, timezone
from hashlib import sha256
import time
import re

from botocore.exceptions import ClientError

from utils.logging_utils import get_logger
from utils.lambda_utils import get_sqs_client, get_s3_client, enhanced_lambda_handler
from utils.response import api_response
from models.file import File
from models.claim import Claim
from database.database import get_db_session as db_get_session
from sqlalchemy.exc import SQLAlchemyError
from models.room import Room

logger = get_logger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB file size limit

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
    S3_BUCKET_NAME = "claimvision-dev-bucket"

# For backward compatibility with tests
def get_db_session():
    """
    Wrapper function for database session creation to maintain backward compatibility with tests.
    
    Returns:
        Session: SQLAlchemy database session
    """
    return db_get_session()

def upload_to_s3(file_data, file_name, claim_id, file_id):
    """
    Upload a file to S3 bucket.
    
    Args:
        file_data (str): Base64-encoded file data
        file_name (str): Name of the file
        claim_id (str): UUID of the claim
        file_id (str): UUID for the file
        
    Returns:
        tuple: (success, s3_key or error_message)
    """
    try:
        logger.info(f"Uploading file {file_name} to S3")
        s3 = get_s3_client()
        
        # Decode the base64 data
        decoded_data = base64.b64decode(file_data)
        
        # Generate S3 key using claim_id and file_id
        s3_key = f"pending/{claim_id}/{file_id}/{file_name}"
        
        # Upload to S3
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=decoded_data,
            ContentType=f"image/{file_name.split('.')[-1].lower()}" if "." in file_name else "application/octet-stream"
        )
        
        logger.info(f"Successfully uploaded file to S3: {s3_key}")
        return True, s3_key
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        return False, str(e)

def queue_file_for_processing(file_name, claim_id, s3_key, room_id=None, household_id=None, user=None):
    """
    Queue a file for asynchronous processing via SQS.
    
    Args:
        file_name (str): Name of the file to process
        claim_id (str): UUID of the claim this file belongs to
        s3_key (str): S3 object key where the file is stored
        room_id (str, optional): UUID of the room this file belongs to
        household_id (str, optional): UUID of the household this file belongs to
        user (User, optional): Authenticated user object from the standard_lambda_handler
        
    Returns:
        str: Message ID from SQS if successful
        
    Raises:
        ValueError: If SQS queue URL is not set
        ConnectionError: If SQS message sending fails
    """
    # Prepare message payload
    logger.info(f"Preparing SQS message for file: {file_name}")
    # Generate a unique file ID
    file_id = s3_key.split('/')[-2]  # Extract file_id from S3 key
    
    # Get user ID from the authenticated user
    user_id = str(user.id) if user and hasattr(user, 'id') else None
    if not user_id:
        logger.error("No authenticated user provided to queue_file_for_processing")
        raise ValueError("User ID is required to queue file for processing")
    
    message_body = {
        "file_id": file_id,
        "user_id": user_id,
        "file_name": file_name,
        "s3_key": s3_key,
        "s3_bucket": S3_BUCKET_NAME,
        "claim_id": claim_id,
        "upload_time": datetime.now(timezone.utc).isoformat()
    }
    
    if room_id:
        message_body["room_id"] = room_id
        
    if household_id:
        message_body["household_id"] = household_id
    
    # Get SQS client
    logger.info("Getting SQS client")
    try:
        sqs = get_sqs_client()
        logger.info("SQS client created successfully")
    except Exception as e:
        logger.error(f"Failed to create SQS client: {str(e)}")
        raise ConnectionError(f"Failed to create SQS client: {str(e)}")
        
    sqs_upload_queue_url = os.getenv("SQS_UPLOAD_QUEUE_URL")
    logger.info(f"SQS queue URL: {sqs_upload_queue_url}")
    
    if not sqs_upload_queue_url:
        logger.error("SQS_UPLOAD_QUEUE_URL environment variable is not set")
        raise ValueError("SQS_UPLOAD_QUEUE_URL environment variable is not set")
    
    try:
        logger.info(f"Sending message to SQS for file: {file_name}")
        # Check if we're running in a VPC
        lambda_vpc_config = os.getenv("AWS_LAMBDA_VPC_SUBNETS")
        logger.info(f"Lambda VPC config: {lambda_vpc_config}")
        
        # Create a copy of the message body for logging
        log_message_body = message_body.copy()
        
        # Set a timeout for the SQS operation
        start_time = time.time()
        sqs_response = sqs.send_message(
            QueueUrl=sqs_upload_queue_url,
            MessageBody=json.dumps(message_body)
        )
        elapsed_time = time.time() - start_time
        logger.info(f"SQS send_message took {elapsed_time:.2f} seconds")
        logger.info(f"SQS response: {sqs_response}")
        logger.info(f"SQS message body: {json.dumps(log_message_body)}")
        return sqs_response["MessageId"]
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"AWS ClientError sending message to SQS: Code={error_code}, Message={error_message}")
        raise ConnectionError(f"Failed to send message to SQS: {error_message}")
    except Exception as e:
        logger.error(f"Error sending message to SQS: {str(e)}")
        raise ConnectionError(f"Failed to send message to SQS: {str(e)}")

def parse_multipart_form_data(event):
    """
    Parse multipart form data from API Gateway event.
    
    Args:
        event (dict): API Gateway event
        
    Returns:
        dict: Parsed form data with files and fields
    """
    try:
        logger.info("Parsing multipart form data")
        
        # Get content type and boundary
        content_type = event.get('headers', {}).get('content-type', '')
        if not content_type or 'multipart/form-data' not in content_type:
            logger.warning(f"Invalid content type for multipart: {content_type}")
            return None
            
        # Extract boundary
        boundary_match = re.search(r'boundary=([^;]+)', content_type)
        if not boundary_match:
            logger.warning("No boundary found in content type")
            return None
            
        boundary = boundary_match.group(1)
        logger.info(f"Multipart boundary: {boundary}")
        
        # Get request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            logger.info("Decoding base64 encoded body")
            body = base64.b64decode(body).decode('utf-8')
        
        # Log a sample of the body for debugging
        logger.info(f"Body sample (first 200 chars): {body[:200]}")
        
        # Split body by boundary
        boundary = f'--{boundary}'
        parts = body.split(boundary)
        
        # Remove first and last parts (they are empty or contain closing boundary)
        parts = [p for p in parts if p and p.strip() and p.strip() != '--']
        
        logger.info(f"Found {len(parts)} parts in multipart form data")
        
        # Parse each part
        form_data = {'files': [], 'fields': {}}
        
        for part in parts:
            # Split headers and content
            headers_content = part.strip().split('\r\n\r\n', 1)
            if len(headers_content) != 2:
                logger.warning(f"Invalid part format: {part[:100]}")
                continue
                
            headers, content = headers_content
            
            # Parse headers
            header_lines = headers.split('\r\n')
            header_dict = {}
            
            for line in header_lines:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    header_dict[key.lower()] = value
            
            # Check if this is a file or a field
            content_disposition = header_dict.get('content-disposition', '')
            name_match = re.search(r'name="([^"]+)"', content_disposition)
            
            if not name_match:
                logger.warning(f"No name found in content disposition: {content_disposition}")
                continue
                
            field_name = name_match.group(1)
            logger.info(f"Found field name: {field_name}")
            
            # Check if this is a file
            filename_match = re.search(r'filename="([^"]+)"', content_disposition)
            
            if filename_match:
                # This is a file
                filename = filename_match.group(1)
                content_type = header_dict.get('content-type', 'application/octet-stream')
                
                # Base64 encode the file content for consistent handling
                file_data = base64.b64encode(content.encode('latin1')).decode('ascii')
                
                form_data['files'].append({
                    'file_name': filename,
                    'file_data': file_data,
                    'content_type': content_type
                })
                logger.info(f"Parsed file: {filename} ({content_type})")
            else:
                # This is a form field
                form_data['fields'][field_name] = content
                logger.info(f"Parsed field: {field_name}")
        
        logger.info(f"Parsed {len(form_data['files'])} files and {len(form_data['fields'])} fields")
        return form_data
    except Exception as e:
        logger.error(f"Error parsing multipart form data: {str(e)}")
        logger.exception("Full exception details:")
        return None

@enhanced_lambda_handler(
    requires_auth=True,
    path_params=["claim_id"],
    auto_load_resources={"claim_id": "Claim"},
    permissions={"resource_type": "CLAIM", "action": "WRITE", "path_param": "claim_id"}
)
def lambda_handler(event, context, db_session, user, path_params, resources, body=None) -> dict:
    """
    Handles receiving file uploads and sending them to SQS for processing.
    Supports both JSON with base64-encoded files and multipart form data.
    
    Args:
        event (dict): API Gateway event containing authentication details and file data
        context (dict): Lambda execution context (unused)
        db_session (Session): SQLAlchemy session
        user (User): Authenticated user object
        path_params (dict): Path parameters from API Gateway event
        resources (dict): Loaded resources (Claim object)
        body (dict, optional): Request body (parsed JSON or multipart form data)
        
    Returns:
        dict: API response containing upload request status
    """
    logger.info("Starting file upload process")
    
    # Enhanced logging for debugging
    logger.info(f"Lambda handler called with user: {user}")
    
    # Check if this is a multipart form data request
    content_type = event.get('headers', {}).get('content-type', '')
    logger.info(f"Content-Type: {content_type}")
    
    # Use decorator-provided path params/resources and validate claim
    claim_id = path_params["claim_id"]
    claim = resources.get("claim")
    logger.info(f"Found claim_id in path parameters: {claim_id}")
    if hasattr(claim, "deleted") and getattr(claim, "deleted") is True:
        logger.warning("Claim is deleted")
        return api_response(404, error_details='Claim not found.')
    
    if content_type and 'multipart/form-data' in content_type:
        logger.info("Processing multipart form data request")
        form_data = parse_multipart_form_data(event)
        
        if not form_data:
            logger.error("Failed to parse multipart form data")
            return api_response(400, error_details='Failed to parse multipart form data')
            
        # Extract form fields and files
        files = form_data.get('files', [])
        fields = form_data.get('fields', {})
        
        # Create body structure similar to JSON request
        body = {
            'files': files,
            'room_id': fields.get('room_id')
        }
        
        logger.info(f"Parsed {len(files)} files from multipart form data")
        
        # If no files were found but we know this is a multipart request,
        # it might be due to a change in how the frontend sends files
        if len(files) == 0:
            logger.warning("No files found in multipart form data, checking for alternative format")
            # Log all field names to help debug
            logger.info(f"Available fields: {list(fields.keys())}")
    else:
        # Process as JSON request with base64-encoded files
        logger.info("Processing JSON request with base64-encoded files")
        
        # Parse the body from the event
        if body is None:
            if 'body' in event:
                try:
                    if isinstance(event['body'], str):
                        body = json.loads(event['body'])
                    else:
                        body = event['body']
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON body")
                    return api_response(400, error_details='Invalid JSON body')
            else:
                logger.error("No body in request")
                return api_response(400, error_details='Request body is required')
    
    # Log only the structure of the request body, not the actual file data
    body_structure = {}
    if body:
        body_structure = {k: v if k != 'files' else f"[{len(v)} files]" for k, v in body.items()}
    logger.info(f"Request body structure: {body_structure}")
    
    # Extract household ID from authenticated user
    household_id = user.household_id
    logger.info(f"User household ID: {household_id}")
    
    # Use loaded claim and derive UUID
    claim_uuid = claim.id
    logger.info(f"Valid claim ID: {claim_uuid}")
    
    # Check for the room if provided
    if body.get("room_id"):
        try:
            room_uuid = uuid.UUID(body["room_id"])
            room = db_session.query(Room).filter_by(id=room_uuid, claim_id=claim_uuid).first()
            if not room:
                return api_response(404, error_details='Room not found.')
        except (ValueError, SQLAlchemyError) as e:
            if isinstance(e, ValueError):
                return api_response(400, error_details='Invalid room ID format. Expected UUID.')
            else:
                logger.error("Database error when checking room: %s", str(e))
                return api_response(500, error_details=f'Database Error: {str(e)}')
    
    # Check for duplicate content
    uploaded_files = []
    failed_files = []
    
    # Process each file in the request
    for file_obj in files:
        file_name = file_obj.get("file_name", "")
        file_data = file_obj.get("file_data", "")
        
        logger.info(f"Processing file: {file_name}")
        
        # Validate file name
        if not file_name:
            logger.info("Missing file name")
            failed_files.append({"file_name": "unknown", "reason": "Missing file name."})
            continue
        
        # Validate file data
        if not file_data:
            logger.info(f"Missing file data for file: {file_name}")
            failed_files.append({"file_name": file_name, "reason": "Missing file data."})
            continue
            
        # Check file extension
        file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
        if not file_extension:
            logger.info(f"Missing file extension for file: {file_name}")
            failed_files.append({"file_name": file_name, "reason": "Missing file extension."})
            continue
            
        # Validate file type (basic check)
        allowed_extensions = ["jpg", "jpeg", "png", "pdf"]
        if file_extension not in allowed_extensions:
            logger.info(f"Invalid file extension: {file_extension} for file: {file_name}. Allowed extensions: {allowed_extensions}")
            failed_files.append({
                "file_name": file_name, 
                "reason": f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}."
            })
            continue
            
        # Validate base64 data
        try:
            logger.info(f"Attempting to decode base64 data for file: {file_name}")
            decoded_data = base64.b64decode(file_data)
            logger.info(f"Successfully decoded base64 data for file: {file_name}")
            
            if not decoded_data:
                logger.info(f"Empty file content for file: {file_name}")
                failed_files.append({"file_name": file_name, "reason": "Empty file content."})
                continue
                
            # Check file size
            file_size = len(decoded_data)
            logger.info(f"File size: {file_size} bytes for file: {file_name}")
            
            if file_size > MAX_FILE_SIZE:
                logger.info(f"File exceeds maximum size: {file_size} > {MAX_FILE_SIZE} bytes for file: {file_name}")
                failed_files.append({
                    "file_name": file_name, 
                    "reason": f"File exceeds maximum size of {MAX_FILE_SIZE/1024/1024}MB."
                })
                continue
                
            # Generate content hash for duplicate detection
            file_hash = sha256(decoded_data).hexdigest()
            logger.info(f"Generated file hash: {file_hash[:10]}... for file: {file_name}")
            
            # Check for duplicate content in this batch
            duplicate_in_batch = any(f.get("file_hash") == file_hash for f in uploaded_files)
            if duplicate_in_batch:
                logger.info(f"Duplicate content detected in current batch for file: {file_name}")
                failed_files.append({"file_name": file_name, "reason": "Duplicate content detected."})
                continue
            
            # Check for existing files with the same content
            existing_file = db_session.query(File).filter_by(
                file_hash=file_hash, 
                claim_id=claim_uuid
            ).first()
            logger.info(f"Existing file: {existing_file}")
            if existing_file:
                failed_files.append({"file_name": file_name, "reason": "Duplicate content detected."})
                continue
                
        except (ValueError, TypeError, base64.binascii.Error) as e:
            logger.error("Error processing file %s: %s", file_name, str(e))
            failed_files.append({"file_name": file_name, "reason": "Invalid file data format."})
            continue
            
        # Upload the file to S3
        file_id = str(uuid.uuid4())
        upload_result, s3_key_or_error = upload_to_s3(file_data, file_name, claim_id, file_id)
        if not upload_result:
            logger.error(f"Failed to upload file to S3: {s3_key_or_error}")
            failed_files.append({"file_name": file_name, "reason": "Failed to upload to S3."})
            continue
        
        # Queue the file for processing
        try:
            logger.info("Queueing file %s for processing", file_name)            
            # Queue the file for processing via SQS
            message_id = queue_file_for_processing(
                file_name=file_name,
                claim_id=claim_id,
                s3_key=s3_key_or_error,
                room_id=room_id,
                household_id=str(household_id),
                user=user
            )
            
            logger.info("File %s queued for processing with message ID %s", file_name, message_id)
            
            # Create a response object for this file
            file_response = {
                "file_name": file_name,
                "status": "QUEUED",
                "file_hash": file_hash
            }
                
            uploaded_files.append(file_response)
        except (ValueError, ConnectionError) as e:
            logger.error("Failed to queue file %s for processing: %s", file_name, str(e))
            failed_files.append({"file_name": file_name, "reason": "Failed to queue for processing."})
            # Remove from uploaded files if it failed to queue
            uploaded_files = [f for f in uploaded_files if f.get("file_hash") != file_hash]
    
    if not uploaded_files and failed_files:
        # Return 500 if SQS failures caused all uploads to fail
        if any(f["reason"] == "Failed to queue for processing." for f in failed_files):
            return api_response(500, error_details='Internal Server Error', data={"files_failed": failed_files})
        elif any(f["reason"] == "Duplicate content detected." for f in failed_files):
            return api_response(409, error_details='Duplicate content detected', data={"files_failed": failed_files})
        primary_reason = failed_files[0]["reason"] if failed_files else "All file uploads failed."
        return api_response(400, error_details=primary_reason, data={"files_failed": failed_files})
    
    return api_response(
        207 if failed_files else 200,
        success_message="Files queued for processing successfully" if not failed_files else "Some files queued for processing", 
        data={"files_queued": uploaded_files, "files_failed": failed_files} if failed_files else {"files_queued": uploaded_files}
    )