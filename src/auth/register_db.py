import json
import os
import logging
from uuid import uuid4
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from database.database import get_db_session
from models.user import User
from models.group import Group
from models.group_membership import GroupMembership
from models.permissions import Permission, PermissionAction
from models.resource_types import ResourceType
from utils.vocab_enums import GroupTypeEnum, GroupRoleEnum, GroupIdentityEnum, MembershipStatusEnum
from utils.response import api_response

logger = logging.getLogger(__name__)

sqs = boto3.client("sqs")
COGNITO_UPDATE_QUEUE_URL = os.environ["COGNITO_UPDATE_QUEUE_URL"]

def process_user(db, cognito_sub, email, first_name, last_name):
    # Check if user already exists
    existing_user = db.query(User).filter_by(cognito_sub=cognito_sub).first()
    if existing_user:
        return

    user_id = uuid4()

    user = User(
        id=user_id,
        email=email.lower(),
        first_name=first_name,
        last_name=last_name,
        cognito_sub=cognito_sub
    )
    db.add(user)

    db.flush()

    # Create the default group (household)
    group_id = uuid4()
    group = Group(
        id=group_id,
        name=f"{first_name} {last_name}'s Household",
        group_type_id=GroupTypeEnum.HOUSEHOLD.value,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(group)

    # Add to group
    membership = GroupMembership(
        user_id=user_id,
        group_id=group_id,
        role_id=GroupRoleEnum.OWNER.value,
        identity_id=GroupIdentityEnum.HOMEOWNER.value,
        status_id=MembershipStatusEnum.ACTIVE.value,
    )
    db.add(membership)
    db.flush()

    claim_resource = db.query(ResourceType).filter_by(id="claim").first()
    if claim_resource:
        # Create permissions for the user in the group
        # Use PermissionAction enum objects consistently
        for action in [PermissionAction.READ.value, PermissionAction.WRITE.value]:
            permission = Permission(
                subject_id=user_id,
                subject_type="user",
                action=action,
                resource_type_id=claim_resource.id,
                group_id=group_id,
                created_by=user_id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(permission)

    # Optionally, trigger a follow-up Cognito update
    if COGNITO_UPDATE_QUEUE_URL:
        try:
            sqs.send_message(
                QueueUrl=COGNITO_UPDATE_QUEUE_URL,
                MessageBody=json.dumps({
                    "cognito_sub": cognito_sub,
                    "user_id": str(user_id)
                })
            )
        except (BotoCoreError, ClientError) as e:
            # Log the specific AWS error but continue processing
            print(f"Error sending SQS message: {str(e)}")

def lambda_handler(event, context):
    db = get_db_session()
    try:
        # Process each record
        for record in event["Records"]:
            # Extract the message body
            body = json.loads(record["body"])
            
            # Extract user details
            cognito_sub = body.get("cognito_sub")
            email = body.get("email")
            first_name = body.get("first_name", "")
            last_name = body.get("last_name", "")
            
            # Create or update the user in the database
            process_user(db, cognito_sub, email, first_name, last_name)
        
        # Commit the transaction
        db.commit()
        
        # Send a success response
        return api_response(
            status_code=200,
            success_message="User registration processed successfully"
        )
    except (SQLAlchemyError, boto3.exceptions.Boto3Error) as e:
        # Roll back the transaction in case of error
        db.rollback()
        
        # Log the error
        logger.error(f"Error processing user registration: {str(e)}")
        
        # Return an error response
        return api_response(
            status_code=500,
            error_details=f"Error processing user registration: {str(e)}"
        )
    finally:
        db.close()
