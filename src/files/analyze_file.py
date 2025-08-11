"""
Lambda handler for analyzing files using AWS Rekognition.

This module is triggered by the analysis SQS queue and handles:
1. Getting the file from S3
2. Sending the file to AWS Rekognition for analysis
3. Storing the analysis results in the database
4. Sending batch tracking events for analysis status
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
from batch.batch_tracker import analysis_started, analysis_completed

logger = get_logger(__name__)

# Get the actual bucket name, not the SSM parameter path
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
if S3_BUCKET_NAME and S3_BUCKET_NAME.startswith('/'):
    # If it looks like an SSM parameter path, use a default for local testing
    logger.warning(
        "S3_BUCKET_NAME appears to be an SSM parameter path: %s. Using default bucket for local testing.",
        S3_BUCKET_NAME,
    )
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

def is_image(s3_key: str) -> bool:
    """
    Checks if a file is an image based on its extension.

    Args:
        s3_key (str): The S3 key for the file

    Returns:
        bool: True if the file is an image, False otherwise
    """
    file_extension = s3_key.split(".")[-1].lower() if "." in s3_key else ""
    image_extensions = {"jpg", "jpeg", "png"}

    return file_extension in image_extensions

def lambda_handler(event, _context):
    """
    Process SQS events containing file analysis requests.

    Args:
        event (dict): SQS event containing file analysis requests
        context: Lambda execution context

    Returns:
        dict: Processing result
    """
    logger.info("Starting file analysis processing")

    try:
        # Initialize results
        results = []

        # Process each SQS record
        for record in event.get('Records', []):
            try:
                # Extract file info from SQS message
                message_body = json.loads(record.get('body', '{}'))
                logger.debug("Processing SQS message: %s", message_body)

                # Extract file information
                file_id = message_body.get('file_id')
                s3_key = message_body.get('s3_key')
                batch_id = message_body.get('batch_id')

                # Skip if missing required information
                if not file_id or not s3_key:
                    logger.error("Missing file_id or s3_key in SQS message: %s", message_body)
                    continue

                # Check if the file is an image
                if not is_image(s3_key):
                    logger.info("File %s is not an image, skipping analysis", file_id)
                    results.append({
                        "file_id": file_id,
                        "status": "skipped",
                        "reason": "not an image"
                    })
                    continue

                # Get file from database
                with get_db_session() as db_session:
                    file = db_session.query(File).filter(File.id == uuid.UUID(file_id)).first()

                    if not file:
                        logger.error("File %s not found in database", file_id)
                        results.append({
                            "file_id": file_id,
                            "status": "error",
                            "error": "File not found in database"
                        })
                        continue

                    # Get user_id and claim_id for batch tracking
                    user_id = str(file.uploaded_by) if getattr(file, 'uploaded_by', None) else None
                    claim_id = str(file.claim_id) if file.claim_id else None

                    # If batch_id is not in the message, check if it's stored in the file record
                    if not batch_id and hasattr(file, 'batch_id') and file.batch_id:
                        batch_id = file.batch_id
                        logger.info("Retrieved batch_id from file record: %s", batch_id)

                    # If still no batch_id, log error but continue processing
                    if not batch_id:
                        logger.error("No batch_id found for file %s, batch tracking disabled", file_id)
                        # We'll still process the file but won't send batch tracking events
                        batch_id = None
                        user_id = None
                        claim_id = None

                # Analyze file with Rekognition
                try:
                    # Send batch tracking event for analysis started
                    if batch_id:
                        try:
                            analysis_started(
                                batch_id=batch_id,
                                file_id=file_id,
                                user_id=user_id,
                                claim_id=claim_id
                            )
                            logger.info("Sent batch tracking event for analysis started: %s", file_id)
                        except Exception as bt_error:
                            logger.warning(
                                "Failed to send batch tracking event for analysis started: %s",
                                str(bt_error),
                            )

                    labels = detect_labels(s3_key)
                    logger.info("File %s analyzed with %d labels detected", file_id, len(labels))
                    seen_labels = set()

                    with get_db_session() as db_session:
                        file = db_session.query(File).filter(File.id == uuid.UUID(file_id)).first()

                        if not file:
                            logger.error(
                                "File %s not found in database when storing analysis results",
                                file_id,
                            )
                            results.append({
                                "file_id": file_id,
                                "status": "error",
                                "error": "File not found in database when storing analysis results"
                            })

                            # Send batch tracking event for analysis failure
                            if batch_id:
                                try:
                                    analysis_completed(
                                        batch_id=batch_id,
                                        file_id=file_id,
                                        success=False,
                                        labels=[],
                                        error="File not found in database when storing analysis results",
                                        user_id=user_id,
                                        claim_id=claim_id
                                    )
                                except Exception as bt_error:
                                    logger.warning(
                                        "Failed to send batch tracking event for analysis failure: %s",
                                        str(bt_error),
                                    )

                            continue

                        # Store labels in database
                        file_labels = []
                        for label_data in labels:
                            label_name = label_data.get('Name', '').lower()

                            # Skip duplicates
                            if label_name in seen_labels:
                                continue
                            seen_labels.add(label_name)

                            # Get or create label (scoped by group and AI flag)
                            label = db_session.query(Label).filter(
                                Label.label_text == label_name,
                                Label.group_id == file.group_id,
                                Label.is_ai_generated.is_(True)
                            ).first()
                            if not label:
                                label = Label(
                                    label_text=label_name,
                                    group_id=file.group_id,
                                    is_ai_generated=True
                                )
                                db_session.add(label)
                                db_session.flush()

                            # Create file-label association
                            file_label = FileLabel(
                                file_id=file.id,
                                label_id=label.id,
                                group_id=file.group_id
                            )
                            db_session.add(file_label)
                            file_labels.append({
                                "name": label_name,
                                "confidence": label_data.get('Confidence', 0)
                            })

                        # Update file status
                        file.status = FileStatus.ANALYZED
                        file.updated_at = datetime.now(timezone.utc)

                        db_session.commit()

                        # Send batch tracking event for analysis completion
                        if batch_id:
                            try:
                                analysis_completed(
                                    batch_id=batch_id,
                                    file_id=file_id,
                                    success=True,
                                    labels=file_labels,
                                    user_id=user_id,
                                    claim_id=claim_id
                                )
                                logger.info("Sent batch tracking event for analysis completion: %s", file_id)
                            except Exception as bt_error:
                                logger.warning(
                                    "Failed to send batch tracking event for analysis completion: %s",
                                    str(bt_error),
                                )

                        logger.info("File %s analysis results stored in database", file_id)

                except Exception as e:
                    logger.exception("Error analyzing file %s: %s", file_id, str(e))
                    results.append({
                        "file_id": file_id,
                        "status": "error",
                        "error": str(e)
                    })

                    # Send batch tracking event for analysis failure
                    if batch_id:
                        try:
                            analysis_completed(
                                batch_id=batch_id,
                                file_id=file_id,
                                success=False,
                                labels=[],
                                error=str(e),
                                user_id=user_id,
                                claim_id=claim_id
                            )
                            logger.info("Sent batch tracking event for analysis failure: %s", file_id)
                        except Exception as bt_error:
                            logger.warning(
                                "Failed to send batch tracking event for analysis failure: %s",
                                str(bt_error),
                            )

                    continue

                results.append({
                    "file_id": file_id,
                    "status": "success",
                    "labels_count": len(seen_labels)
                })

            except Exception as e:
                logger.exception("Error processing SQS record: %s", str(e))
                results.append({
                    "status": "error",
                    "error": str(e)
                })

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Processed {len(results)} files",
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
