from sqlalchemy import String, UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from typing import List
from models.base import Base  # Restored Base import

class User(Base):
    """
    Represents a user of the ClaimVision system.
    
    Users belong to a household and can create/manage claims, items, and files.
    Authentication and authorization are based on the user's identity and household membership.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    cognito_sub: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    memberships: Mapped[List["GroupMembership"]] = relationship("GroupMembership", back_populates="user") # noqa: F821
    claims_created: Mapped[List["Claim"]] = relationship("Claim", back_populates="creator") # noqa: F821

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name
        }
