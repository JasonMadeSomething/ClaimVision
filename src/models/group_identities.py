from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base
from models.group import Group
from sqlalchemy.orm import relationship

class GroupIdentity(Base):
    """
    Represents a group identity.
    
    Group identities are used to identify groups in the system.
    """
    __tablename__ = "group_identities"

    id: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    groups: Mapped[list[Group]] = relationship("Group", back_populates="group_identities")
