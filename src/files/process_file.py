"""
Lambda handler for processing files from the processing queue.

This module handles moving files from the pending directory to their final location,
updating file metadata in the database, and sending notifications.
"""
import os
import json
import boto3
import time
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from database.database import get_db_session
from models.file import File, FileStatus
from models.claim import Claim
from models.group_membership import GroupMembership
from models.user import User
from utils.logging_utils import get_logger, log_structured, LogLevel
from utils.lambda_utils import get_s3_client, get_sqs_client
from batch.batch_tracker import file_processed, file_analysis_queued, file_uploaded
from misc.websocket_sender import notify_file_processed

logger = get_logger(__name__)

# Get environment variables
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
PROCESSING_QUEUE_URL = os.environ.get('PROCESSING_QUEUE_URL')
ANALYSIS_QUEUE_URL = os.environ.get('ANALYSIS_QUEUE_URL')
OUTBOUND_QUEUE_URL = os.environ.get('OUTBOUND_QUEUE_URL')

# Get the actual bucket name, not the SSM parameter path
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning("S3_BUCKET_NAME appears to be an SSM parameter path: %s. Using default bucket for local testing.", S3_BUCKET_NAME)
    S3_BUCKET_NAME = "claimvision-dev-bucket"

SQS_ANALYSIS_QUEUE_URL = ANALYSIS_QUEUE_URL

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
        
        # Get S3 client
        s3 = get_s3_client()
        
        # Get file metadata
        response = s3.head_object(Bucket=s3_bucket, Key=s3_key)
        file_size = response.get('ContentLength', 0)
        content_type = response.get('ContentType', 'application/octet-stream')
        
        # Get file content and compute hash
        file_obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        file_content = file_obj['Body'].read()
        
        # Compute SHA-256 hash
        file_hash = sha256(file_content).hexdigest()
        
        log_structured(logger, LogLevel.INFO, "Computed file hash", 
                      s3_key=s3_key, file_size=file_size, hash=file_hash)
        
        return file_hash, file_size, content_type
    except Exception as e:
        log_structured(logger, LogLevel.ERROR, "Error computing file hash", 
                      error=str(e), s3_bucket=s3_bucket, s3_key=s3_key)
        return None, 0, 'application/octet-stream'


