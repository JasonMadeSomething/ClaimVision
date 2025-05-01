"""
Report Request Handler

This module handles incoming report requests, creates entries in the reports table,
and sends messages to the report aggregation queue.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3
from utils.access_control import has_permission
from utils.vocab_enums import PermissionAction

from database.database import get_db_session
from models.claim import Claim
from models.report import Report, ReportStatus
from models.user import User
from utils.response import api_response


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs_client = boto3.client('sqs')

# Get environment variables
REPORT_REQUEST_QUEUE_URL = os.environ.get('REPORT_REQUEST_QUEUE_URL')

def lambda_handler(event, context):
    """
    Handle incoming report requests.
    
    Creates a new entry in the reports table and sends a message to the
    report aggregation queue to start the report generation process.
    
    Parameters
    ----------
    event : dict
        The event dict containing the request parameters
    context : object
        The Lambda context object
    
    Returns
    -------
    dict
        API response with status code and message
    """
    try:
        logger.info("Processing report request")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract request parameters directly from the authorizer context
        auth_ctx = event.get("requestContext", {}).get("authorizer", {})
        user_id = auth_ctx.get("user_id")  # This matches what the JWT authorizer sets
        
        # Log the auth context for debugging
        logger.info(f"Auth context: {auth_ctx}")
        
        # Get claim_id from path parameters
        claim_id = event.get('pathParameters', {}).get('claim_id')
        report_type = body.get('report_type', 'FULL')  # Default to FULL report
        email_address = body.get('email_address')  # Get email address from request
        
        

        # Validate required parameters
        if not user_id:
            logger.warning(f"User ID not found in request: {auth_ctx}")
            return api_response(401, error_details="User ID not found in request")
        
        if not claim_id:
            return api_response(400, error_details="Claim ID is required")
            
        if not email_address:
            return api_response(400, error_details="Email address is required for report delivery")
            
        # Get database session
        session = get_db_session()
        
        try:
            # Verify user has access to claim
            user = session.query(User).filter(User.id == uuid.UUID(user_id)).first()
            if not user:
                return api_response(404, error_details="User not found")
                
            claim = session.query(Claim).filter(Claim.id == uuid.UUID(claim_id)).first()
            if not claim:
                return api_response(404, error_details="Claim not found")
                
            # Verify user has export access to claim
            success, error_response = has_permission(user, PermissionAction.EXPORT, "claim", session, resource_id=claim.id)
            if not success:
                return error_response
                
            # Create new report record
            report = Report(
                user_id=uuid.UUID(user_id),
                group_id=user.group_id,
                claim_id=uuid.UUID(claim_id),
                report_type=report_type,
                email_address=email_address,  # Store email address in the Report model
                status=ReportStatus.REQUESTED.value
            )
            
            session.add(report)
            session.commit()
            
            # Send message to report aggregation queue
            message = {
                'report_id': str(report.id),
                'user_id': user_id,
                'claim_id': claim_id,
                'group_id': str(user.group_id),
                'report_type': report_type,
                'email_address': email_address,  # Include email address in the message
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            sqs_client.send_message(
                QueueUrl=REPORT_REQUEST_QUEUE_URL,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'ReportId': {
                        'DataType': 'String',
                        'StringValue': str(report.id)
                    }
                }
            )
            
            logger.info(f"Report request created with ID: {report.id}")
            
            return api_response(
                200, 
                success_message="Report request submitted successfully",
                data={
                    'report_id': str(report.id),
                    'status': report.status,
                    'email_address': email_address
                }
            )
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            return api_response(500, error_details=f"Database error: {str(e)}")
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error processing report request: {str(e)}")
        return api_response(500, error_details=f"Error processing report request: {str(e)}")
