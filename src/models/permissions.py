from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum, String, ForeignKey, DateTime, JSON
import uuid
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.sql import func
from models.base import Base
import enum

class PermissionAction(enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(Enum("user", "group", name="policy_subject_enum"), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(nullable=False)  # not a FK to support polymorphic subject
    resource_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g. 'claim', 'file'
    resource_id: Mapped[UUID] = mapped_column(nullable=False)
    action: Mapped[PermissionAction] = mapped_column(Enum(PermissionAction, native_enum=False))
    conditions: Mapped[dict] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


