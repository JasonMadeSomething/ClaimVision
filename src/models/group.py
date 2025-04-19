from sqlalchemy import Enum, ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid
from uuid import UUID
from datetime import datetime, timezone
from models.base import Base
from models.group_membership import GroupMembership
from models.group_types import GroupType

class Group(Base):
    """
    Represents a group of users.
    
    Groups can be of different types (e.g., household, firm, partner, other).
    Each group has a name and a creator.
    """
    __tablename__ = "groups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    group_type_id: Mapped[str] = mapped_column(ForeignKey("group_types.id"))
    group_type: Mapped["GroupType"] = relationship("GroupType", back_populates="groups")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    members: Mapped[list[GroupMembership]] = relationship("GroupMembership", back_populates="group")
