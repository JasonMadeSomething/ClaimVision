"""
Lambda handler triggered by S3 events when files are uploaded.

This module processes files after they've been uploaded to S3 and sends them to an SQS queue
for asynchronous processing. It handles special cases like ZIP files by moving them to EFS
for extraction and further processing.
"""
import os
import json
import uuid
import boto3
import mimetypes
from datetime import datetime, timezone
import re

from utils.logging_utils import get_logger
from utils.lambda_utils import get_sqs_client, get_s3_client
from database.database import get_db_session
from models.file import File, FileStatus
from models.claim import Claim
from models.room import Room

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
    S3_BUCKET_NAME = "claimvision-dev-bucket"

SQS_UPLOAD_QUEUE_URL = os.getenv("SQS_UPLOAD_QUEUE_URL")
EFS_MOUNT_PATH = os.getenv("EFS_MOUNT_PATH", "/mnt/efs")

def extract_metadata_from_s3_key(s3_key):
    """
    Extract metadata from the S3 key structure.
    
    Expected format: pending/{claim_id}/{file_id}/{filename}
    
    Args:
        s3_key (str): S3 object key
        
    Returns:
        dict: Extracted metadata including claim_id, file_id, and file_name
    """
    try:
        parts = s3_key.split('/')
        if len(parts) >= 4 and parts[0] == 'pending':
            return {
                'claim_id': parts[1],
                'file_id': parts[2],
                'file_name': '/'.join(parts[3:])  # Handle filenames with slashes
            }
        return None
    except Exception as e:
        logger.error(f"Error extracting metadata from S3 key {s3_key}: {str(e)}")
        return None

def is_zip_file(file_name):
    """
    Check if a file is a ZIP archive based on its extension.
    
    Args:
        file_name (str): Name of the file
        
    Returns:
        bool: True if the file is a ZIP archive, False otherwise
    """
    return file_name.lower().endswith('.zip')

def extract_room_from_path(path):
    """
    Extract room information from a file path.
    
    This function looks for patterns matching the canonical room types defined in the database.
    
    Args:
        path (str): File path to analyze
        
    Returns:
        str or None: Extracted room name if found, None otherwise
    """
    # Canonical room types from database initialization
    canonical_rooms = [
        "Attic", "Auto", "Basement", "Bathroom", "Bedroom", "Closet", "Dining Room", "Entry", "Exterior",
        "Family Room", "Foyer", "Game Room", "Garage", "Hall", "Kitchen", "Laundry Room", "Living Room",
        "Primary Bathroom", "Primary Bedroom", "Mud Room", "Nursery", "Office", "Pantry", "Patio",
        "Play Room", "Pool", "Porch", "Shop", "Storage", "Theater", "Utility Room", "Workout Room"
    ]
    
    # Convert to lowercase for case-insensitive matching
    canonical_rooms_lower = [room.lower() for room in canonical_rooms]
    
    # First try direct matching with canonical room names
    for i, room in enumerate(canonical_rooms_lower):
        if room in path.lower():
            return canonical_rooms[i]  # Return the properly cased room name
    
    # Try more flexible pattern matching for rooms with potential prefixes/suffixes
    room_patterns = [
        r'room[_\s-]?(\d+)',  # Room with number (Room 1, Room_2, etc.)
        r'(primary|master)[_\s-]?(bed|bath)',  # Primary/Master Bedroom/Bathroom variations
        r'(bed|bath)[_\s-]?(\d+)'  # Bedroom/Bathroom with number
    ]
    
    for pattern in room_patterns:
        match = re.search(pattern, path, re.IGNORECASE)
        if match:
            # Map to closest canonical room
            if 'bed' in match.group(0).lower():
                return "Primary Bedroom" if "primary" in match.group(0).lower() or "master" in match.group(0).lower() else "Bedroom"
            elif 'bath' in match.group(0).lower():
                return "Primary Bathroom" if "primary" in match.group(0).lower() or "master" in match.group(0).lower() else "Bathroom"
            else:
                return "Room"  # Generic room if we can't map to a specific type
    
    return None

def process_zip_file(s3_client, bucket, s3_key, metadata):
    """
    Process a ZIP file by moving it to EFS and extracting its contents.
    
    Args:
        s3_client: The boto3 S3 client
        bucket (str): S3 bucket name
        s3_key (str): S3 object key
        metadata (dict): Extracted metadata from the S3 key
        
    Returns:
        list: List of extracted files with their metadata
    """
    logger.info(f"Processing ZIP file: {s3_key}")
    
    claim_id = metadata['claim_id']
    file_id = metadata['file_id']
    file_name = metadata['file_name']
    
    # Create a directory in EFS for this extraction
    extraction_dir = os.path.join(EFS_MOUNT_PATH, claim_id, file_id)
    os.makedirs(extraction_dir, exist_ok=True)
    
    # Download the ZIP file to EFS
    zip_path = os.path.join(extraction_dir, file_name)
    logger.info(f"Downloading ZIP file to: {zip_path}")
    
    try:
        s3_client.download_file(bucket, s3_key, zip_path)
        
        # TODO: Implement ZIP extraction logic
        # This would involve using the zipfile module to extract the contents
        # and then processing each extracted file
        
        # For now, just return a placeholder
        return [{
            "status": "pending",
            "message": "ZIP file processing not yet implemented",
            "zip_path": zip_path,
            "extraction_dir": extraction_dir
        }]
    except Exception as e:
        logger.error(f"Error processing ZIP file {s3_key}: {str(e)}")
        return [{
            "status": "error",
            "error": f"Failed to process ZIP file: {str(e)}"
        }]

