from functools import wraps
from typing import Callable, Any
from uuid import UUID

from models import User, Claim, File, Item, Label, Report
from models.group_membership import GroupMembership
from models.permissions import Permission

from database.database import Session


class AccessDeniedError(Exception):
    pass


class ResourceNotFoundError(Exception):
    pass


RESOURCE_MODEL_MAP = {
    "claim": Claim,
    "file": File,
    "item": Item,
    "label": Label,
    "report": Report,
}

def load_resource(resource_type: str, resource_id: UUID, db: Session):
    model = RESOURCE_MODEL_MAP.get(resource_type)
    if not model:
        raise ValueError(f"Unsupported resource type: {resource_type}")
    resource = db.query(model).filter(model.id == resource_id).first()
    if not resource:
        raise ResourceNotFoundError(f"{resource_type} with id {resource_id} not found")
    return resource


def can_access(user: User, resource: Any, action: str, db: Session) -> bool:
    # 1. User belongs to the owning group
    if hasattr(resource, "group_id") and resource.group_id:
        membership = db.query(GroupMembership).filter_by(
            user_id=user.id, group_id=resource.group_id, status="active"
        ).first()
        if membership:
            return True

    # 2. Group-level permission
    group_ids = [m.group_id for m in user.memberships if m.status == "active"]
    if group_ids:
        group_perm = db.query(Permission).filter_by(
            subject_type="group",
            resource_type=resource.__class__.__name__.lower(),
            resource_id=resource.id,
            action=action
        ).filter(Permission.subject_id.in_(group_ids)).first()
        if group_perm:
            return True

    # 3. User-level permission
    user_perm = db.query(Permission).filter_by(
        subject_type="user",
        subject_id=user.id,
        resource_type=resource.__class__.__name__.lower(),
        resource_id=resource.id,
        action=action
    ).first()
    return bool(user_perm)


def check_access(user: User, resource: Any, action: str, db: Session) -> None:
    if not can_access(user, resource, action, db):
        raise AccessDeniedError(f"User {user.id} cannot {action} this {resource.__class__.__name__}.")

def has_permission(
    user: User,
    action: str,
    resource_type: str,
    db: Session,
    resource_id: UUID | None = None,
    group_id: UUID | None = None,
) -> bool:
    # 1. Check direct user permission
    query = db.query(Permission).filter_by(
        subject_type="user",
        subject_id=user.id,
        resource_type=resource_type,
        action=action,
    )
    if resource_id:
        query = query.filter_by(resource_id=resource_id)
    if query.first():
        return True

    # 2. Check group-based permission
    group_ids = [m.group_id for m in user.memberships if m.status == "active"]
    if group_id and group_id not in group_ids:
        return False  # Cannot check permission in a group you're not a member of

    group_query = db.query(Permission).filter(
        Permission.subject_type == "group",
        Permission.subject_id.in_(group_ids),
        Permission.resource_type == resource_type,
        Permission.action == action,
    )
    if resource_id:
        group_query = group_query.filter_by(resource_id=resource_id)

    return bool(group_query.first())


def secured(resource_type: str, action: str):
    """
    Decorator to enforce access control on a resource by ID from pathParameters.
    Expects the handler to accept (event, context, user, resource, db_session).
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(event, context, user: User, db_session: Session, **kwargs):
            resource_id = event.get("pathParameters", {}).get("id")
            if not resource_id:
                raise ValueError("Missing 'id' path parameter")
            resource = load_resource(resource_type, UUID(resource_id), db_session)
            check_access(user, resource, action, db_session)
            return func(event, context, user=user, db_session=db_session, **{resource_type: resource, **kwargs})

        return wrapper
    return decorator