"""
Batch Tracker Lambda Handler

This module processes events from the batch tracking queue and updates DynamoDB with file/report status per batch.
When all items in a batch are marked complete, it sends a 'batch_completed' event to the notifier Lambda.
"""

import os
import json
import time
import boto3
import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

# Get environment variables
BATCH_TRACKING_TABLE = os.environ.get('BATCH_TRACKING_TABLE')
OUTBOUND_QUEUE_URL = os.environ.get('OUTBOUND_QUEUE_URL')

# Constants
TTL_DAYS = 7  # Number of days to keep batch tracking records

# Event types
EVENT_FILE_UPLOADED = 'file_uploaded'
EVENT_FILE_PROCESSED = 'file_processed'
EVENT_ANALYSIS_STARTED = 'analysis_started'
EVENT_ANALYSIS_COMPLETED = 'analysis_completed'
EVENT_EXPORT_STARTED = 'export_started'
EVENT_EXPORT_COMPLETED = 'export_completed'
EVENT_BATCH_COMPLETED = 'batch_completed'
EVENT_FILE_ANALYSIS_QUEUED = 'file_analysis_queued'

# Item status
STATUS_PENDING = 'pending'
STATUS_PROCESSING = 'processing'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float for JSON serialization"""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event, context):
    """
    Process events from the batch tracking queue and update DynamoDB.
    
    Args:
        event (dict): SQS event containing batch tracking messages
        context (object): Lambda context
        
    Returns:
        dict: Response with processing results
    """
    logger.info(f"Processing {len(event.get('Records', []))} batch tracking events")
    
    results = {
        'processed': 0,
        'failed': 0,
        'batch_completed': 0
    }
    
    # Validate required environment configuration
    if not BATCH_TRACKING_TABLE:
        logger.error("BATCH_TRACKING_TABLE environment variable not set")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Server misconfiguration: missing BATCH_TRACKING_TABLE'})
        }
    if not OUTBOUND_QUEUE_URL:
        logger.error("OUTBOUND_QUEUE_URL environment variable not set")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Server misconfiguration: missing OUTBOUND_QUEUE_URL'})
        }

    # Get the batch tracking table
    table = dynamodb.Table(BATCH_TRACKING_TABLE)
    
    # Process each record
    for record in event.get('Records', []):
        try:
            # Parse the message body
            message = json.loads(record['body'])
            logger.info(f"Processing message: {json.dumps(message)}")
            
            # Process the event
            process_event(table, message)
            
            # Check if batch is complete
            if check_batch_completion(table, message.get('batchId')):
                send_batch_completed_notification(message.get('batchId'), message.get('userId'))
                results['batch_completed'] += 1
            
            results['processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            results['failed'] += 1
    
    logger.info(f"Batch tracking results: {json.dumps(results)}")
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }


def process_event(table, message: Dict[str, Any]) -> None:
    """
    Process a batch tracking event and update DynamoDB.
    
    Args:
        table: DynamoDB table resource
        message (dict): Event message
    """
    event_type = message.get('eventType')
    batch_id = message.get('batchId')
    item_id = message.get('itemId')
    user_id = message.get('userId')
    claim_id = message.get('claimId')
    data = message.get('data', {})
    
    if not batch_id or not item_id:
        logger.error(f"Missing required fields: batchId or itemId in message: {json.dumps(message)}")
        return
    
    # Calculate TTL (7 days from now)
    ttl = int(time.time()) + (TTL_DAYS * 24 * 60 * 60)
    
    # Get current item if it exists
    try:
        response = table.get_item(
            Key={
                'batchId': batch_id,
                'itemId': item_id
            }
        )
        item = response.get('Item')
    except Exception as e:
        logger.error(f"Error getting item from DynamoDB: {str(e)}")
        item = None
    
    # Determine the new status based on event type
    status = determine_status(event_type, data)
    
    # Prepare the item to update
    update_item = {
        'batchId': batch_id,
        'itemId': item_id,
        'userId': user_id,
        'ttl': ttl,
        'lastUpdated': int(time.time()),
        'status': status
    }
    
    # Add optional fields if present
    if claim_id:
        update_item['claimId'] = claim_id
    
    # Add event-specific data
    if data:
        update_item['data'] = data
    
    # If item exists, merge with existing data
    if item:
        # Don't overwrite existing data if new data is empty
        if 'data' in item and (not data or data == {}):
            update_item['data'] = item['data']
        
        # Don't downgrade status (e.g., from completed to processing)
        if 'status' in item and not is_status_upgrade(item['status'], status):
            update_item['status'] = item['status']
    
    # Update the item in DynamoDB
    try:
        table.put_item(Item=update_item)
        logger.info(f"Updated item in batch tracking table: {json.dumps(update_item, cls=DecimalEncoder)}")
        
        # Send notification for this event
        send_event_notification(event_type, batch_id, item_id, user_id, claim_id, data)
        
    except Exception as e:
        logger.error(f"Error updating item in DynamoDB: {str(e)}")


def determine_status(event_type: str, data: Dict[str, Any]) -> str:
    """
    Determine the status based on the event type and data.
    
    Args:
        event_type (str): Type of event
        data (dict): Event data
        
    Returns:
        str: Status (pending, processing, completed, failed)
    """
    if event_type == EVENT_FILE_UPLOADED:
        return STATUS_PENDING
    elif event_type == EVENT_FILE_PROCESSED:
        return STATUS_COMPLETED if data.get('success') else STATUS_FAILED
    elif event_type == EVENT_ANALYSIS_STARTED:
        return STATUS_PROCESSING
    elif event_type == EVENT_FILE_ANALYSIS_QUEUED:
        return STATUS_PROCESSING
    elif event_type == EVENT_ANALYSIS_COMPLETED:
        return STATUS_COMPLETED if data.get('success') else STATUS_FAILED
    elif event_type == EVENT_EXPORT_STARTED:
        return STATUS_PROCESSING
    elif event_type == EVENT_EXPORT_COMPLETED:
        return STATUS_COMPLETED if data.get('success') else STATUS_FAILED
    else:
        return STATUS_PENDING


def is_status_upgrade(current_status: str, new_status: str) -> bool:
    """
    Check if the new status is an upgrade from the current status.
    
    Args:
        current_status (str): Current status
        new_status (str): New status
        
    Returns:
        bool: True if the new status is an upgrade, False otherwise
    """
    status_priority = {
        STATUS_PENDING: 0,
        STATUS_PROCESSING: 1,
        STATUS_COMPLETED: 2,
        STATUS_FAILED: 3  # Failed is considered higher priority than completed for notification purposes
    }
    
    return status_priority.get(new_status, 0) > status_priority.get(current_status, 0)


def check_batch_completion(table, batch_id: str) -> bool:
    """
    Check if all items in a batch are completed or failed.
    
    Args:
        table: DynamoDB table resource
        batch_id (str): Batch ID to check
        
    Returns:
        bool: True if all items are completed or failed, False otherwise
    """
    if not batch_id:
        return False
    
    try:
        # Query all items in the batch
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('batchId').eq(batch_id)
        )
        
        items = response.get('Items', [])
        
        # If no items, batch is not complete
        if not items:
            return False
        
        # Check if all items are completed or failed
        for item in items:
            status = item.get('status')
            if status not in [STATUS_COMPLETED, STATUS_FAILED]:
                return False
        
        # All items are completed or failed
        return True
        
    except Exception as e:
        logger.error(f"Error checking batch completion: {str(e)}")
        return False


def send_batch_completed_notification(batch_id: str, user_id: Optional[str]) -> None:
    """
    Send a batch completed notification to the outbound queue.
    
    Args:
        batch_id (str): Batch ID
        user_id (str): User ID
    """
    if not batch_id:
        return
    
    try:
        # Get all items in the batch
        table = dynamodb.Table(BATCH_TRACKING_TABLE)
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('batchId').eq(batch_id)
        )
        
        items = response.get('Items', [])
        
        # Prepare the notification message
        message = {
            'messageType': 'notification',
            'notificationType': EVENT_BATCH_COMPLETED,
            'batchId': batch_id,
            'timestamp': int(time.time()),
            'data': {
                'itemCount': len(items),
                'completedCount': sum(1 for item in items if item.get('status') == STATUS_COMPLETED),
                'failedCount': sum(1 for item in items if item.get('status') == STATUS_FAILED),
                'items': items
            }
        }
        
        # Add user ID if present
        if user_id:
            message['userId'] = user_id
        
        # Send the message to the outbound queue
        sqs.send_message(
            QueueUrl=OUTBOUND_QUEUE_URL,
            MessageBody=json.dumps(message, cls=DecimalEncoder)
        )
        
        logger.info(f"Sent batch completed notification: {json.dumps(message, cls=DecimalEncoder)}")
        
    except Exception as e:
        logger.error(f"Error sending batch completed notification: {str(e)}")


def send_event_notification(event_type: str, batch_id: str, item_id: str, 
                           user_id: Optional[str], claim_id: Optional[str], 
                           data: Dict[str, Any]) -> None:
    """
    Send an event notification to the outbound queue.
    
    Args:
        event_type (str): Type of event
        batch_id (str): Batch ID
        item_id (str): Item ID
        user_id (str): User ID
        claim_id (str): Claim ID
        data (dict): Event data
    """
    try:
        # Prepare the notification message
        message = {
            'messageType': 'notification',
            'notificationType': event_type,
            'batchId': batch_id,
            'itemId': item_id,
            'timestamp': int(time.time()),
            'data': data
        }
        
        # Add optional fields if present
        if user_id:
            message['userId'] = user_id
        
        if claim_id:
            message['claimId'] = claim_id
        
        # Send the message to the outbound queue
        sqs.send_message(
            QueueUrl=OUTBOUND_QUEUE_URL,
            MessageBody=json.dumps(message, cls=DecimalEncoder)
        )
        
        logger.info(f"Sent event notification: {json.dumps(message, cls=DecimalEncoder)}")
        
    except Exception as e:
        logger.error(f"Error sending event notification: {str(e)}")