def send_to_analysis_queue(file_id, s3_key, file_name, group_id, claim_id):
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
    if not SQS_ANALYSIS_QUEUE_URL:
        log_structured(logger, LogLevel.WARNING, "SQS_ANALYSIS_QUEUE_URL not set, skipping analysis queue")
        return str(uuid.uuid4())  # Return a dummy message ID
    
    try:
        # Get SQS client
        sqs = get_sqs_client()
        
        # Prepare message
        message = {
            'file_id': str(file_id),
            's3_key': s3_key,
            'file_name': file_name,
            'group_id': str(group_id) if group_id else None,
            'claim_id': str(claim_id) if claim_id else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Send message to analysis queue
        response = sqs.send_message(
            QueueUrl=SQS_ANALYSIS_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        
        message_id = response.get('MessageId')
        log_structured(logger, LogLevel.INFO, "Sent file to analysis queue", 
                      file_id=str(file_id), message_id=message_id)
        
        return message_id
    except Exception as e:
        log_structured(logger, LogLevel.ERROR, "Error sending file to analysis queue", 
                      error=str(e), file_id=str(file_id))
        return str(uuid.uuid4())  # Return a dummy message ID


def lambda_handler(event, _context):
    """
    Processes file uploads from the SQS queue.
    
    Args:
        event (dict): SQS event containing file data and metadata
        _context (dict): Lambda execution context
        
    Returns:
        dict: Processing status
    """
    db_session = get_db_session()
    
    try:
        log_structured(logger, LogLevel.INFO, "Processing SQS event", records_count=len(event.get('Records', [])))
        
        for record in event.get('Records', []):
            try:
                # Parse the message body
                message_body = json.loads(record['body'])
                log_structured(logger, LogLevel.INFO, "Processing SQS message", message_body=message_body)
                
                # Extract file information
                file_id = message_body.get('file_id')
                s3_key = message_body.get('s3_key')
                file_name = message_body.get('file_name')
                claim_id = message_body.get('claim_id')
                user_id = message_body.get('user_id')
                group_id = message_body.get('group_id')
                batch_id = message_body.get('batch_id')
                
                # Skip if missing required information
                if not file_id or not s3_key or not file_name:
                    log_structured(logger, LogLevel.ERROR, "Missing required file information", 
                                  file_id=file_id, s3_key=s3_key, file_name=file_name)
                    continue
                
                # If batch_id is missing, log error but continue processing
                if not batch_id:
                    log_structured(logger, LogLevel.ERROR, "No batch_id found in message, batch tracking disabled for this file", 
                                  file_id=file_id)
                    # We'll still process the file but won't send batch tracking events
                try:
                    # Get the group ID for the user and claim
                    if user_id and claim_id:
                        user = db_session.query(User).filter(User.id == user_id).first()
                        if user:
                            # Find the group membership for this user
                            membership = db_session.query(GroupMembership).filter(
                                GroupMembership.user_id == user_id
                            ).first()
                            
                            if membership:
                                group_id = membership.group_id
                                log_structured(logger, LogLevel.INFO, "Found group ID for user", 
                                              user_id=user_id, group_id=str(group_id))
                            
                            # Verify the claim belongs to the user's group
                            claim = db_session.query(Claim).filter(
                                Claim.id == claim_id,
                                Claim.group_id == group_id
                            ).first()
                            
                            if not claim:
                                log_structured(logger, LogLevel.WARNING, "Claim not found or does not belong to user's group", 
                                              claim_id=claim_id, user_id=user_id, group_id=str(group_id) if group_id else None)
                                continue
                    
                    # Send batch tracking event for file upload
                    if batch_id:
                        file_uploaded(
                            batch_id=batch_id,
                            file_id=file_id,
                            file_name=file_name or "Unknown",
                            user_id=user_id,
                            claim_id=claim_id
                        )
                    
                    # Construct target S3 key (move from 'pending/' to appropriate location)
                    target_s3_key = s3_key.replace('pending/', '', 1)
                    
                    # Move the file in S3
                    s3 = get_s3_client()
                    s3.copy_object(
                        CopySource={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
                        Bucket=S3_BUCKET_NAME,
                        Key=target_s3_key
                    )
                    
                    # Delete the source file
                    s3.delete_object(
                        Bucket=S3_BUCKET_NAME,
                        Key=s3_key
                    )
                    
                    log_structured(logger, LogLevel.INFO, "Moved file in S3", 
                                  source_key=s3_key, target_key=target_s3_key)
                    
                    # Update file record in database
                    file_record = db_session.query(File).filter(File.id == file_id).first()
                    
                    if file_record:
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
                            
                            # Send batch tracking event for file analysis queued
                            if batch_id:
                                file_analysis_queued(
                                    batch_id=batch_id,
                                    file_id=file_id,
                                    message_id=message_id,
                                    user_id=user_id,
                                    claim_id=claim_id
                                )
                                log_structured(logger, LogLevel.INFO, "Batch tracking event sent for file analysis queued", 
                                              file_id=str(file_id), batch_id=batch_id)
                        
                        # Send WebSocket notification if OUTBOUND_QUEUE_URL is configured
                        try:
                            if os.environ.get('OUTBOUND_QUEUE_URL'):
                                # Prepare file info for notification
                                file_info = {
                                    'id': str(file_id),
                                    'name': file_name,
                                    'size': file_record.file_size,
                                    'contentType': file_record.content_type,
                                    'status': file_record.status.value,
                                    's3Key': target_s3_key
                                }
                                
                                # Send notification
                                notify_file_processed(
                                    file_id=str(file_id),
                                    claim_id=str(claim_id),
                                    user_id=str(user_id),
                                    file_info=file_info
                                )
                                log_structured(logger, LogLevel.INFO, "WebSocket notification sent for processed file", 
                                              file_id=str(file_id), user_id=str(user_id))
                                
                                # Send batch tracking event for file processed
                                if batch_id:
                                    file_processed(
                                        batch_id=batch_id,
                                        file_id=file_id,
                                        success=True,
                                        file_url=f"s3://{S3_BUCKET_NAME}/{target_s3_key}",
                                        user_id=user_id,
                                        claim_id=claim_id
                                    )
                                    log_structured(logger, LogLevel.INFO, "Batch tracking event sent for processed file", 
                                                  file_id=str(file_id), batch_id=batch_id)
                        except Exception as ws_error:
                            log_structured(logger, LogLevel.WARNING, "Error sending notifications", 
                                          error=str(ws_error), file_id=str(file_id))
                            
                            # Send batch tracking event for failed file processing
                            try:
                                if batch_id:
                                    file_processed(
                                        batch_id=batch_id,
                                        file_id=file_id,
                                        success=False,
                                        user_id=user_id,
                                        claim_id=claim_id,
                                        error=str(ws_error)
                                    )
                            except Exception as bt_error:
                                log_structured(logger, LogLevel.WARNING, "Error sending batch tracking event", 
                                              error=str(bt_error), file_id=str(file_id))
                    else:
                        log_structured(logger, LogLevel.WARNING, "File record not found in database", file_id=str(file_id))
                        
                except Exception as s3_error:
                    log_structured(logger, LogLevel.ERROR, "Error moving file in S3", 
                                  error=str(s3_error), source_key=s3_key)
                    
                    # Send batch tracking event for failed file processing
                    try:
                        if batch_id:
                            file_processed(
                                batch_id=batch_id,
                                file_id=file_id,
                                success=False,
                                user_id=user_id,
                                claim_id=claim_id,
                                error=str(s3_error)
                            )
                    except Exception as bt_error:
                        log_structured(logger, LogLevel.WARNING, "Error sending batch tracking event", 
                                      error=str(bt_error), file_id=str(file_id))
                    continue
                    
            except Exception as record_error:
                log_structured(logger, LogLevel.ERROR, "Error processing SQS record", error=str(record_error))
                continue
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Processed {len(event.get('Records', []))} files",
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
