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
from utils.lambda_utils import extract_uuid_param, standard_lambda_handler, enhanced_lambda_handler

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

@enhanced_lambda_handler(
    requires_auth=True,
    requires_body=True,
    required_fields=['email_address'],
    path_params=['claim_id'],
    permissions={'resource_type': 'claim', 'action': 'read', 'path_param': 'claim_id'},
    auto_load_resources={'claim_id': 'Claim'},
    validation_schema={
        'email_address': {'type': str, 'pattern': r'^[^@]+@[^@]+\.[^@]+$'},
        'report_type': {'type': str, 'required': False}
    }
)
def lambda_handler(event, context, db_session, user, body, path_params, resources):
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
    db_session : Session
        SQLAlchemy database session
    user : User
        Authenticated user object
    body : dict
        Parsed and validated request body
    path_params : dict
        Extracted path parameters
    resources : dict
        Auto-loaded resources
    
    Returns
    -------
    dict
        API response with status code and message
    """
    logger.info("Processing report request")
    
    claim = resources['claim']
    claim_id = path_params['claim_id']
    report_type = body.get('report_type', 'FULL')  # Default to FULL report
    email_address = body.get('email_address')  # Already validated by schema
    
    # Create new report record  
    report = Report(
        user_id=user.id,
        group_id=user.group_id,
        claim_id=uuid.UUID(claim_id),
        report_type=report_type,
        email_address=email_address,
        status=ReportStatus.REQUESTED.value
    )
    
    db_session.add(report)
    db_session.commit()
    
    # Send message to report aggregation queue
    message = {
        'report_id': str(report.id),
        'user_id': str(user.id),
        'claim_id': claim_id,
        'group_id': str(user.group_id),
        'report_type': report_type,
        'email_address': email_address,
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
