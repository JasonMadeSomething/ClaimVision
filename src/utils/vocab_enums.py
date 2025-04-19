from enum import Enum

class GroupTypeEnum(str, Enum):
    HOUSEHOLD = "household"
    FIRM = "firm"
    PARTNER = "partner"
    OTHER = "other"

class GroupRoleEnum(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"

class GroupIdentityEnum(str, Enum):
    HOMEOWNER = "homeowner"
    ADJUSTER = "adjuster"
    CONTRACTOR = "contractor"
    OTHER = "other"

class MembershipStatusEnum(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    REVOKED = "revoked"

class PermissionAction(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"

class ResourceTypeEnum(str, Enum):
    CLAIM = "claim"
    FILE = "file"
    ITEM = "item"
    LABEL = "label"
    ROOM = "room"
    REPORT = "report"
