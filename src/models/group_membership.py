from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum, ForeignKey
from uuid import UUID
from models.base import Base
from models.user import User
from models.group import Group
from models.group_identities import GroupIdentity
from models.membership_statuses import MembershipStatus

class GroupMembership(Base):
    __tablename__ = "group_memberships"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    role: Mapped[str] = mapped_column(Enum("owner", "editor", "viewer", name="group_role_enum"), nullable=False)
    identity_id: Mapped[str] = mapped_column(ForeignKey("group_identities.id"))
    status_id: Mapped[str] = mapped_column(ForeignKey("membership_statuses.id"))
    
    user: Mapped[User] = relationship("User", back_populates="memberships")
    group: Mapped[Group] = relationship("Group", back_populates="members")
    identity: Mapped[GroupIdentity] = relationship()
    status: Mapped[MembershipStatus] = relationship()