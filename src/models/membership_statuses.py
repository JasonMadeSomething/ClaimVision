from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

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
    group_memberships: Mapped[list["GroupMembership"]] = relationship("GroupMembership", back_populates="status")  # noqa: F821