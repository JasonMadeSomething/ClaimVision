"""
Lambda handler for analyzing files using AWS Rekognition.

This module is triggered by the analysis SQS queue and handles:
1. Getting the file from S3
2. Sending the file to AWS Rekognition for analysis
3. Storing the analysis results in the database
"""
import os
import json
import uuid
from datetime import datetime, timezone
from utils.logging_utils import get_logger
from utils.lambda_utils import get_rekognition_client
from models.file import FileStatus, File
from models.label import Label
from models.file_labels import FileLabel
from database.database import get_db_session

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(f"S3_BUCKET_NAME appears to be an SSM parameter path: {S3_BUCKET_NAME}. Using default bucket for local testing.")
    S3_BUCKET_NAME = "claimvision-dev-bucket"

MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "70.0"))  # Minimum confidence for labels

def detect_labels(s3_key: str) -> list:
    """
    Detects labels in an image using AWS Rekognition.
    
    Args:
        s3_key (str): The S3 key for the image
        
    Returns:
        list: List of detected labels
    """
    rekognition = get_rekognition_client()
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME environment variable is not set")
        
    response = rekognition.detect_labels(
        Image={
            'S3Object': {
                'Bucket': S3_BUCKET_NAME,
                'Name': s3_key
            }
        },
        MinConfidence=MIN_CONFIDENCE
    )
    
    return [{"Name": label["Name"], "Confidence": label["Confidence"]} for label in response.get('Labels', [])]

def lambda_handler(event, context):
    """
    Analyzes files from the analysis SQS queue.
    
    Args:
        event (dict): SQS event containing file metadata
        context (dict): Lambda execution context
        
    Returns:
        dict: Analysis status
    """
    logger.info("Processing file analysis from SQS")
    
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
                s3_key = message_body['s3_key']
                file_name = message_body['file_name']
                
                # Get the file from the database
                file = db_session.query(File).filter_by(id=file_id).first()
                if not file:
                    logger.error(f"File {file_id} not found in database")
                    continue
                
                # Check if file is an image (only images can be analyzed with Rekognition)
                file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
                image_extensions = {"jpg", "jpeg", "png"}
                
                if file_extension not in image_extensions:
                    logger.info(f"File {file_id} is not an image, skipping analysis")
                    
                    # Update file status to ANALYZED (even though we're skipping analysis)
                    file.status = FileStatus.ANALYZED
                    file.updated_at = datetime.now(timezone.utc)
                    db_session.commit()
                    
                    continue
                    
                # Analyze file with Rekognition
                try:
                    labels = detect_labels(s3_key)
                    logger.info(f"File {file_id} analyzed with {len(labels)} labels detected")
                    
                    # Store labels in database
                    for label_data in labels:
                        label_name = label_data['Name']
                        # We don't need confidence since the Label model doesn't store it
                        
                        # Check if label already exists
                        existing_label = db_session.query(Label).filter_by(
                            label_text=label_name,
                            is_ai_generated=True,
                            household_id=file.household_id
                        ).first()
                        
                        if not existing_label:
                            # Create new label
                            existing_label = Label(
                                id=uuid.uuid4(),
                                label_text=label_name,
                                is_ai_generated=True,
                                household_id=file.household_id
                            )
                            db_session.add(existing_label)
                            db_session.flush()  # Flush to get the ID
                        
                        # Create file-label association
                        file_label = FileLabel(
                            file_id=file_id,
                            label_id=existing_label.id
                        )
                        db_session.add(file_label)
                    
                    # Update file status
                    file.status = FileStatus.ANALYZED
                    file.updated_at = datetime.now(timezone.utc)
                    
                    db_session.commit()
                    logger.info(f"File {file_id} analysis results stored in database")
                    
                except Exception as e:
                    logger.error(f"Failed to analyze file {file_id}: {str(e)}")
                    
                    # Update file status to ERROR
                    try:
                        file.status = FileStatus.ERROR
                        file.updated_at = datetime.now(timezone.utc)
                        db_session.commit()
                    except Exception as db_error:
                        logger.error(f"Failed to update file {file_id} status: {str(db_error)}")
                    
                    continue
                    
            except Exception as e:
                logger.error(f"Failed to process SQS message: {str(e)}")
                continue
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "File analysis complete"
            })
        }
    finally:
        # Always close the database session
        db_session.close()
