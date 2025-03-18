"""
Lambda handler for processing files from the SQS queue.

This module is triggered by the SQS queue and handles:
1. Decoding the base64 file data
2. Uploading the file to S3
3. Storing file metadata in the database
4. Sending a message to the analysis queue
"""
import os
import json
import uuid
import base64
from datetime import datetime, timezone
from utils.logging_utils import get_logger
from utils.lambda_utils import get_s3_client, get_sqs_client
from models.file import FileStatus, File
from database.database import get_db_session
import sys

logger = get_logger(__name__)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "test-bucket")
SQS_ANALYSIS_QUEUE_URL = os.getenv("SQS_ANALYSIS_QUEUE_URL", "")

def upload_to_s3(s3_key: str, file_data: bytes) -> str:
    """
    Uploads file to S3 and returns the S3 URL.
    
    Args:
        s3_key (str): The S3 key for the file
        file_data (bytes): The binary data of the file
        
    Returns:
        str: The S3 URL of the uploaded file
        
    Raises:
        ValueError: If S3_BUCKET_NAME is not set
    """
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME environment variable is not set")
        
    s3 = get_s3_client()
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=file_data)
    return f"s3://{S3_BUCKET_NAME}/{s3_key}"

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

def lambda_handler(event, context):
    """
    Processes file uploads from the SQS queue.
    
    Args:
        event (dict): SQS event containing file data and metadata
        context (dict): Lambda execution context
        
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
                s3_key = message_body['s3_key']
                claim_id = uuid.UUID(message_body['claim_id'])
                room_id = uuid.UUID(message_body['room_id']) if message_body.get('room_id') else None
                file_hash = message_body['file_hash']
                file_data_base64 = message_body['file_data']
                
                # Decode base64 data
                try:
                    file_data = base64.b64decode(file_data_base64)
                except Exception as e:
                    logger.error(f"Failed to decode base64 data for file {file_id}: {str(e)}")
                    return {
                        "statusCode": 400,
                        "body": json.dumps({
                            "error": f"Invalid base64 data: {str(e)}"
                        })
                    }
                    
                # Upload to S3
                try:
                    s3_url = upload_to_s3(s3_key, file_data)
                    logger.info(f"File {file_id} uploaded to S3: {s3_url}")
                except Exception as e:
                    logger.error(f"Failed to upload file {file_id} to S3: {str(e)}")
                    return {
                        "statusCode": 500,
                        "body": json.dumps({
                            "error": f"Error uploading file to S3: {str(e)}"
                        })
                    }
                    
                # Store metadata in database
                try:
                    new_file = File(
                        id=file_id,
                        uploaded_by=user_id,
                        household_id=household_id,
                        file_name=file_name,
                        s3_key=s3_key,
                        claim_id=claim_id,
                        room_id=room_id,
                        status=FileStatus.UPLOADED,
                        file_hash=file_hash,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db_session.add(new_file)
                    db_session.commit()
                    logger.info(f"File {file_id} metadata stored in database")
                except Exception as e:
                    logger.error(f"Failed to store file {file_id} metadata in database: {str(e)}")
                    return {
                        "statusCode": 500,
                        "body": json.dumps({
                            "error": f"Error storing file metadata in database: {str(e)}"
                        })
                    }
                    
                # Send to analysis queue
                warnings = []
                try:
                    message_id = send_to_analysis_queue(file_id, s3_key, file_name, household_id, claim_id)
                    logger.info(f"File {file_id} queued for analysis with message ID {message_id}")
                except Exception as e:
                    warning_msg = f"Failed to queue file {file_id} for analysis: {str(e)}"
                    logger.error(warning_msg)
                    warnings.append(warning_msg)
                    # We don't return an error here because the file is already uploaded and stored
                
            except Exception as e:
                logger.error(f"Failed to process SQS message: {str(e)}")
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
