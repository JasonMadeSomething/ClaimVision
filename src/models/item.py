from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, DateTime, Numeric
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from models.base import Base
import uuid
from datetime import datetime, timezone

class Item(Base):
    """
    Represents an item in a claim.
    
    Items belong to a claim and can have multiple files associated with them.
    They can also have labels attached for categorization and searchability.
    """
    __tablename__ = "items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(PG_UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    condition = Column(String, nullable=True)  # (New, Good, Average, Bad, etc.)
    is_ai_suggested = Column(Boolean, default=False)
    room_id = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)
    group_id = Column(PG_UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    
    # Additional fields for reporting
    brand_manufacturer = Column(String, nullable=True)
    model_number = Column(String, nullable=True)
    original_vendor = Column(String, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    age_years = Column(Integer, nullable=True)
    age_months = Column(Integer, nullable=True)
    # Monetary values use Decimal to avoid float rounding issues
    unit_cost = Column(Numeric(10, 2), nullable=False, default=0)
    deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
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