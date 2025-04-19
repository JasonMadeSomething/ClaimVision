from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.group_membership import GroupMembership
from models.group import Group
from sqlalchemy.sql import func

class MembershipStatus(Base):
    """
    Represents a membership status.
    
    Membership statuses are used to track the status of a user's membership in a group.
    """
    __tablename__ = "membership_statuses"

    id: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    groups: Mapped[list[Group]] = relationship("Group", back_populates="membership_statuses")
    group_memberships: Mapped[list[GroupMembership]] = relationship("GroupMembership", back_populates="status")