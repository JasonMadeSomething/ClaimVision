from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from models.base import Base
from models.user import User
from utils.vocab_enums import MembershipStatusEnum


class GroupMembership(Base):
    __tablename__ = "group_memberships"

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    group_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("group_roles.id"), nullable=False)
    identity_id: Mapped[str] = mapped_column(ForeignKey("group_identities.id"))
    status_id: Mapped[str] = mapped_column(ForeignKey("membership_statuses.id"))

    user: Mapped[User] = relationship("User", back_populates="memberships")
    group: Mapped["Group"] = relationship("Group", back_populates="members")  # noqa: F821
    identity: Mapped["GroupIdentity"] = relationship()  # noqa: F821
    status: Mapped["MembershipStatus"] = relationship("MembershipStatus", back_populates="group_memberships")  # noqa: F821
    role: Mapped["GroupRole"] = relationship(back_populates="memberships")  # noqa: F821