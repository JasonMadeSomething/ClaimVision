"""
Report Delivery Handler

This module processes messages from the file organization queue,
zips the organized files, uploads them to S3, and sends a notification email.
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
ses_client = boto3.client('ses')

# Get environment variables
REPORTS_BUCKET_NAME = os.environ.get('REPORTS_BUCKET_NAME')
EFS_MOUNT_PATH = os.environ.get('EFS_MOUNT_PATH', '/mnt/reports')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

def lambda_handler(event, context):
    """
    Process messages from the file organization queue.
    
    Zips the organized files, uploads them to S3, and sends a notification email.
    
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
        logger.info("Processing report delivery request")
        
        # Process each SQS message
        for record in event.get('Records', []):
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
                    # Update report status to DELIVERING
                    report = session.query(Report).filter(Report.id == uuid.UUID(report_id)).first()
                    
                    if not report:
                        logger.error(f"Report with ID {report_id} not found")
                        continue
                    
                    logger.info("Updating report status")
                    # Update report status
                    report.update_status(ReportStatus.DELIVERING)
                    session.commit()
                    
                    logger.info("Getting user and claim information")
                    # Get user and claim information
                    user = session.query(User).filter(User.id == report.user_id).first()
                    claim = session.query(Claim).filter(Claim.id == report.claim_id).first()
                    
                    if not user or not claim:
                        logger.error(f"User or claim not found for report {report_id}")
                        report.update_status(ReportStatus.FAILED, "User or claim not found")
                        session.commit()
                        continue
                    
                    logger.info("Getting submission directory path")
                    # Get the submission directory path
                    submission_dir = os.path.join(report_dir, "submission")
                    
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
                    
                    # Upload zip file to S3
                    s3_key = f"reports/{report.household_id}/{report.claim_id}/{zip_filename}"
                    logger.info("Uploading zip file to S3 at %s", s3_key)
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
                    
                    # Update report with S3 key
                    report.s3_key = s3_key
                    report.update_status(ReportStatus.COMPLETED)
                    session.commit()
                    
                    # Send notification email to the specified email address
                    send_notification_email(
                        email_address,  # Use the email address from the message
                        claim.title,
                        presigned_url
                    )
                    
                    logger.info(f"Report delivery completed for report ID: {report_id}")
                    
                    # Clean up temporary files
                    try:
                        shutil.rmtree(report_dir)
                    except Exception as cleanup_error:
                        logger.warning(f"Error cleaning up temporary files: {str(cleanup_error)}")
                    
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
            'body': json.dumps({'message': 'Report delivery processing completed'})
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def send_notification_email(recipient_email, claim_title, download_url):
    """
    Send a notification email to the user.
    
    Parameters
    ----------
    recipient_email : str
        The recipient's email address
    recipient_name : str
        The recipient's first name
    claim_title : str
        The title of the claim
    download_url : str
        The pre-signed URL to download the report
    """
    try:
        subject = f"Your ClaimVision Report for '{claim_title}' is Ready"
        
        # HTML body with styling
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a90e2; color: white; padding: 10px 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .button {{ display: inline-block; background-color: #4a90e2; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 4px; margin-top: 20px; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>ClaimVision Report Ready</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>Your requested report for claim <strong>"{claim_title}"</strong> is now ready for download.</p>
                    <p>The report includes a comprehensive summary of your claim, including all items, rooms, and associated files.</p>
                    <p>You can download your report by clicking the button below:</p>
                    <p style="text-align: center;">
                        <a href="{download_url}" class="button">Download Report</a>
                    </p>
                    <p>This download link will expire in 7 days. If you need access to the report after that time, 
                    please request a new report from the ClaimVision portal.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from ClaimVision. Please do not reply to this email.</p>
                    <p>&copy; {datetime.now().year} ClaimVision. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version for email clients that don't support HTML
        text_body = f"""
        Hello,
        
        Your requested report for claim "{claim_title}" is now ready for download.
        
        The report includes a comprehensive summary of your claim, including all items, rooms, and associated files.
        
        You can download your report by visiting the following URL:
        {download_url}
        
        This download link will expire in 7 days. If you need access to the report after that time, 
        please request a new report from the ClaimVision portal.
        
        This is an automated message from ClaimVision. Please do not reply to this email.
        
        &copy; {datetime.now().year} ClaimVision. All rights reserved.
        """
        
        # Send the email
        ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={
                'ToAddresses': [recipient_email]
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Text': {
                        'Data': text_body
                    },
                    'Html': {
                        'Data': html_body
                    }
                }
            }
        )
        
        logger.info(f"Notification email sent to {recipient_email}")
        
    except Exception as e:
        logger.error(f"Error sending notification email: {str(e)}")
        raise
