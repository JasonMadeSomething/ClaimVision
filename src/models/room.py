"""
Room model for the ClaimVision application.

This module defines the Room model, which represents a physical room
in a property associated with a claim and group.
"""
import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
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


