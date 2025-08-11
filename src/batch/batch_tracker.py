"""
Batch Tracker Utility

This module provides utility functions to send events to the batch tracking queue.
"""

import os
import json
import time
import boto3
import uuid
import logging
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs = boto3.client('sqs')

# Get environment variables
BATCH_TRACKING_QUEUE_URL = os.environ.get('BATCH_TRACKING_QUEUE_URL')

# Event types
EVENT_FILE_UPLOADED = 'file_uploaded'
EVENT_FILE_PROCESSED = 'file_processed'
EVENT_ANALYSIS_STARTED = 'analysis_started'
EVENT_ANALYSIS_COMPLETED = 'analysis_completed'
EVENT_EXPORT_STARTED = 'export_started'
EVENT_EXPORT_COMPLETED = 'export_completed'
EVENT_FILE_ANALYSIS_QUEUED = 'file_analysis_queued'


def send_batch_event(event_type: str, batch_id: str, item_id: str, 
                    user_id: Optional[str] = None, claim_id: Optional[str] = None, 
                    data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Send an event to the batch tracking queue.
    
    Args:
        event_type (str): Type of event
        batch_id (str): Batch ID
        item_id (str): Item ID
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        data (dict, optional): Event data
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    if not BATCH_TRACKING_QUEUE_URL:
        logger.error("BATCH_TRACKING_QUEUE_URL environment variable not set")
        return False
    
    if not batch_id or not item_id:
        logger.error("batch_id and item_id are required")
        return False
    
    try:
        # Prepare the message
        message = {
            'eventType': event_type,
            'batchId': batch_id,
            'itemId': item_id,
            'timestamp': int(time.time())
        }
        
        # Add optional fields if present
        if user_id:
            message['userId'] = user_id
        
        if claim_id:
            message['claimId'] = claim_id
        
        if data:
            message['data'] = data
        
        # Send the message to the batch tracking queue
        sqs.send_message(
            QueueUrl=BATCH_TRACKING_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        
        logger.info("Sent batch event: %s", json.dumps(message))
        return True
        
    except ClientError as e:
        logger.error("AWS error sending batch event: %s", e.response['Error']['Message'])
        return False
    except (ValueError, TypeError) as e:
        logger.error("Error serializing batch event: %s", str(e))
        return False
    except Exception as e:
        logger.error("An error occurred: %s", str(e))
        return False


def generate_batch_id() -> str:
    """
    Generate a unique batch ID.
    
    Returns:
        str: Unique batch ID
    """
    return f"batch-{uuid.uuid4()}"


def file_uploaded(batch_id: str, file_id: str, file_name: str,
                 user_id: Optional[str] = None, claim_id: Optional[str] = None) -> bool:
    """
    Send a file uploaded event to the batch tracking queue.
    
    Args:
        batch_id (str): Batch ID
        file_id (str): File ID
        file_name (str): File name
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    data = {
        'fileName': file_name
    }
    
    return send_batch_event(
        event_type=EVENT_FILE_UPLOADED,
        batch_id=batch_id,
        item_id=file_id,
        user_id=user_id,
        claim_id=claim_id,
        data=data
    )


def file_analysis_queued(batch_id: str, file_id: str, message_id: str,
                       user_id: Optional[str] = None, claim_id: Optional[str] = None) -> bool:
    """
    Send a file analysis queued event to the batch tracking queue.
    
    Args:
        batch_id (str): Batch ID
        file_id (str): File ID
        message_id (str): SQS message ID
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    data = {
        'messageId': message_id
    }
    
    return send_batch_event(
        event_type=EVENT_FILE_ANALYSIS_QUEUED,
        batch_id=batch_id,
        item_id=file_id,
        user_id=user_id,
        claim_id=claim_id,
        data=data
    )


def file_processed(batch_id: str, file_id: str, success: bool, file_url: Optional[str] = None,
                  user_id: Optional[str] = None, claim_id: Optional[str] = None,
                  error: Optional[str] = None) -> bool:
    """
    Send a file processed event to the batch tracking queue.
    
    Args:
        batch_id (str): Batch ID
        file_id (str): File ID
        success (bool): Whether the file was processed successfully
        file_url (str, optional): URL to the processed file
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        error (str, optional): Error message if the file processing failed
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    data = {
        'success': success
    }
    
    if file_url:
        data['fileUrl'] = file_url
    
    if error:
        data['error'] = error
    
    return send_batch_event(
        event_type=EVENT_FILE_PROCESSED,
        batch_id=batch_id,
        item_id=file_id,
        user_id=user_id,
        claim_id=claim_id,
        data=data
    )


def analysis_started(batch_id: str, file_id: str, 
                    user_id: Optional[str] = None, claim_id: Optional[str] = None) -> bool:
    """
    Send an analysis started event to the batch tracking queue.
    
    Args:
        batch_id (str): Batch ID
        file_id (str): File ID being analyzed
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    return send_batch_event(
        event_type=EVENT_ANALYSIS_STARTED,
        batch_id=batch_id,
        item_id=file_id,
        user_id=user_id,
        claim_id=claim_id
    )


def analysis_completed(batch_id: str, file_id: str, success: bool, 
                      labels: Optional[List[Dict[str, Any]]] = None,
                      user_id: Optional[str] = None, claim_id: Optional[str] = None,
                      error: Optional[str] = None) -> bool:
    """
    Send an analysis completed event to the batch tracking queue.
    
    Args:
        batch_id (str): Batch ID
        file_id (str): File ID
        success (bool): Whether the analysis was completed successfully
        labels (list, optional): List of detected labels with confidence scores
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        error (str, optional): Error message if the analysis failed
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    data = {
        'success': success
    }
    
    if labels:
        data['labels'] = labels
    
    if error:
        data['error'] = error
    
    return send_batch_event(
        event_type=EVENT_ANALYSIS_COMPLETED,
        batch_id=batch_id,
        item_id=file_id,
        user_id=user_id,
        claim_id=claim_id,
        data=data
    )


def export_started(batch_id: str, export_id: str, export_type: str,
                  user_id: Optional[str] = None, claim_id: Optional[str] = None) -> bool:
    """
    Send an export started event to the batch tracking queue.
    
    Args:
        batch_id (str): Batch ID
        export_id (str): Export ID
        export_type (str): Type of export (e.g., 'pdf', 'csv')
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    data = {
        'exportType': export_type
    }
    
    return send_batch_event(
        event_type=EVENT_EXPORT_STARTED,
        batch_id=batch_id,
        item_id=export_id,
        user_id=user_id,
        claim_id=claim_id,
        data=data
    )


def export_completed(batch_id: str, export_id: str, success: bool, 
                    export_url: Optional[str] = None,
                    user_id: Optional[str] = None, claim_id: Optional[str] = None,
                    error: Optional[str] = None) -> bool:
    """
    Send an export completed event to the batch tracking queue.
    
    Args:
        batch_id (str): Batch ID
        export_id (str): Export ID
        success (bool): Whether the export was completed successfully
        export_url (str, optional): URL to the exported file
        user_id (str, optional): User ID
        claim_id (str, optional): Claim ID
        error (str, optional): Error message if the export failed
        
    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    data = {
        'success': success
    }
    
    if export_url:
        data['exportUrl'] = export_url
    
    if error:
        data['error'] = error
    
    return send_batch_event(
        event_type=EVENT_EXPORT_COMPLETED,
        batch_id=batch_id,
        item_id=export_id,
        user_id=user_id,
        claim_id=claim_id,
        data=data
    )
