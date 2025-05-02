import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base

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
