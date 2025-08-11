from sqlalchemy import String, ForeignKey, Boolean, Integer, DateTime, Numeric
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from models.base import Base
import uuid
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal

class Item(Base):
    """
    Represents an item in a claim.
    
    Items belong to a claim and can have multiple files associated with them.
    They can also have labels attached for categorization and searchability.
    """
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    condition: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # (New, Good, Average, Bad, etc.)
    is_ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False)
    room_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)
    group_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    
    # Additional fields for reporting
    brand_manufacturer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_vendor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    age_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Monetary values use Decimal to avoid float rounding issues
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    claim = relationship("Claim", back_populates="items")
    files = relationship("File", secondary="item_files", back_populates="items")
    room = relationship("Room", back_populates="items")
    group = relationship("Group", back_populates="items")
    
    def to_dict(self):
        """
        Convert the item to a dictionary representation.
        """
        return {
            "id": str(self.id),
            "claim_id": str(self.claim_id),
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "is_ai_suggested": self.is_ai_suggested,
            "room_id": str(self.room_id) if self.room_id else None,
            "brand_manufacturer": self.brand_manufacturer,
            "model_number": self.model_number,
            "original_vendor": self.original_vendor,
            "quantity": self.quantity,
            "age_years": self.age_years,
            "age_months": self.age_months,
            # Serialize Decimal as string to preserve precision for clients
            "unit_cost": str(self.unit_cost) if self.unit_cost is not None else None,
            "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') else None,
        }
    
    @property
    def total_cost(self):
        """
        Calculate the total cost of the item (quantity * unit_cost).
        """
        if self.unit_cost is not None and self.quantity is not None:
            return self.unit_cost * self.quantity
        return None