def queue_file_for_processing(file_info, s3_client, sqs_client):
    """
    Queue a file for asynchronous processing via SQS.
    
    Args:
        file_info (dict): Information about the file to process
        s3_client: The boto3 S3 client
        sqs_client: The boto3 SQS client
        
    Returns:
        dict: Result of the SQS message send operation
    """
    try:
        logger.info(f"Queueing file for processing: {file_info.get('file_name')}")
        
        # Prepare message payload
        message_body = {
            "file_id": file_info.get('file_id'),
            "user_id": file_info.get('user_id'),
            "file_name": file_info.get('file_name'),
            "s3_key": file_info.get('s3_key'),
            "s3_bucket": S3_BUCKET_NAME,
            "claim_id": file_info.get('claim_id'),
            "upload_time": datetime.now(timezone.utc).isoformat()
        }
        
        if file_info.get('room_id'):
            message_body["room_id"] = file_info.get('room_id')
        
        # Send message to SQS
        if not SQS_UPLOAD_QUEUE_URL:
            logger.error("SQS_UPLOAD_QUEUE_URL environment variable is not set")
            return {"status": "error", "error": "SQS queue URL not configured"}
        
        response = sqs_client.send_message(
            QueueUrl=SQS_UPLOAD_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
        
        logger.info(f"File queued successfully: {response.get('MessageId')}")
        return {
            "status": "queued",
            "message_id": response.get('MessageId'),
            "file_id": file_info.get('file_id')
        }
    except Exception as e:
        logger.error(f"Error queueing file for processing: {str(e)}")
        return {"status": "error", "error": str(e)}

def create_file_record(db_session, file_info):
    """
    Create a database record for the uploaded file.
    
    Args:
        db_session: SQLAlchemy database session
        file_info (dict): Information about the file
        
    Returns:
        File: The created file record
    """
    try:
        # Check if a room ID was provided or extracted
        room_id = file_info.get('room_id')
        if room_id:
            # Verify the room exists and belongs to the claim
            room = db_session.query(Room).filter(
                Room.id == room_id,
                Room.claim_id == file_info.get('claim_id')
            ).first()
            
            if not room:
                logger.warning(f"Room {room_id} not found or does not belong to claim {file_info.get('claim_id')}")
                room_id = None
        
        # Create the file record
        file_record = File(
            id=uuid.UUID(file_info.get('file_id')),
            uploaded_by=uuid.UUID(file_info.get('user_id')),
            group_id=file_info.get('group_id'),  # This should be fetched from the claim
            file_name=file_info.get('file_name'),
            s3_key=file_info.get('s3_key'),
            status=FileStatus.UPLOADED,
            claim_id=uuid.UUID(file_info.get('claim_id')),
            content_type=file_info.get('content_type'),
            file_size=file_info.get('file_size'),
            file_hash=file_info.get('file_hash', ''),
            room_id=uuid.UUID(room_id) if room_id else None,
            file_metadata={
                "upload_method": "presigned_url",
                "original_upload_time": file_info.get('timestamp')
            }
        )
        
        db_session.add(file_record)
        db_session.commit()
        
        logger.info(f"File record created: {file_record.id}")
        return file_record
    except Exception as e:
        logger.error(f"Error creating file record: {str(e)}")
        db_session.rollback()
        return None

def lambda_handler(event, context):
    """
    Process S3 events triggered when files are uploaded.
    
    Args:
        event (dict): S3 event notification
        context (dict): Lambda execution context
        
    Returns:
        dict: Processing result
    """
    logger.info("Processing S3 upload event")
    
    try:
        # Initialize clients
        s3_client = get_s3_client()
        sqs_client = get_sqs_client()
        
        # Process each record in the event
        results = []
        for record in event.get('Records', []):
            try:
                # Extract S3 event information
                bucket = record['s3']['bucket']['name']
                s3_key = record['s3']['object']['key']
                object_size = record['s3']['object'].get('size', 0)
                
                logger.info(f"Processing uploaded file: {s3_key} in bucket {bucket}")
                
                # Extract metadata from the S3 key
                metadata = extract_metadata_from_s3_key(s3_key)
                if not metadata:
                    logger.error(f"Could not extract metadata from S3 key: {s3_key}")
                    results.append({
                        "status": "error",
                        "s3_key": s3_key,
                        "error": "Invalid S3 key format"
                    })
                    continue
                
                # Add file size to metadata
                metadata['file_size'] = object_size
                
                # Determine content type
                content_type, _ = mimetypes.guess_type(metadata['file_name'])
                metadata['content_type'] = content_type
                
                # Check if this is a ZIP file
                if is_zip_file(metadata['file_name']):
                    # Process ZIP file
                    zip_results = process_zip_file(s3_client, bucket, s3_key, metadata)
                    results.extend(zip_results)
                    continue
                
                # For regular files, queue for processing
                file_info = {
                    "file_id": metadata['file_id'],
                    "file_name": metadata['file_name'],
                    "s3_key": s3_key,
                    "claim_id": metadata['claim_id'],
                    "file_size": object_size,
                    "content_type": content_type
                }
                
                # TODO: Get user_id and group_id from metadata or database
                # For now, we'll need to implement this part
                
                # Queue the file for processing
                queue_result = queue_file_for_processing(file_info, s3_client, sqs_client)
                results.append(queue_result)
                
                # TODO: Create database record for the file
                # This requires a database session and additional metadata
                
            except Exception as e:
                logger.error(f"Error processing record: {str(e)}")
                results.append({
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Processed {len(event.get('Records', []))} records",
                "results": results
            })
        }
    except Exception as e:
        logger.exception(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error processing S3 event",
                "error": str(e)
            })
        }
