"""
Email Report Handler

This module processes messages from the email queue and sends notification emails using SES.
This Lambda runs outside the VPC to access SES, which is only available from the public internet.
"""

import os
import json
import logging
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses_client = boto3.client('ses')

# Get environment variables
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')

def lambda_handler(event, _):  # Renamed context to _ since it's unused
    """
    Process messages from the email queue and send notification emails.
    
    Parameters
    ----------
    event : dict
        The SQS event containing the email message
    _ : object
        The Lambda context object (unused)
    
    Returns
    -------
    dict
        Response indicating success or failure
    """
    try:
        logger.info("Processing email report request")
        results = []
        
        # Process each SQS message
        for record in event.get('Records', []):
            try:
                # Parse message body
                message_body = json.loads(record.get('body', '{}'))
                
                # Extract message data
                report_id = message_body.get('report_id')
                presigned_url = message_body.get('presigned_url')
                email = message_body.get('email')
                recipient_name = message_body.get('recipient_name', 'Valued Customer')
                claim_title = message_body.get('claim_title', 'Your Claim')
                
                if not report_id or not presigned_url or not email:
                    error_msg = "Required parameters not found in message"
                    logger.error(error_msg)
                    results.append({
                        "success": False,
                        "report_id": report_id,
                        "error": error_msg
                    })
                    continue
                
                # Send notification email
                success = send_notification_email(
                    email,
                    recipient_name,
                    claim_title,
                    presigned_url
                )
                
                results.append({
                    "success": success,
                    "report_id": report_id,
                    "email": email
                })
                
            except json.JSONDecodeError as e:
                logger.error("Error decoding JSON message: %s", str(e))
                results.append({
                    "success": False,
                    "error": f"JSON decode error: {str(e)}"
                })
            except KeyError as e:
                logger.error("Missing key in message: %s", str(e))
                results.append({
                    "success": False,
                    "error": f"Missing key: {str(e)}"
                })
            except Exception as e:
                logger.error("Error processing SQS message: %s", str(e))
                results.append({
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Email processing completed",
                "results": results
            })
        }
    
    except Exception as e:
        logger.error("Error in lambda_handler: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error processing email",
                "error": str(e)
            })
        }

def send_notification_email(recipient_email, recipient_name, claim_title, download_url):
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
    
    Returns
    -------
    bool
        True if email was sent successfully, False otherwise
    """
    if not SENDER_EMAIL:
        logger.error("SENDER_EMAIL environment variable not set")
        return False
    
    # Create the email subject
    subject = f"Your ClaimVision Report for {claim_title} is Ready"
    
    # Create the email body
    html_body = f"""
    <html>
    <head></head>
    <body>
        <h1>Your ClaimVision Report is Ready</h1>
        <p>Hello {recipient_name},</p>
        <p>Your report for claim <strong>{claim_title}</strong> has been successfully generated and is now ready for download.</p>
        <p>You can download your report by clicking the button below:</p>
        <p style="text-align: center;">
            <a href="{download_url}" style="background-color: #4CAF50; border: none; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 12px;">
                Download Report
            </a>
        </p>
        <p>This download link will expire in 7 days. If you need access to your report after this period, please contact support.</p>
        <p>Thank you for using ClaimVision!</p>
        <p>Best regards,<br>The ClaimVision Team</p>
    </body>
    </html>
    """
    
    text_body = f"""
    Your ClaimVision Report is Ready
    
    Hello {recipient_name},
    
    Your report for claim '{claim_title}' has been successfully generated and is now ready for download.
    
    You can download your report by visiting the following link:
    {download_url}
    
    This download link will expire in 7 days. If you need access to your report after this period, please contact support.
    
    Thank you for using ClaimVision!
    
    Best regards,
    The ClaimVision Team
    """
    
    try:
        # Send the email
        response = ses_client.send_email(
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
        logger.info("Email sent successfully! Message ID: %s", response['MessageId'])
        return True
    except ClientError as e:
        logger.error("Error sending email: %s", e.response['Error']['Message'])
        return False
    except Exception as e:
        logger.error("Unexpected error sending email: %s", str(e))
        return False
