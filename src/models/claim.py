from sqlalchemy import Column, String, ForeignKey, UUID, DateTime
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from models.base import Base  

class Claim(Base):
    __tablename__ = "claims"

    id: uuid.UUID = Column(UUID, primary_key=True, default=uuid.uuid4)
    household_id: uuid.UUID = Column(UUID, ForeignKey("households.id"), nullable=False)
    title: str = Column(String, nullable=False)
    description: str = Column(String, nullable=True)
    date_of_loss: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)  # ✅ Restored date of loss

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
