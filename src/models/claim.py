from sqlalchemy import String, ForeignKey, UUID, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime, timezone
from models.base import Base  

class Claim(Base):
    """
    Represents an insurance claim filed by a household.
    
    Claims contain multiple items and can have files directly associated with them.
    Each claim belongs to a specific household and tracks information about the loss event.
    """
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("households.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_loss: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now(timezone.utc), index=True)  # Added index for date queries
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    household = relationship("Household", back_populates="claims")
    files = relationship("File", back_populates="claim")
    items = relationship("Item", back_populates="claim", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="claim", cascade="all, delete-orphan")
    
    __table_args__ = (
        # Create a composite unique constraint on title and deleted per household
        # This allows the same title to exist if one is deleted and one is not
        UniqueConstraint('title', 'deleted', 'household_id', name='uq_title_deleted_household'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "household_id": str(self.household_id),
            "title": self.title,
            "description": self.description,
            "date_of_loss": self.date_of_loss.isoformat(),
            "deleted": self.deleted,
            "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None
        }
