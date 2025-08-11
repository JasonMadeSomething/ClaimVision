import os
import json
import boto3
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SQS client
sqs = boto3.client('sqs')

def send_websocket_message(message_type, data, user_id=None, claim_id=None):
    """
    Send a message to the outbound WebSocket queue.
    
    Args:
        message_type (str): Type of message (e.g., 'file_processed', 'analysis_complete', 'export_status')
        data (dict): Message payload data
        user_id (str, optional): Specific user to send the message to
        claim_id (str, optional): Specific claim the message relates to
    
    Returns:
        dict: SQS response
    """
    queue_url = os.environ.get('OUTBOUND_QUEUE_URL')
    if not queue_url:
        logger.error("Missing OUTBOUND_QUEUE_URL environment variable")
        raise ValueError("Missing outbound queue configuration")
    
    # Construct the message
    message = {
        'type': message_type,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data
    }
    
    # Add routing information if provided
    if user_id:
        message['userId'] = user_id
    if claim_id:
        message['claimId'] = claim_id
    
    try:
        # Send the message to SQS
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        logger.info("Sent message to WebSocket queue: %s", json.dumps(message))
        return response
    except Exception as e:
        logger.error("Error sending WebSocket message: %s", str(e))
        raise

def notify_file_processed(file_id, claim_id, user_id, file_info):
    """
    Notify a user that their file has been processed and is available.
    
    Args:
        file_id (str): ID of the processed file
        claim_id (str): ID of the claim the file belongs to
        user_id (str): ID of the user who uploaded the file
        file_info (dict): Information about the processed file including:
                          - name: File name
                          - size: File size in bytes
                          - contentType: MIME type
                          - s3Key: S3 key for generating presigned URL
    """
    # Generate a presigned URL for the file if s3Key is provided
    s3_url = None
    if file_info.get('s3Key'):
        try:
            s3 = boto3.client('s3')
            bucket_name = os.environ.get('S3_BUCKET_NAME')
            if bucket_name:
                s3_url = s3.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': file_info['s3Key']
                    },
                    ExpiresIn=3600  # URL expires in 1 hour
                )
        except Exception as e:
            logger.warning("Could not generate presigned URL: %s", str(e))
    
    # Add the presigned URL to the file info if available
    if s3_url:
        file_info['presignedUrl'] = s3_url
    
    return send_websocket_message(
        message_type='file_processed',
        data={
            'fileId': file_id,
            'claimId': claim_id,
            'fileInfo': file_info
        },
        user_id=user_id,
        claim_id=claim_id
    )

def notify_analysis_complete(file_id, claim_id, user_id, analysis_results):
    """
    Notify a user that analysis is complete for their file.
    
    Args:
        file_id (str): ID of the analyzed file
        claim_id (str): ID of the claim the file belongs to
        user_id (str): ID of the user who should receive the notification
        analysis_results (dict): Analysis results including:
                                - labels: List of labels/tags assigned to the file
                                - confidence: Confidence scores
                                - other analysis metadata
    """
    return send_websocket_message(
        message_type='analysis_complete',
        data={
            'fileId': file_id,
            'claimId': claim_id,
            'analysisResults': analysis_results
        },
        user_id=user_id,
        claim_id=claim_id
    )

def notify_export_status(export_id, claim_id, user_id, status, details=None):
    """
    Notify a user about the status of an export operation.
    
    Args:
        export_id (str): ID of the export operation
        claim_id (str): ID of the claim being exported
        user_id (str): ID of the user who initiated the export
        status (str): Status of the export ('started', 'in_progress', 'completed', 'failed')
        details (dict, optional): Additional details about the export status
    """
    data = {
        'exportId': export_id,
        'claimId': claim_id,
        'status': status
    }
    
    if details:
        data['details'] = details
    
    return send_websocket_message(
        message_type='export_status',
        data=data,
        user_id=user_id,
        claim_id=claim_id
    )
