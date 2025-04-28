import json
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models.claim import Claim
from models.user import User
from utils.vocab_enums import MembershipStatusEnum
from utils.access_control import has_permission
from utils.lambda_utils import standard_lambda_handler
from utils.auth_utils import extract_user_id
from utils import response
from utils.logging_utils import get_logger
from models.permissions import Permission, PermissionAction
from models.resource_types import ResourceType
from models.group_membership import GroupMembership

# Configure logging
logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True, requires_body=True, required_fields=["title", "date_of_loss"])
def lambda_handler(event, context, db_session):
    body = json.loads(event["body"])

    # Get the authenticated user ID
    success, user_id_or_response = extract_user_id(event)
    if not success:
        return user_id_or_response
    
    user_id = user_id_or_response
    
    # Get the user from the database with their group memberships
    user = db_session.query(User).filter(User.cognito_sub == user_id).first()
    if not user:
        return response.api_response(404, error_details="User not found")
    
    # Get the group ID from the request or infer it from user's memberships
    group_id_raw = body.get("group_id")
    if group_id_raw:
        try:
            group_id = uuid.UUID(group_id_raw)
        except (ValueError, TypeError):
            return response.api_response(400, error_details="Invalid group ID format. Expected UUID")
    else:
        # Infer group from user's active memberships
        active_memberships = [
            m for m in user.memberships
            if m.status_id == MembershipStatusEnum.ACTIVE.value
        ]
        if len(active_memberships) == 1:
            group_id = active_memberships[0].group_id
        elif len(active_memberships) == 0:
            return response.api_response(400, error_details="You are not part of any active group.")
        else:
            return response.api_response(400, error_details="Multiple active groups found. Please specify which group to use.")

    if not has_permission(user, action=PermissionAction.WRITE, resource_type="claim", group_id=group_id, db=db_session):
        return response.api_response(403, error_details="You do not have permission to create claims in this group")

    # Validate title
    title = body["title"].strip()
    if not title:
        return response.api_response(400, error_details="Title cannot be empty")

    # Validate and parse date_of_loss
    try:
        date_of_loss = datetime.strptime(body["date_of_loss"], "%Y-%m-%d").date()
        if date_of_loss > datetime.now().date():
            return response.api_response(400, error_details="Date of loss cannot be in the future")
    except ValueError:
        return response.api_response(400, error_details="Invalid date format. Expected YYYY-MM-DD")

    try:
        new_claim = Claim(
            title=title,
            description=body.get("description", ""),
            date_of_loss=date_of_loss,
            group_id=group_id,
            created_by=user.id
        )
        db_session.add(new_claim)
        db_session.commit()
        db_session.refresh(new_claim)

        logger.info("Claim %s created by user %s in group %s", new_claim.id, user.id, group_id)
        
        resource_types = db_session.query(ResourceType).filter(
            ResourceType.id.in_(["claim", "file", "item"])
        ).all()
        resource_map = {r.id: r for r in resource_types}
        
        logger.info("Resource types loaded: %s", resource_map)

        permissions = []

        # Claim permissions
        for action in [PermissionAction.READ, PermissionAction.WRITE, PermissionAction.DELETE]:
            logger.info("Creating permission with action %s for user %s on claim %s", action, user.id, new_claim.id)
            permissions.append(Permission(
                subject_type="user",
                subject_id=user.id,
                action=action,
                resource_type_id=resource_map["claim"].id,
                resource_id=new_claim.id
            ))

        # File and Item creation permissions scoped to the claim
        for resource_id in ["file", "item"]:
            logger.info("Creating file/item permission for resource %s", resource_id)
            permissions.append(Permission(
                subject_type="user",
                subject_id=user.id,
                action=PermissionAction.WRITE,
                resource_type_id=resource_map[resource_id].id,
                resource_id=new_claim.id
            ))

        logger.info("Adding %d permissions to the database", len(permissions))
        db_session.add_all(permissions)
        db_session.commit()
        # Prepare response data
        claim_data = {
            "id": str(new_claim.id),
            "title": new_claim.title,
            "description": new_claim.description,
            "date_of_loss": new_claim.date_of_loss.strftime("%Y-%m-%d"),
            "group_id": str(new_claim.group_id)
        }
        
        return response.api_response(201, data=claim_data, success_message="Claim created successfully")

    except IntegrityError as e:
        db_session.rollback()
        if "duplicate key" in str(e.orig):
            return response.api_response(409, error_details="A claim with similar data already exists")
        return response.api_response(500, error_details="Database error: " + str(e))

    except Exception as e:
        db_session.rollback()
        logger.exception("Error creating claim")
        return response.api_response(500, error_details="An unexpected error occurred: " + str(e))
