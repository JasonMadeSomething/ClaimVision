"""
Report Zipper Handler

This module processes messages from the file organization queue,
zips the organized files, uploads them to S3, and sends the report details to an email queue.
"""

import os
import json
import logging
import uuid
import boto3
import shutil
import zipfile
import csv
from datetime import datetime, timezone
from database.database import get_db_session
from models.report import Report, ReportStatus
from models.user import User
from models.claim import Claim

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')

# Get environment variables
REPORTS_BUCKET_NAME = os.environ.get('REPORTS_BUCKET_NAME')
EFS_MOUNT_PATH = os.environ.get('EFS_MOUNT_PATH', '/mnt/reports')
EMAIL_QUEUE_URL = os.environ.get('EMAIL_QUEUE_URL')

def lambda_handler(event, context):
    """
    Process messages from the file organization queue.
    
    Zips the organized files, uploads them to S3, and sends the report details to the email queue.
    
    Parameters
    ----------
    event : dict
        The SQS event containing the report delivery message
    context : object
        The Lambda context object
    
    Returns
    -------
    dict
        Response indicating success or failure
    """
    try:
        logger.info("Processing report zipping request")
        warnings = []
        
        # Process each SQS message
        for record in event.get('Records', []):
            session = None
            report = None
            report_id = None
            
            try:
                # Parse message body
                message_body = json.loads(record.get('body', '{}'))
                
                # Extract message data
                report_id = message_body.get('report_id')
                report_dir = message_body.get('report_dir')
                report_data = message_body.get('report_data', {})  # Get the structured report data
                email_address = message_body.get('email_address')
                
                if not report_id or not report_dir:
                    logger.error("Required parameters not found in message")
                    continue
                
                if not email_address:
                    logger.error("Email address not found in message")
                    continue
                
                logger.info("Getting db session")
                # Get database session
                session = get_db_session()
                
                try:
                    logger.info("Getting report")
                    # Get the report and update status to DELIVERING
                    report = session.query(Report).filter(Report.id == uuid.UUID(report_id)).first()
                    
                    if not report:
                        logger.error("Report with ID %s not found", report_id)
                        continue
                    
                    logger.info("Updating report status to DELIVERING")
                    # Update report status
                    report.update_status(ReportStatus.DELIVERING)
                    session.commit()
                    
                    logger.info("Getting user and claim information")
                    # Get user and claim information
                    user = session.query(User).filter(User.id == report.user_id).first()
                    claim = session.query(Claim).filter(Claim.id == report.claim_id).first()
                    
                    if not user or not claim:
                        error_msg = "User or claim not found for report"
                        logger.error("%s %s", error_msg, report_id)
                        report.update_status(ReportStatus.FAILED, error_msg)
                        session.commit()
                        continue
                    
                    logger.info("Getting submission directory path")
                    # Get the submission directory path
                    submission_dir = os.path.join(report_dir, "submission")
                    
                    if not os.path.exists(submission_dir):
                        error_msg = "Submission directory not found"
                        logger.error("%s: %s", error_msg, submission_dir)
                        report.update_status(ReportStatus.FAILED, error_msg)
                        session.commit()
                        continue
                    
                    try:
                        logger.info("Generating CSV file from structured data")
                        # Generate CSV file from the structured data
                        # Items summary CSV
                        items_path = os.path.join(submission_dir, 'items_summary.csv')
                        with open(items_path, 'w', newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow([
                                'Item #', 
                                'Room', 
                                'Brand or Manufacturer', 
                                'Model#', 
                                'Item Description', 
                                'Original Vendor', 
                                'Quantity Lost', 
                                'Item Age (Years)', 
                                'Item Age (Months)', 
                                'Condition', 
                                'Cost to Replace Pre-Tax (each)', 
                                'Total Cost'
                            ])
                            
                            for item in report_data.get('items', []):
                                writer.writerow([
                                    item.get('number', ''),
                                    item.get('room', 'N/A'),
                                    item.get('brand_manufacturer', 'N/A'),
                                    item.get('model_number', 'N/A'),
                                    item.get('description', ''),
                                    item.get('original_vendor', 'N/A'),
                                    item.get('quantity', 1),
                                    item.get('age_years', 'N/A'),
                                    item.get('age_months', 'N/A'),
                                    item.get('condition', 'N/A'),
                                    f"${item.get('unit_cost', 0):.2f}" if item.get('unit_cost') is not None else 'N/A',
                                    f"${item.get('total_cost', 0):.2f}" if item.get('total_cost') is not None else 'N/A'
                                ])
                    except Exception as e:
                        error_msg = f"Error generating CSV file: {str(e)}"
                        logger.error(error_msg)
                        report.update_status(ReportStatus.FAILED, error_msg)
                        session.commit()
                        continue
                    
                    try:
                        # Create zip file
                        zip_filename = f"claim_report_{claim.title.replace(' ', '_')}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
                        zip_path = os.path.join(report_dir, zip_filename)
                        logger.info("Creating zip file at %s", zip_path)
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root, dirs, files in os.walk(submission_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    # Create relative path for the zip file - preserve the submission directory structure
                                    arcname = os.path.relpath(file_path, os.path.dirname(submission_dir))
                                    zipf.write(file_path, arcname)
                    except Exception as e:
                        error_msg = f"Error creating zip file: {str(e)}"
                        logger.error(error_msg)
                        report.update_status(ReportStatus.FAILED, error_msg)
                        session.commit()
                        continue
                    
                    try:
                        # Upload zip file to S3
                        s3_key = f"reports/{report.group_id}/{report.claim_id}/{zip_filename}"
                        logger.info("Uploading zip file to S3 at %s", s3_key)
                        
                        if not REPORTS_BUCKET_NAME:
                            error_msg = "REPORTS_BUCKET_NAME environment variable not set"
                            logger.error(error_msg)
                            report.update_status(ReportStatus.FAILED, error_msg)
                            session.commit()
                            continue
                            
                        s3_client.upload_file(
                            zip_path,
                            REPORTS_BUCKET_NAME,
                            s3_key
                        )
                        
                        # Generate a pre-signed URL for the report
                        presigned_url = s3_client.generate_presigned_url(
                            'get_object',
                            Params={
                                'Bucket': REPORTS_BUCKET_NAME,
                                'Key': s3_key
                            },
                            ExpiresIn=604800  # URL valid for 7 days
                        )
                        logger.info("Generated presigned URL: %s", presigned_url)
                    except Exception as e:
                        error_msg = f"Error uploading to S3: {str(e)}"
                        logger.error(error_msg)
                        report.update_status(ReportStatus.FAILED, error_msg)
                        session.commit()
                        continue
                    
                    # Update report with S3 key
                    report.s3_key = s3_key
                    report.update_status(ReportStatus.COMPLETED)
                    session.commit()
                    
                    # Send message to email queue
                    email_message = {
                        "report_id": str(report_id),
                        "presigned_url": presigned_url,
                        "email": email_address,
                        "recipient_name": user.first_name,
                        "claim_title": claim.title
                    }
                    
                    if EMAIL_QUEUE_URL:
                        try:
                            logger.info("Sending message to email queue: %s", EMAIL_QUEUE_URL)
                            response = sqs_client.send_message(
                                QueueUrl=EMAIL_QUEUE_URL,
                                MessageBody=json.dumps(email_message)
                            )
                            logger.info("Message sent to email queue with ID: %s", response.get('MessageId'))
                        except Exception as e:
                            error_msg = f"Error sending message to email queue: {str(e)}"
                            logger.error(error_msg)
                            warnings.append(f"Failed to send email notification: {str(e)}")
                            # Don't mark as failed since the report is already processed and stored in S3
                            # Just add a warning for monitoring
                    else:
                        warning_msg = "EMAIL_QUEUE_URL environment variable not set"
                        logger.warning(warning_msg)
                        warnings.append(warning_msg)
                    
                    logger.info("Report zipping completed for report ID: %s", report_id)
                    
                    # Clean up temporary files
                    try:
                        shutil.rmtree(report_dir)
                    except Exception as cleanup_error:
                        logger.warning("Error cleaning up temporary files: %s", str(cleanup_error))
                    
                except Exception as e:
                    error_msg = f"Error processing report: {str(e)}"
                    logger.error(error_msg)
                    if report and session:
                        try:
                            report.update_status(ReportStatus.FAILED, error_msg)
                            session.commit()
                        except Exception as db_error:
                            logger.error("Error updating report status: %s", str(db_error))
                            session.rollback()
                    else:
                        session.rollback()
                    warnings.append(f"Error processing report {report_id}: {str(e)}")
                    
                finally:
                    if session:
                        session.close()
                    
            except json.JSONDecodeError as e:
                logger.error("Error decoding JSON message: %s", str(e))
                warnings.append(f"Error decoding JSON message: {str(e)}")
            except Exception as e:
                logger.error("Error processing SQS message: %s", str(e))
                warnings.append(f"Error processing SQS message: {str(e)}")
                # Try to update the report status if we have a report_id
                if report_id:
                    try:
                        error_msg = f"Error processing SQS message: {str(e)}"
                        session = get_db_session()
                        report = session.query(Report).filter(Report.id == uuid.UUID(report_id)).first()
                        if report:
                            report.update_status(ReportStatus.FAILED, error_msg)
                            session.commit()
                        session.close()
                    except Exception as db_error:
                        logger.error("Error updating report status: %s", str(db_error))
        
        if warnings:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Report zipping completed with warnings",
                    "warnings": warnings
                })
            }
        else:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Report zipping completed successfully"
                })
            }
    
    except Exception as e:
        logger.error("Error in lambda_handler: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error processing report",
                "error": str(e)
            })
        }
