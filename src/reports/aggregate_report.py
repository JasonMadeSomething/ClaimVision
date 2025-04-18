"""
Report Aggregation Handler

This module processes messages from the report request queue,
aggregates claim data, and sends batch messages to the file organization queue.
"""

import os
import json
import logging
import uuid
import boto3
from datetime import datetime, timezone
from database.database import get_db_session
from models.report import Report, ReportStatus
from models.claim import Claim

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')

# Get environment variables
FILE_ORGANIZATION_QUEUE_URL = os.environ.get('FILE_ORGANIZATION_QUEUE_URL')

def lambda_handler(event, context):
    """
    Process messages from the report request queue.
    
    Aggregates claim data and sends batch messages to the file organization queue.
    
    Parameters
    ----------
    event : dict
        The SQS event containing the report request message
    context : object
        The Lambda context object
    
    Returns
    -------
    dict
        Response indicating success or failure
    """
    try:
        logger.info("Processing report aggregation request")
        
        # Process each SQS message
        for record in event.get('Records', []):
            try:
                # Parse message body
                message_body = json.loads(record.get('body', '{}'))
                
                # Extract message data
                report_id = message_body.get('report_id')
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
                    # Update report status to AGGREGATING
                    report = session.query(Report).filter(Report.id == uuid.UUID(report_id)).first()
                    
                    if not report:
                        logger.error(f"Report with ID {report_id} not found")
                        continue
                    
                    # Update report status
                    report.update_status(ReportStatus.AGGREGATING)
                    session.commit()
                    
                    # Get claim data
                    claim = session.query(Claim).filter(Claim.id == report.claim_id).first()
                    
                    if not claim:
                        logger.error(f"Claim with ID {report.claim_id} not found")
                        report.update_status(ReportStatus.FAILED, "Claim not found")
                        session.commit()
                        continue
                    
                    # Generate structured report data using the Claim's method
                    report_data = claim.generate_report_data(session)
                    
                    # Send message to file organization queue
                    message = {
                        'report_id': report_id,
                        'report_data': report_data,
                        'email_address': email_address,  # Pass email address to next step
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    sqs_client.send_message(
                        QueueUrl=FILE_ORGANIZATION_QUEUE_URL,
                        MessageBody=json.dumps(message),
                        MessageAttributes={
                            'ReportId': {
                                'DataType': 'String',
                                'StringValue': report_id
                            }
                        }
                    )
                    
                    logger.info(f"Report aggregation completed for report ID: {report_id}")
                    
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
            'body': json.dumps({'message': 'Report aggregation processing completed'})
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
