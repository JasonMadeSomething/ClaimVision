"""
Room model for the ClaimVision application.

This module defines the Room model, which represents a physical room
in a property associated with a claim and household.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class Room(Base):
    """
    Room model representing a physical room in a property.
    
    Rooms are associated with a specific claim and household. Items and files
    can be assigned to rooms for better organization and tracking.
    
    Attributes:
        id (UUID): Primary key for the room
        name (str): Name of the room (e.g., "Living Room", "Kitchen")
        description (str): Optional description of the room
        household_id (UUID): Foreign key to the household that owns this room
        claim_id (UUID): Foreign key to the claim this room belongs to
        created_at (datetime): Timestamp when the room was created
        updated_at (datetime): Timestamp when the room was last updated
        deleted (bool): Soft delete flag
    """
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("households.id"), nullable=False)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("claims.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    household = relationship("Household", back_populates="rooms")
    claim = relationship("Claim", back_populates="rooms")
    items = relationship("Item", back_populates="room", cascade="all, delete-orphan")
    files = relationship("File", back_populates="room")

    # Indexes for performance
    __table_args__ = (
        Index('idx_room_household_id', household_id),
        Index('idx_room_claim_id', claim_id),
        Index('idx_room_deleted', deleted),
    )

    def to_dict(self):
        """
        Convert the Room object to a dictionary.
        
        Returns:
            dict: Dictionary representation of the Room
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "household_id": str(self.household_id),
            "claim_id": str(self.claim_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
