from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base
from sqlalchemy import Boolean

class GroupIdentity(Base):
    """
    Represents a group identity.

    Group identities are used to identify groups in the system.
    """
    __tablename__ = "group_identities"

    id: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
