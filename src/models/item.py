from sqlalchemy import Column, String, UUID, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models.base import Base
import uuid

class Item(Base):
    __tablename__ = "items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID, ForeignKey("claims.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    estimated_value = Column(Float, nullable=True)
    condition = Column(String, nullable=True)  # (New, Good, Average, Bad, etc.)
    is_ai_suggested = Column(Boolean, default=False)

    claim = relationship("Claim", back_populates="items")
    files = relationship("File", secondary="item_files", back_populates="items")
