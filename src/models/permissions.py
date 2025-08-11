from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import uuid
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime, timezone
from sqlalchemy.sql import text
from models.base import Base
import enum
from typing import Optional

class PermissionAction(enum.Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(Enum("user", "group", name="policy_subject_enum"), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)  # not a FK to support polymorphic subject
    resource_type_id: Mapped[str] = mapped_column(ForeignKey("resource_types.id"), nullable=False)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[PermissionAction] = mapped_column(
        Enum(PermissionAction, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False
    )
    conditions: Mapped[dict] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=text('now()'))
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)


    resource_type = relationship("ResourceType", back_populates="permissions")
