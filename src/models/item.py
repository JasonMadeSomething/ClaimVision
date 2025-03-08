from sqlalchemy import Column, String, ForeignKey, UUID, Enum, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from enum import Enum as PyEnum

from models.base import Base  # ✅ Restored Base import

class PriceLookupStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("households.id"), nullable=False)
    room_name: Mapped[str | None] = mapped_column(String, nullable=True)  # ✅ Stored as a field
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    price_lookup_status: Mapped[PriceLookupStatus] = mapped_column(Enum(PriceLookupStatus), default=PriceLookupStatus.PENDING)
    item_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ✅ Restored metadata

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
