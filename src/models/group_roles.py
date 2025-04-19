from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from typing import Optional
from models.group_membership import GroupMembership

class GroupRole(Base):
    """
    Represents a role within a group.
    
    Group roles define the permissions and responsibilities of users within a group.
    """
    __tablename__ = "group_roles"

    id: Mapped[str] = mapped_column(primary_key=True)  # "owner", "editor", etc.
    label: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    memberships: Mapped[list[GroupMembership]] = relationship("GroupMembership", back_populates="role")
