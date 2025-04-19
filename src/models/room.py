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
    
    Items and files can be assigned to rooms for better organization and tracking.
    
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
    items = relationship("Item", back_populates="room", cascade="all, delete-orphan")
    files = relationship("File", back_populates="room")

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
