"""
Lambda handler for processing files from the SQS queue.

This module is triggered by the SQS queue and handles:
1. Moving the file from the 'pending' location to the final location in S3
2. Storing file metadata in the database
3. Sending a message to the analysis queue
"""
import os
import json
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from utils.logging_utils import get_logger
from utils.lambda_utils import get_s3_client, get_sqs_client
from models.file import FileStatus, File
from database.database import get_db_session

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning("S3_BUCKET_NAME appears to be an SSM parameter path: %s. Using default bucket for local testing.", S3_BUCKET_NAME)
    S3_BUCKET_NAME = "claimvision-dev-bucket"

SQS_ANALYSIS_QUEUE_URL = os.getenv("SQS_ANALYSIS_QUEUE_URL", "")

def compute_file_hash(s3_bucket, s3_key):
    """
    Compute the SHA-256 hash of a file stored in S3.
    
    Args:
        s3_bucket (str): S3 bucket name
        s3_key (str): S3 object key
        
    Returns:
        tuple: (SHA-256 hash of the file, file size in bytes, content type)
    """
    try:
        logger.info("Computing hash for file in S3: %s/%s", s3_bucket, s3_key)
        s3 = get_s3_client()
        response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        file_data = response['Body'].read()
        file_hash = sha256(file_data).hexdigest()
        
        # Extract file size and content type
        file_size = len(file_data)
        content_type = response.get('ContentType', '')
        
        logger.info("Computed file hash: %s, size: %s bytes, content type: %s", 
                   file_hash, file_size, content_type)
        return file_hash, file_size, content_type
    except Exception as e:
        logger.error("Error computing file hash: %s", str(e))
        raise

def send_to_analysis_queue(file_id, s3_key, file_name, household_id, claim_id) -> str:
    """
    Sends a message to the analysis queue.
    
    Args:
        file_id (UUID): The ID of the file
        s3_key (str): The S3 key where the file is stored
        file_name (str): The name of the file
        household_id (UUID): The ID of the household
        claim_id (UUID): The ID of the claim
        
    Returns:
        str: The message ID if successful, or a dummy ID if queue URL is not set
    """
    # Prepare the message body
    message_body = {
        "file_id": str(file_id),
        "s3_key": s3_key,
        "file_name": file_name,
        "household_id": str(household_id),
        "claim_id": str(claim_id),
    }
    
    # Check if queue URL is set
    if not SQS_ANALYSIS_QUEUE_URL:
        logger.warning("SQS_ANALYSIS_QUEUE_URL environment variable is not set, skipping analysis queue")
        return "dummy-message-id-for-testing"
    
    # Send the message
    sqs = get_sqs_client()
    response = sqs.send_message(
        QueueUrl=SQS_ANALYSIS_QUEUE_URL,
        MessageBody=json.dumps(message_body)
    )
    return response['MessageId']

def lambda_handler(event, _context):
    """
    Processes file uploads from the SQS queue.
    
    Args:
        event (dict): SQS event containing file data and metadata
        _context (dict): Lambda execution context
        
    Returns:
        dict: Processing status
    """
    logger.info("Processing file upload from SQS")
    
    # Get database session
    db_session = get_db_session()
    
    try:
        # Process each record from SQS
        for record in event.get('Records', []):
            try:
                # Parse message body
                message_body = json.loads(record['body'])
                
                # Extract file information
                file_id = uuid.UUID(message_body['file_id'])
                user_id = uuid.UUID(message_body['user_id'])
                household_id = uuid.UUID(message_body['household_id'])
                file_name = message_body['file_name']
                claim_id = uuid.UUID(message_body['claim_id'])
                room_id = uuid.UUID(message_body['room_id']) if message_body.get('room_id') else None
                
                # Get S3 information
                source_s3_key = message_body['s3_key']
                source_s3_bucket = message_body['s3_bucket']
                
                # Construct final S3 key
                target_s3_key = f"ClaimVision/{claim_id}/{file_id}/{file_name}"
                logger.info("Moving file from %s to %s", source_s3_key, target_s3_key)
                
                # Move file from pending location to final location
                try:
                    s3 = get_s3_client()
                    
                    # Copy the object to the new location
                    s3.copy_object(
                        CopySource={'Bucket': source_s3_bucket, 'Key': source_s3_key},
                        Bucket=S3_BUCKET_NAME,
                        Key=target_s3_key
                    )
                    
                    # Delete the original object (from pending location)
                    s3.delete_object(
                        Bucket=source_s3_bucket,
                        Key=source_s3_key
                    )
                    
                    s3_url = f"s3://{S3_BUCKET_NAME}/{target_s3_key}"
                    logger.info("File %s moved to final location: %s", file_id, s3_url)
                except Exception as e:
                    logger.error("Failed to move file %s in S3: %s", file_id, str(e))
                    return {
                        "statusCode": 500,
                        "body": json.dumps({
                            "error": f"Error moving file in S3: {str(e)}"
                        })
                    }
                    
                # Compute file hash
                file_hash, file_size, content_type = compute_file_hash(S3_BUCKET_NAME, target_s3_key)
                
                # Store metadata in database
                try:
                    new_file = File(
                        id=file_id,
                        uploaded_by=user_id,
                        household_id=household_id,
                        file_name=file_name,
                        s3_key=target_s3_key,
                        claim_id=claim_id,
                        room_id=room_id,
                        status=FileStatus.UPLOADED,
                        file_hash=file_hash,
                        file_size=file_size,
                        content_type=content_type,
                        file_metadata={},  # Initialize with empty metadata
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db_session.add(new_file)
                    db_session.commit()
                    logger.info("File %s metadata stored in database", file_id)
                except Exception as e:
                    logger.error("Failed to store file %s metadata in database: %s", file_id, str(e))
                    return {
                        "statusCode": 500,
                        "body": json.dumps({
                            "error": f"Error storing file metadata in database: {str(e)}"
                        })
                    }
                    
                # Send to analysis queue
                warnings = []
                try:
                    message_id = send_to_analysis_queue(file_id, target_s3_key, file_name, household_id, claim_id)
                    logger.info("File %s queued for analysis with message ID %s", file_id, message_id)
                except Exception as e:
                    warning_msg = f"Failed to queue file {file_id} for analysis: {str(e)}"
                    logger.error(warning_msg)
                    warnings.append(warning_msg)
                    # We don't return an error here because the file is already uploaded and stored
                
            except Exception as e:
                logger.error("Failed to process SQS message: %s", str(e))
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": f"Error processing SQS message: {str(e)}"
                    })
                }
        
        # Return success response
        response_body = {
            "message": "File processing complete"
        }
        if warnings:
            response_body["warnings"] = warnings
            
        return {
            "statusCode": 200,
            "body": json.dumps(response_body)
        }
    finally:
        # Always close the database session
        db_session.close()
