"""Claim model for PostgreSQL database."""
from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from models import Base


class Claim(Base):
    """
    Represents an insurance claim linked to a household.

    Attributes
    ----------
    id : int
        Unique identifier for the claim.
    household_id : str
        ID of the household that owns the claim.
    title : str
        Short title for the claim.
    description : Optional[str]
        Detailed description of the claim.
    created_at : str
        Timestamp in ISO 8601 format.
    status : str
        The current status of the claim.
    """

    __tablename__ = "claims"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    household_id: str = Column(
        String, ForeignKey("households.id"), nullable=False
    )  # ✅ Household ownership
    title: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(String, nullable=True)
    created_at: str = Column(String, default=lambda: datetime.now(UTC).isoformat())
    status: str = Column(String, default="open")

    # ✅ Relationships
    household = relationship("Household", back_populates="claims")
    files = relationship("File", back_populates="claim")

    def to_dict(self) -> dict:
        """Converts the SQLAlchemy model to a dictionary."""
        return {
            "id": self.id,
            "household_id": self.household_id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "status": self.status,
        }
