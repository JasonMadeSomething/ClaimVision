from sqlalchemy import Column, String, UUID, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models.base import Base
import uuid

class Item(Base):
    """
    Represents an item in a claim.
    
    Items belong to a claim and can have multiple files associated with them.
    They can also have labels attached for categorization and searchability.
    """
    __tablename__ = "items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID, ForeignKey("claims.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    estimated_value = Column(Float, nullable=True)
    condition = Column(String, nullable=True)  # (New, Good, Average, Bad, etc.)
    is_ai_suggested = Column(Boolean, default=False)
    room_id = Column(UUID, ForeignKey("rooms.id"), nullable=True)
    
    claim = relationship("Claim", back_populates="items")
    files = relationship("File", secondary="item_files", back_populates="items")
    room = relationship("Room", back_populates="items")