from uuid import UUID, uuid4
from datetime import datetime
import json
import os
import boto3

from database.database import get_db_session
from models.user import User
from models.group import Group
from models.group_membership import GroupMembership
from utils.vocab_enums import GroupTypeEnum, GroupIdentityEnum, GroupRoleEnum, MembershipStatusEnum

sqs = boto3.client("sqs")
COGNITO_UPDATE_QUEUE_URL = os.environ["COGNITO_UPDATE_QUEUE_URL"]

def lambda_handler(event, context):
    db = get_db_session()
    try:
        for record in event["Records"]:
            body = json.loads(record["body"])
            cognito_sub = body["cognito_sub"]
            email = body["email"].lower()
            name = body.get("name") or "Unnamed User"

            # Check if user already exists
            existing_user = db.query(User).filter_by(cognito_sub=cognito_sub).first()
            if existing_user:
                continue

            user_id = uuid4()

            # Create the default group (household)
            group_id = uuid4()
            group = Group(
                id=group_id,
                name=f"{name}'s Household",
                type=GroupTypeEnum.HOUSEHOLD.value,
                created_by=user_id,
                created_at=datetime.utcnow(),
            )
            db.add(group)

            # Create the user
            user = User(
                id=user_id,
                email=email,
                name=name,
                cognito_sub=cognito_sub,
                created_at=datetime.utcnow(),
            )
            db.add(user)

            # Add to group
            membership = GroupMembership(
                user_id=user_id,
                group_id=group_id,
                role=GroupRoleEnum.OWNER.value,
                identity=GroupIdentityEnum.HOMEOWNER.value,
                status=MembershipStatusEnum.ACTIVE.value,
            )
            db.add(membership)

            db.commit()

            # Optionally, trigger a follow-up Cognito update
            sqs.send_message(
                QueueUrl=COGNITO_UPDATE_QUEUE_URL,
                MessageBody=json.dumps({
                    "user_id": str(user_id),
                    "action": "registration_complete"
                })
            )

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
