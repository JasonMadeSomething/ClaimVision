from sqlalchemy import Column, String, ForeignKey, UUID, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime, timezone
from models.base import Base  

class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("households.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_loss: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now(timezone.utc))  # ✅ Restored date of loss

    household = relationship("Household", back_populates="claims")
    files = relationship("File", back_populates="claim")

    def to_dict(self):
        return {
            "id": str(self.id),
            "household_id": str(self.household_id),
            "title": self.title,
            "description": self.description,
            "date_of_loss": self.date_of_loss.isoformat()
        }
