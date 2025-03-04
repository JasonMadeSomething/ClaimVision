from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, UUID, Enum, JSON
from sqlalchemy.orm import relationship
import uuid
from enum import Enum as PyEnum

from models.base import Base  # ✅ Restored Base import

class PriceLookupStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class Item(Base):
    __tablename__ = "items"

    id: uuid.UUID = Column(UUID, primary_key=True, default=uuid.uuid4)
    household_id: uuid.UUID = Column(UUID, ForeignKey("households.id"), nullable=False)
    room_name: str = Column(String, nullable=True)  # ✅ Stored as a field
    description: str = Column(String, nullable=True)
    price_lookup_status: PriceLookupStatus = Column(Enum(PriceLookupStatus), default=PriceLookupStatus.PENDING)
    item_metadata: dict = Column(JSON, nullable=True)  # ✅ Restored metadata

    files = relationship("File", secondary="item_files", back_populates="items")

    def to_dict(self):
        return {
            "id": str(self.id),
            "household_id": str(self.household_id),
            "room_name": self.room_name,
            "description": self.description,
            "price_lookup_status": self.price_lookup_status.value,
            "item_metadata": self.item_metadata
        }
