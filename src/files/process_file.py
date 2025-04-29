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
from utils.logging_utils import get_logger, log_structured, LogLevel
from utils.lambda_utils import get_s3_client, get_sqs_client
from models.file import FileStatus, File
from database.database import get_db_session
from models.user import User
from models.group_membership import GroupMembership
from models.claim import Claim

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
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
        log_structured(logger, LogLevel.INFO, "Computing hash for file in S3", s3_bucket=s3_bucket, s3_key=s3_key)
        s3 = get_s3_client()
        response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        file_data = response['Body'].read()
        file_hash = sha256(file_data).hexdigest()
        
        # Extract file size and content type
        file_size = len(file_data)
        content_type = response.get('ContentType', '')
        
        log_structured(logger, LogLevel.INFO, "Computed file hash", file_hash=file_hash, file_size=file_size, content_type=content_type)
        return file_hash, file_size, content_type
    except Exception as e:
        log_structured(logger, LogLevel.ERROR, "Error computing file hash", error=str(e))
        raise

def send_to_analysis_queue(file_id, s3_key, file_name, group_id, claim_id) -> str:
    """
    Sends a message to the analysis queue.
    
    Args:
        file_id (UUID): The ID of the file
        s3_key (str): The S3 key where the file is stored
        file_name (str): The name of the file
        group_id (UUID): The ID of the group
        claim_id (UUID): The ID of the claim
        
    Returns:
        str: The message ID if successful, or a dummy ID if queue URL is not set
    """
    # Prepare the message body
    message_body = {
        "file_id": str(file_id),
        "s3_key": s3_key,
        "file_name": file_name,
        "group_id": str(group_id),
        "claim_id": str(claim_id),
    }
    
    # Check if queue URL is set
    if not SQS_ANALYSIS_QUEUE_URL:
        log_structured(logger, LogLevel.WARNING, "SQS_ANALYSIS_QUEUE_URL environment variable is not set, skipping analysis queue")
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
    log_structured(logger, LogLevel.INFO, "Processing file upload from SQS")
    
    # Get database session
    db_session = get_db_session()
    
    try:
        # Process each record from SQS
        for record in event.get('Records', []):
            try:
                # Parse message body
                message_body = json.loads(record['body'])
                
                # Log the full message body in dev environments
                log_structured(logger, LogLevel.DEBUG, "Processing SQS message", message_body=message_body)
                
                # Extract file information
                file_id = uuid.UUID(message_body['file_id'])
                user_id = uuid.UUID(message_body['user_id'])
                file_name = message_body['file_name']
                claim_id = uuid.UUID(message_body['claim_id'])
                room_id = uuid.UUID(message_body['room_id']) if message_body.get('room_id') else None
                
                # Get group_id if available, otherwise try to get it from the user or claim
                group_id = None
                if message_body.get('group_id'):
                    group_id = uuid.UUID(message_body['group_id'])
                else:
                    # Try to get group_id from user
                    try:
                        with get_db_session() as user_db_session:
                            # First try to get from user's membership
                            user = user_db_session.query(User).filter_by(id=user_id).first()
                            if user:
                                membership = user_db_session.query(GroupMembership).filter_by(
                                    user_id=user.id
                                ).first()
                                
                                if membership and membership.group_id:
                                    group_id = membership.group_id
                                    log_structured(logger, LogLevel.INFO, "Using group_id from user membership", 
                                                  group_id=str(group_id), user_id=str(user_id))
                            
                            # If still not found, try to get from claim
                            if not group_id:
                                claim = user_db_session.query(Claim).filter_by(id=claim_id).first()
                                if claim and claim.group_id:
                                    group_id = claim.group_id
                                    log_structured(logger, LogLevel.INFO, "Using group_id from claim", 
                                                  group_id=str(group_id), claim_id=str(claim_id))
                    except Exception as e:
                        log_structured(logger, LogLevel.WARNING, "Error getting group_id", error=str(e))
                
                # Ensure we have a group_id before proceeding
                if not group_id:
                    log_structured(logger, LogLevel.ERROR, "Could not determine group_id for file", file_id=str(file_id))
                    continue
                
                # Get S3 information
                source_s3_key = message_body['s3_key']
                source_s3_bucket = message_body['s3_bucket']
                
                # Construct final S3 key
                target_s3_key = f"ClaimVision/{claim_id}/{file_id}/{file_name}"
                log_structured(logger, LogLevel.INFO, "Moving file from pending to final location", 
                              source_key=source_s3_key, target_key=target_s3_key)
                
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
                    log_structured(logger, LogLevel.INFO, "File moved successfully", s3_url=s3_url)
                    
                    # Update file record in database
                    file_record = db_session.query(File).filter(File.id == file_id).first()
                    if file_record:
                        # Update S3 key and status
                        file_record.s3_key = target_s3_key
                        file_record.status = FileStatus.PROCESSED
                        file_record.updated_at = datetime.now(timezone.utc)
                        
                        # Compute file hash if not already set
                        if not file_record.file_hash or file_record.file_hash.startswith('temp-'):
                            try:
                                file_hash, file_size, content_type = compute_file_hash(S3_BUCKET_NAME, target_s3_key)
                                file_record.file_hash = file_hash
                                
                                # Update file size and content type if they were not set correctly
                                if not file_record.file_size or file_record.file_size == 0:
                                    file_record.file_size = file_size
                                    
                                if not file_record.content_type:
                                    file_record.content_type = content_type
                                    
                                log_structured(logger, LogLevel.INFO, "Updated file hash and metadata", 
                                              file_id=str(file_id), file_hash=file_hash)
                            except Exception as hash_error:
                                log_structured(logger, LogLevel.WARNING, "Error computing file hash", 
                                              error=str(hash_error), file_id=str(file_id))
                        
                        db_session.commit()
                        log_structured(logger, LogLevel.INFO, "File record updated", file_id=str(file_id))
                        
                        # Send to analysis queue if configured
                        if SQS_ANALYSIS_QUEUE_URL:
                            message_id = send_to_analysis_queue(
                                file_id, target_s3_key, file_name, group_id, claim_id
                            )
                            log_structured(logger, LogLevel.INFO, "File sent to analysis queue", 
                                          message_id=message_id, file_id=str(file_id))
                    else:
                        log_structured(logger, LogLevel.WARNING, "File record not found in database", file_id=str(file_id))
                        
                except Exception as s3_error:
                    log_structured(logger, LogLevel.ERROR, "Error moving file in S3", 
                                  error=str(s3_error), source_key=source_s3_key)
                    continue
                    
            except Exception as record_error:
                log_structured(logger, LogLevel.ERROR, "Error processing SQS record", error=str(record_error))
                continue
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Processed {len(event.get('Records', []))} files"
            })
        }
    except Exception as e:
        log_structured(logger, LogLevel.ERROR, "Error in lambda_handler", error=str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error processing SQS event",
                "error": str(e)
            })
        }
    finally:
        # Always close the database session
        db_session.close()
