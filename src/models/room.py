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
    
    Rooms are stored as a static reference table. Claims can have multiple rooms
    associated with them through the ClaimRoom join table.
    
    Attributes:
        id (UUID): Primary key for the room
        name (str): Name of the room (e.g., "Living Room", "Kitchen")
        description (str): Optional description of the room
        is_active (bool): Whether the room is active
        sort_order (int): Sort order for the room
    """
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    # Relationships
    items = relationship("Item", back_populates="room")
    files = relationship("File", back_populates="room")
    claims = relationship("Claim", secondary="claim_rooms", back_populates="rooms")

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
            "is_active": self.is_active,
            "sort_order": self.sort_order
        }


class ClaimRoom(Base):
    """
    Join table for associating rooms with claims.
    
    This allows claims to have multiple rooms associated with them.
    Items and files can reference a specific room within a claim.
    
    Attributes:
        claim_id (UUID): Foreign key to the claim
        room_id (UUID): Foreign key to the room
    """
    __tablename__ = "claim_rooms"
    
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("claims.id"), primary_key=True)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("rooms.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Define indexes for faster lookups
    __table_args__ = (
        Index("ix_claim_rooms_claim_id", "claim_id"),
        Index("ix_claim_rooms_room_id", "room_id"),
    )
