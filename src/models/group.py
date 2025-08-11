from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from uuid import UUID
from datetime import datetime, timezone
from models.base import Base
from models.group_membership import GroupMembership
from models.group_types import GroupType

class Group(Base):
    """
    Represents a group of users.

    Groups can be of different types (e.g., firm, partner, other).
    Each group has a name and a creator.
    """
    __tablename__ = "groups"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    group_type_id: Mapped[str] = mapped_column(ForeignKey("group_types.id"))
    group_type: Mapped["GroupType"] = relationship("GroupType", back_populates="groups")
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=text('now()')
    )
    items: Mapped[list["Item"]] = relationship("Item", back_populates="group") # noqa: F821
    claims: Mapped[list["Claim"]] = relationship("Claim", back_populates="group") # noqa: F821

    members: Mapped[list[GroupMembership]] = relationship("GroupMembership", back_populates="group")
