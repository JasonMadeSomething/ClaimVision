"""
File Organization Handler

This module processes messages from the file organization queue,
organizes files in EFS, and prepares them for zipping and delivery.
"""

import os
import json
import logging
import uuid
import boto3
import mimetypes
from datetime import datetime, timezone
from database.database import get_db_session
from models.report import Report, ReportStatus
from models.file import File

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')

# Get environment variables
DELIVER_REPORT_QUEUE_URL = os.environ.get('DELIVER_REPORT_QUEUE_URL')
EFS_MOUNT_PATH = os.environ.get('EFS_MOUNT_PATH', '/mnt/reports')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')

def lambda_handler(event, context):
    """
    Process messages from the file organization queue.
    
    Organizes files in EFS and prepares them for zipping and delivery.
    
    Parameters
    ----------
    event : dict
        The SQS event containing the file organization message
    context : object
        The Lambda context object
    
    Returns
    -------
    dict
        Response indicating success or failure
    """
    try:
        logger.info("Processing file organization request")
        
        # Process each SQS message
        for record in event.get('Records', []):
            try:
                # Parse message body
                message_body = json.loads(record.get('body', '{}'))
                
                # Extract message data
                report_id = message_body.get('report_id')
                report_data = message_body.get('report_data', {})
                email_address = message_body.get('email_address')  # Get email address from message
                
                if not report_id:
                    logger.error("Report ID not found in message")
                    continue
                
                if not email_address:
                    logger.error("Email address not found in message")
                    continue
                
                # Get database session
                session = get_db_session()
                
                try:
                    # Update report status to ORGANIZING
                    report = session.query(Report).filter(Report.id == uuid.UUID(report_id)).first()
                    
                    if not report:
                        logger.error(f"Report with ID {report_id} not found")
                        continue
                    
                    # Update report status
                    report.update_status(ReportStatus.ORGANIZING)
                    session.commit()
                    
                    # Create report directory in EFS
                    report_dir = os.path.join(EFS_MOUNT_PATH, str(report.id))
                    os.makedirs(report_dir, exist_ok=True)
                    
                    # Create submission directory
                    submission_dir = os.path.join(report_dir, "submission")
                    os.makedirs(submission_dir, exist_ok=True)
                    
                    # Create room directories
                    for room_name, room_data in report_data.get('rooms', {}).items():
                        room_dir = os.path.join(submission_dir, room_name)
                        os.makedirs(room_dir, exist_ok=True)
                    
                    # Download and organize claim files from S3
                    claim_files = session.query(File).filter(
                        File.claim_id == report.claim_id,
                        File.deleted.is_(False)
                    ).all()
                    
                    # Track file counts for each item to handle multiple files per item
                    item_file_counts = {}
                    
                    for file in claim_files:
                        try:
                            # Determine which room and item this file belongs to
                            file_item_id = None
                            for item_file in file.items:
                                file_item_id = item_file.id
                                break
                            
                            if file_item_id:
                                # Find the room and item number for this file
                                target_room = None
                                item_number = None
                                item_name = None
                                
                                for room_name, room_data in report_data.get('rooms', {}).items():
                                    for item in room_data.get('items', []):
                                        if item.get('id') == str(file_item_id):
                                            target_room = room_name
                                            item_number = item.get('number')
                                            item_name = item.get('name')
                                            break
                                    if target_room:
                                        break
                                
                                if target_room and item_number and item_name:
                                    # Create a sanitized item name for the filename
                                    safe_item_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in item_name)
                                    safe_item_name = safe_item_name.strip()
                                    
                                    # Get the file count for this item
                                    if str(file_item_id) not in item_file_counts:
                                        item_file_counts[str(file_item_id)] = 0
                                    item_file_counts[str(file_item_id)] += 1
                                    
                                    # Format the filename: <item number> - <Short description> (x of y).extension
                                    file_ext = mimetypes.guess_extension(file.content_type)
                                    if not file_ext:
                                        file_ext = os.path.splitext(file.file_name)[-1] or ".bin"
                                    
                                    file_ext = file_ext.lstrip(".")
                                    new_filename = f"{item_number} - {safe_item_name} ({item_file_counts[str(file_item_id)]}).{file_ext}"
                                    
                                    # Create the target directory if it doesn't exist
                                    target_dir = os.path.join(submission_dir, target_room)
                                    os.makedirs(target_dir, exist_ok=True)
                                    
                                    # Download file from S3
                                    local_path = os.path.join(target_dir, new_filename)
                                    s3_client.download_file(
                                        S3_BUCKET_NAME,
                                        file.s3_key,
                                        local_path
                                    )
                                    
                                    logger.info(f"Downloaded file {file.file_name} to {local_path}")
                                else:
                                    # If we can't determine the room/item, put it in a misc folder
                                    misc_dir = os.path.join(submission_dir, "misc")
                                    os.makedirs(misc_dir, exist_ok=True)
                                    
                                    local_path = os.path.join(misc_dir, file.file_name)
                                    
                                    s3_client.download_file(
                                        S3_BUCKET_NAME,
                                        file.s3_key,
                                        local_path
                                    )
                                    
                                    logger.info(f"Downloaded file {file.file_name} to misc directory")
                            else:
                                # If the file isn't associated with an item, put it in a misc folder
                                misc_dir = os.path.join(submission_dir, "misc")
                                os.makedirs(misc_dir, exist_ok=True)
                                
                                local_path = os.path.join(misc_dir, file.file_name)
                                
                                s3_client.download_file(
                                    S3_BUCKET_NAME,
                                    file.s3_key,
                                    local_path
                                )
                                
                                logger.info(f"Downloaded file {file.file_name} to misc directory")
                            
                        except Exception as e:
                            logger.error(f"Error downloading file {file.id}: {str(e)}")
                    
                    # Send message to deliver report queue
                    message = {
                        'report_id': report_id,
                        'report_dir': report_dir,
                        'report_data': report_data,  # Pass the structured report data to the next step
                        'email_address': email_address,  # Pass email address to next step
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    sqs_client.send_message(
                        QueueUrl=DELIVER_REPORT_QUEUE_URL,
                        MessageBody=json.dumps(message),
                        MessageAttributes={
                            'ReportId': {
                                'DataType': 'String',
                                'StringValue': report_id
                            }
                        }
                    )
                    
                    logger.info(f"File organization completed for report ID: {report_id}")
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error processing report {report_id}: {str(e)}")
                    
                    # Update report status to FAILED
                    try:
                        report = session.query(Report).filter(Report.id == uuid.UUID(report_id)).first()
                        if report:
                            report.update_status(ReportStatus.FAILED, str(e))
                            session.commit()
                    except Exception as update_error:
                        logger.error(f"Error updating report status: {str(update_error)}")
                
                finally:
                    session.close()
                    
            except Exception as e:
                logger.error(f"Error processing SQS message: {str(e)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'File organization processing completed'})
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
