"""
Lambda handler triggered by SQS events containing S3 notifications when files are uploaded.

This module processes files after they've been uploaded to S3 and sends them to an SQS queue
for asynchronous processing. It handles special cases like ZIP files by moving them to EFS
for extraction and further processing.
"""
import json
import mimetypes
import os
import tempfile
import uuid
import zipfile
import hashlib
from datetime import datetime, timezone
import re

from database.database import get_db_session
from models.file import File, FileStatus
from models.user import User
from models.group_membership import GroupMembership
from models.room import Room
from utils.lambda_utils import get_s3_client, get_sqs_client
from utils.logging_utils import get_logger, log_structured, LogLevel
from batch.batch_tracker import file_processed, file_uploaded

# Configure logging
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
    
    Expected formats:
    - pending/{claim_id}/{file_id}/{filename}
    - pending/{claim_id}/{user_id}/{file_id}/{filename}
    
    Args:
        s3_key (str): S3 object key
        
    Returns:
        dict: Extracted metadata including claim_id, file_id, and file_name
    """
    try:
        parts = s3_key.split('/')
        if len(parts) >= 4 and parts[0] == 'pending':
            if len(parts) >= 5:  # New format with user_id
                return {
                    'claim_id': parts[1],
                    'user_id': parts[2],
                    'file_id': parts[3],
                    'file_name': '/'.join(parts[4:])  # Handle filenames with slashes
                }
            else:  # Old format without user_id
                return {
                    'claim_id': parts[1],
                    'file_id': parts[2],
                    'file_name': '/'.join(parts[3:])  # Handle filenames with slashes
                }
        return None
    except Exception as e:
        logger.error("Error extracting metadata from S3 key %s: %s", s3_key, str(e))
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

def process_zip_file(bucket, s3_key, file_name, claim_id, group_id, user_id):
    """
    Process a ZIP file by extracting its contents and uploading each file to S3.
    
    Args:
        bucket (str): S3 bucket containing the ZIP file
        s3_key (str): S3 key of the ZIP file
        file_name (str): Original file name
        claim_id (uuid.UUID): ID of the claim this file belongs to
        group_id (uuid.UUID): ID of the group this file belongs to
        user_id (uuid.UUID): ID of the user who uploaded the file
        
    Returns:
        list: List of processed file information
    """
    temp_dir = None
    results = []
    
    # Define allowed file extensions and MIME types for security
    allowed_extensions = [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',  # Images
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Documents
        '.txt', '.csv', '.rtf',  # Text files
        '.mp4', '.mov', '.avi', '.wmv',  # Videos
        '.mp3', '.wav', '.aac',  # Audio
        '.heic', '.heif'  # Apple formats
    ]
    
    # Potentially dangerous file extensions that should be blocked
    blocked_extensions = [
        '.exe', '.bat', '.cmd', '.ps1', '.sh', '.js', '.vbs', '.jar',  # Executables
        '.msi', '.dll', '.sys', '.com', '.bin',  # System files
        '.php', '.asp', '.aspx', '.jsp', '.cgi',  # Web scripts
        '.py', '.rb', '.pl',  # Programming languages
        '.htaccess', '.config',  # Configuration files
        '.reg',  # Registry files
        '.app', '.dmg'  # Mac executables
    ]
    
    try:
        # Validate inputs
        if not bucket or not s3_key or not file_name:
            log_structured(logger, LogLevel.ERROR, "Invalid parameters for ZIP processing", 
                          bucket=bucket, s3_key=s3_key, file_name=file_name)
            return [{
                "status": "error",
                "error": "Missing required parameters for ZIP processing"
            }]
        
        if not claim_id:
            log_structured(logger, LogLevel.ERROR, "Missing claim_id for ZIP processing", 
                          s3_key=s3_key)
            return [{
                "status": "error",
                "error": "Missing claim_id for ZIP processing"
            }]
            
        if not group_id:
            log_structured(logger, LogLevel.WARNING, "Missing group_id for ZIP processing", 
                          s3_key=s3_key, claim_id=str(claim_id))
            # Continue processing but log a warning
            
        if not user_id:
            log_structured(logger, LogLevel.WARNING, "Missing user_id for ZIP processing", 
                          s3_key=s3_key, claim_id=str(claim_id))
            # Continue processing but log a warning
        
        # Create a temporary directory to extract the ZIP file
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, file_name)
        
        log_structured(logger, LogLevel.INFO, "Processing ZIP file", 
                      s3_key=s3_key, 
                      claim_id=str(claim_id),
                      temp_dir=temp_dir)
        
        # Download the ZIP file
        try:
            s3_client = get_s3_client()
            s3_client.download_file(bucket, s3_key, zip_path)
            log_structured(logger, LogLevel.INFO, "Downloaded ZIP file", 
                          zip_path=zip_path, 
                          s3_key=s3_key)
        except Exception as download_error:
            log_structured(logger, LogLevel.ERROR, "Error downloading ZIP file", 
                          error=str(download_error), 
                          s3_key=s3_key)
            return [{
                "status": "error",
                "error": f"Failed to download ZIP file: {str(download_error)}"
            }]
        
        # Validate ZIP file
        if not os.path.exists(zip_path):
            log_structured(logger, LogLevel.ERROR, "ZIP file not found after download", 
                          zip_path=zip_path)
            return [{
                "status": "error",
                "error": "ZIP file not found after download"
            }]
            
        if not zipfile.is_zipfile(zip_path):
            log_structured(logger, LogLevel.ERROR, "File is not a valid ZIP archive", 
                          zip_path=zip_path)
            return [{
                "status": "error",
                "error": "File is not a valid ZIP archive"
            }]
        
        # Extract the ZIP file
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the list of files in the ZIP
                file_list = zip_ref.namelist()
                log_structured(logger, LogLevel.INFO, "ZIP file contents", 
                              file_count=len(file_list), 
                              s3_key=s3_key)
                
                # Check for empty ZIP file
                if not file_list:
                    log_structured(logger, LogLevel.WARNING, "ZIP file is empty", 
                                  s3_key=s3_key)
                    return [{
                        "status": "warning",
                        "message": "ZIP file is empty"
                    }]
                
                # Extract all files
                zip_ref.extractall(temp_dir)
                log_structured(logger, LogLevel.INFO, "Extracted ZIP contents", 
                              file_count=len(file_list), 
                              temp_dir=temp_dir)
                
                # Process each extracted file
                for extracted_file in file_list:
                    # Skip directories
                    if extracted_file.endswith('/'):
                        continue
                    
                    try:
                        # Generate a unique ID for this file
                        extracted_file_id = str(uuid.uuid4())
                        
                        # Get the full path of the extracted file
                        extracted_path = os.path.join(temp_dir, extracted_file)
                        
                        # Check if file exists
                        if not os.path.exists(extracted_path):
                            log_structured(logger, LogLevel.WARNING, "Extracted file not found", 
                                          file_path=extracted_path)
                            continue
                        
                        # Check if file is empty
                        file_size = os.path.getsize(extracted_path)
                        if file_size == 0:
                            log_structured(logger, LogLevel.WARNING, "Extracted file is empty", 
                                          file_path=extracted_path)
                            continue
                        
                        # Security check: Validate file extension
                        file_ext = os.path.splitext(extracted_file.lower())[1]
                        if file_ext in blocked_extensions:
                            log_structured(logger, LogLevel.WARNING, "Blocked potentially malicious file", 
                                          file_name=extracted_file, 
                                          extension=file_ext)
                            continue
                            
                        if file_ext not in allowed_extensions:
                            log_structured(logger, LogLevel.WARNING, "Skipping file with unsupported extension", 
                                          file_name=extracted_file, 
                                          extension=file_ext)
                            continue
                        
                        # Get content type
                        content_type, _ = mimetypes.guess_type(extracted_file)
                        if not content_type:
                            content_type = 'application/octet-stream'  # Default content type
                        
                        # Additional security check: Verify content type matches extension
                        # For example, if file has .jpg extension, content type should be image/jpeg
                        expected_type = None
                        if file_ext in ['.jpg', '.jpeg']:
                            expected_type = 'image/jpeg'
                        elif file_ext == '.png':
                            expected_type = 'image/png'
                        elif file_ext == '.pdf':
                            expected_type = 'application/pdf'
                        
                        if expected_type and content_type != expected_type:
                            log_structured(logger, LogLevel.WARNING, "File content type doesn't match extension", 
                                          file_name=extracted_file, 
                                          extension=file_ext,
                                          content_type=content_type,
                                          expected_type=expected_type)
                            # We'll still process it, but log the warning
                        
                        # Extract room information from file path if available
                        room_name = extract_room_from_path(extracted_file)
                        
                        # Generate S3 key for the extracted file
                        extracted_s3_key = f"pending/{claim_id}/{group_id}/{extracted_file_id}/{os.path.basename(extracted_file)}"
                        
                        # Upload the extracted file to S3
                        log_structured(logger, LogLevel.INFO, "Uploading extracted file", 
                                      file_name=os.path.basename(extracted_file), 
                                      s3_key=extracted_s3_key,
                                      file_size=file_size,
                                      content_type=content_type)
                        
                        try:
                            s3_client.upload_file(
                                extracted_path,
                                bucket,
                                extracted_s3_key,
                                ExtraArgs={'ContentType': content_type}
                            )
                        except Exception as upload_error:
                            log_structured(logger, LogLevel.ERROR, "Error uploading extracted file", 
                                          error=str(upload_error), 
                                          file_path=extracted_path,
                                          s3_key=extracted_s3_key)
                            continue
                        
                        # Create file info for this extracted file
                        file_info = {
                            "file_id": extracted_file_id,
                            "file_name": os.path.basename(extracted_file),
                            "s3_key": extracted_s3_key,
                            "claim_id": str(claim_id),
                            "file_size": file_size,
                            "content_type": content_type,
                            "user_id": str(user_id) if user_id else None,
                            "group_id": str(group_id) if group_id else None,
                            "extracted_from_zip": s3_key,
                            "bucket": bucket,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Add room information if available
                        if room_name:
                            file_info["room_name"] = room_name
                        
                        # Add to results
                        results.append({
                            "status": "extracted",
                            "file_info": file_info
                        })
                        
                        # Queue the extracted file for processing
                        try:
                            if file_info.get('group_id') and file_info.get('user_id'):
                                queue_result = queue_file_for_processing(
                                    file_info, 
                                    file_info.get('s3_key'), 
                                    file_info.get('file_name'), 
                                    uuid.UUID(file_info.get('claim_id')), 
                                    uuid.UUID(file_info.get('group_id')), 
                                    uuid.UUID(file_info.get('user_id'))
                                )
                                log_structured(logger, LogLevel.INFO, "Queued extracted file", 
                                              message_id=queue_result.get('message_id'),
                                              file_id=extracted_file_id)
                            else:
                                log_structured(logger, LogLevel.WARNING, "Skipping queue for extracted file - missing group_id or user_id", 
                                              file_id=extracted_file_id)
                        except Exception as queue_error:
                            log_structured(logger, LogLevel.ERROR, "Error queueing extracted file", 
                                          error=str(queue_error), 
                                          file_id=extracted_file_id)
                    except Exception as file_error:
                        log_structured(logger, LogLevel.ERROR, "Error processing extracted file", 
                                      error=str(file_error), 
                                      file_name=extracted_file)
                        continue
        except zipfile.BadZipFile as zip_error:
            log_structured(logger, LogLevel.ERROR, "Invalid ZIP file format", 
                          error=str(zip_error), 
                          zip_path=zip_path)
            return [{
                "status": "error",
                "error": f"Invalid ZIP file format: {str(zip_error)}"
            }]
        
        # Return the results
        return results
        
    except Exception as e:
        log_structured(logger, LogLevel.ERROR, "Error processing ZIP file", 
                      error=str(e), 
                      s3_key=s3_key)
        return [{
            "status": "error",
            "error": f"Failed to process ZIP file: {str(e)}"
        }]
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                log_structured(logger, LogLevel.INFO, "Cleaned up temporary directory", 
                              temp_dir=temp_dir)
            except Exception as cleanup_error:
                log_structured(logger, LogLevel.WARNING, "Error cleaning up temporary directory", 
                              error=str(cleanup_error), 
                              temp_dir=temp_dir)

def queue_file_for_processing(file_info, s3_key, file_name, claim_id, group_id, user_id, **kwargs):
    """
    Queue a file for processing by sending a message to SQS.
    
    Args:
        file_info (dict): Information about the file
        s3_key (str): S3 key where the file is stored
        file_name (str): Original file name
        claim_id (uuid.UUID): ID of the claim this file belongs to
        group_id (uuid.UUID): ID of the group this file belongs to
        user_id (uuid.UUID): ID of the user who uploaded the file
        **kwargs: Additional parameters (not used)
        
    Returns:
        dict: Response with status and message ID
    """
    try:
        log_structured(
            logger, 
            LogLevel.INFO, 
            f"Queueing file for processing: {file_name}", 
            file_id=file_info.get('file_id'),
            file_name=file_name,
            claim_id=str(claim_id)
        )
        
        # Prepare message payload - convert UUID objects to strings
        message_body = {
            "file_id": file_info.get('file_id'),
            "user_id": str(user_id),
            "file_name": file_name,
            "s3_key": s3_key,
            "s3_bucket": S3_BUCKET_NAME,
            "claim_id": str(claim_id),
            "upload_time": datetime.now(timezone.utc).isoformat()
        }
        
        # Only add group_id if it's not None or empty
        if group_id:
            message_body["group_id"] = str(group_id)
        
        if file_info.get('room_id'):
            message_body["room_id"] = str(file_info.get('room_id'))
        
        # Log the full message body in dev environments
        log_structured(logger, LogLevel.DEBUG, "SQS message payload", message_body=message_body)
        
        sqs_client = get_sqs_client()
        response = sqs_client.send_message(
            QueueUrl=SQS_UPLOAD_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
        
        log_structured(
            logger, 
            LogLevel.INFO, 
            "File queued successfully", 
            message_id=response.get('MessageId'),
            file_id=file_info.get('file_id')
        )
        
        return {
            "status": "queued",
            "message_id": response.get('MessageId'),
            "file_id": file_info.get('file_id')
        }
    except Exception as e:
        log_structured(logger, LogLevel.ERROR, "Error queueing file for processing", error=str(e), file_info=file_info)
        return {"status": "error", "error": str(e)}

def create_file_record(db_session, file_info):
    """
    Create a file record in the database.
    
    Args:
        db_session (Session): Database session
        file_info (dict): Information about the file
        
    Returns:
        dict: File information with ID
    """
    try:
        # Extract room information from the file name if available
        room_id = None
        if file_info.get('file_name'):
            room_name = extract_room_from_path(file_info.get('file_name'))
            if room_name:
                # Look up the room ID by name
                room = db_session.query(Room).filter(
                    Room.name.ilike(f"%{room_name}%")
                ).first()
                
                if room:
                    room_id = room.id
                    log_structured(logger, LogLevel.INFO, "Associated file with room", 
                                  room_name=room_name, room_id=str(room_id))
                    # Add room_id to file_info
                    file_info['room_id'] = str(room_id)
        
        # Calculate file hash if not provided
        file_hash = file_info.get('file_hash')
        if not file_hash and file_info.get('s3_key') and file_info.get('bucket'):
            try:
                # Get S3 client
                s3_client = get_s3_client()
                
                # Get the file content from S3 and calculate hash
                log_structured(logger, LogLevel.INFO, "Calculating file hash", 
                              file_id=file_info.get('file_id'), 
                              s3_key=file_info.get('s3_key'))
                
                response = s3_client.get_object(
                    Bucket=file_info.get('bucket'),
                    Key=file_info.get('s3_key')
                )
                
                # Calculate SHA-256 hash of the file content
                sha256_hash = hashlib.sha256()
                for chunk in response['Body'].iter_chunks(4096):
                    sha256_hash.update(chunk)
                
                file_hash = sha256_hash.hexdigest()
                log_structured(logger, LogLevel.INFO, "Calculated file hash", 
                              file_id=file_info.get('file_id'), 
                              file_hash=file_hash)
                
                # Add hash to file_info
                file_info['file_hash'] = file_hash
                
            except Exception as e:
                log_structured(logger, LogLevel.WARNING, "Error calculating file hash", 
                              error=str(e), 
                              file_id=file_info.get('file_id'))
                # Generate a temporary unique hash to avoid constraint violation
                file_hash = f"temp-{uuid.uuid4().hex}"
                file_info['file_hash'] = file_hash
        
        # Create the file record with all available information
        file_record = File(
            id=uuid.UUID(file_info.get('file_id')),
            claim_id=uuid.UUID(file_info.get('claim_id')),
            group_id=uuid.UUID(file_info.get('group_id')),
            uploaded_by=uuid.UUID(file_info.get('user_id')),  # Use uploaded_by for the user ID
            file_name=file_info.get('file_name'),
            status=FileStatus.UPLOADED,  # Use UPLOADED instead of PENDING
            s3_key=file_info.get('s3_key'),
            content_type=file_info.get('content_type', ''),
            file_size=file_info.get('file_size', 0),
            file_hash=file_hash,
            room_id=uuid.UUID(file_info.get('room_id')) if file_info.get('room_id') else None,
            file_metadata={
                "upload_method": "presigned_url",
                "original_upload_time": file_info.get('timestamp')
            }
        )
        
        db_session.add(file_record)
        db_session.commit()
        
        log_structured(logger, LogLevel.INFO, "Created file record", file_id=str(file_record.id))
        return file_info
    except Exception as e:
        log_structured(logger, LogLevel.ERROR, "Error creating file record", error=str(e))
        db_session.rollback()
        return None

def lambda_handler(event, _context):
    """
    Process SQS events containing S3 notifications when files are uploaded.
    
    Args:
        event (dict): SQS event containing S3 notifications
        _context: Lambda execution context (unused)
        
    Returns:
        dict: Processing result
    """
    log_structured(logger, LogLevel.INFO, "Processing SQS event with S3 upload notifications")
    
    try:
        # Initialize results
        results = []
        
        # Process each SQS record
        for record in event.get('Records', []):
            try:
                # Extract S3 event from SQS message
                message_body = json.loads(record.get('body', '{}'))
                log_structured(logger, LogLevel.DEBUG, "Processing SQS message", message_body=message_body)
                
                # Extract S3 information
                s3_info = message_body.get('Records', [])[0].get('s3', {})
                bucket = s3_info.get('bucket', {}).get('name', '')
                s3_key = s3_info.get('object', {}).get('key', '')
                
                # Skip if missing required information
                if not bucket or not s3_key:
                    log_structured(logger, LogLevel.ERROR, "Missing bucket or key in S3 event", 
                                  bucket=bucket, s3_key=s3_key)
                    continue
                
                # Extract metadata from S3 key
                metadata = extract_metadata_from_s3_key(s3_key)
                if not metadata:
                    log_structured(logger, LogLevel.ERROR, "Could not extract metadata from S3 key", s3_key=s3_key)
                    continue
                
                # Create file info dictionary
                file_info = {
                    "file_id": str(uuid.uuid4()),
                    "file_name": metadata.get('file_name', ''),
                    "claim_id": metadata.get('claim_id', ''),
                    "user_id": metadata.get('user_id', ''),
                    "s3_key": s3_key,
                    "bucket": bucket,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Check if there's a batch_id in the metadata (from the URL query parameters)
                batch_id = metadata.get('batch_id')
                if not batch_id:
                    # Log error and continue without batch tracking - this indicates a real issue
                    log_structured(logger, LogLevel.ERROR, "No batch_id found in metadata, batch tracking disabled for this file", 
                                  file_id=file_info['file_id'])
                    # We'll still process the file but won't send batch tracking events
                else:
                    file_info['batch_id'] = batch_id
                    
                    # Send batch tracking event for file upload confirmation
                    try:
                        file_uploaded(
                            batch_id=batch_id,
                            file_id=file_info['file_id'],
                            file_name=file_info['file_name'],
                            user_id=file_info['user_id'],
                            claim_id=file_info['claim_id']
                        )
                        log_structured(logger, LogLevel.INFO, "Sent batch tracking event for file upload confirmation", 
                                      file_id=file_info['file_id'], batch_id=batch_id)
                    except Exception as bt_error:
                        log_structured(logger, LogLevel.WARNING, "Failed to send batch tracking event", 
                                      error=str(bt_error), file_id=file_info['file_id'])
                
                # Get group_id from user if not in metadata
                if not metadata.get('group_id'):
                    try:
                        with get_db_session() as user_db_session:
                            user = user_db_session.query(User).filter_by(
                                id=uuid.UUID(metadata.get('user_id'))
                            ).first()
                            
                            if user:
                                # Get the user's active membership
                                membership = user_db_session.query(GroupMembership).filter_by(
                                    user_id=user.id
                                ).first()
                                
                                if membership and membership.group_id:
                                    file_info['group_id'] = str(membership.group_id)
                                    log_structured(logger, LogLevel.INFO, "Using group_id from user membership", 
                                                 group_id=file_info['group_id'], user_id=metadata.get('user_id'))
                            else:
                                log_structured(logger, LogLevel.WARNING, "User not found", user_id=metadata.get('user_id'))
                    except Exception as user_error:
                        log_structured(logger, LogLevel.WARNING, "Could not fetch user to get group_id", error=str(user_error))
                else:
                    file_info['group_id'] = metadata.get('group_id')
                
                # Determine content type
                content_type, _ = mimetypes.guess_type(file_info['file_name'])
                file_info['content_type'] = content_type
                
                # Check if this is a ZIP file
                if is_zip_file(file_info['file_name']):
                    # Process ZIP file
                    zip_results = process_zip_file(bucket, s3_key, file_info['file_name'], file_info['claim_id'], file_info.get('group_id'), file_info.get('user_id'))
                    
                    # Add batch tracking for each extracted file
                    for zip_result in zip_results:
                        try:
                            file_processed(
                                batch_id=file_info.get('batch_id'),
                                file_id=zip_result.get('file_id', str(uuid.uuid4())),
                                success=zip_result.get('status') == 'success',
                                file_url=f"s3://{bucket}/{zip_result.get('s3_key')}",
                                user_id=file_info['user_id'],
                                claim_id=file_info['claim_id'],
                                error=zip_result.get('error') if zip_result.get('status') != 'success' else None
                            )
                        except Exception as bt_error:
                            log_structured(logger, LogLevel.WARNING, "Failed to send batch tracking event for ZIP file", 
                                          error=str(bt_error), file_name=zip_result.get('file_name'))
                    
                    results.extend(zip_results)
                    continue
                
                # For regular files, queue for processing
                queue_result = queue_file_for_processing(
                    file_info, 
                    file_info.get('s3_key'), 
                    file_info.get('file_name'), 
                    uuid.UUID(file_info.get('claim_id')), 
                    uuid.UUID(file_info.get('group_id')), 
                    uuid.UUID(file_info.get('user_id'))
                )
                
                # Add batch_id to the queue result
                queue_result['batch_id'] = file_info.get('batch_id')
                results.append(queue_result)
                
                # Send batch tracking event for file queued for processing
                try:
                    file_processed(
                        batch_id=file_info.get('batch_id'),
                        file_id=file_info['file_id'],
                        success=queue_result.get('status') == 'success',
                        file_url=f"s3://{bucket}/{s3_key}",
                        user_id=file_info['user_id'],
                        claim_id=file_info['claim_id'],
                        error=queue_result.get('error') if queue_result.get('status') != 'success' else None
                    )
                    log_structured(logger, LogLevel.INFO, "Sent batch tracking event for file queued for processing", 
                                  file_id=file_info['file_id'], batch_id=file_info.get('batch_id'))
                except Exception as bt_error:
                    log_structured(logger, LogLevel.WARNING, "Failed to send batch tracking event", 
                                  error=str(bt_error), file_id=file_info['file_id'])
                
                # Create database record for the file
                try:
                    with get_db_session() as db_session:
                        file_info = create_file_record(db_session, file_info)
                        log_structured(logger, LogLevel.INFO, "Created file record", file_id=file_info.get('file_id'))
                except Exception as db_error:
                    log_structured(logger, LogLevel.ERROR, "Error creating database record", error=str(db_error))
                    # Continue processing even if database record creation fails
            
            except Exception as e:
                log_structured(logger, LogLevel.ERROR, "Error processing SQS record", error=str(e))
                results.append({
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Processed %s files" % len(results),
                "results": results
            })
        }
    except Exception as e:
        logger.exception("Error in lambda_handler: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error processing SQS event",
                "error": str(e)
            })
        }
