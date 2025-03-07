from sqlalchemy import Column, String, UUID
from sqlalchemy.orm import relationship
import uuid
from models.base import Base  # ✅ Restored Base import

class Household(Base):
    __tablename__ = "households"

    id: uuid.UUID = Column(UUID, primary_key=True, default=uuid.uuid4)
    name: str = Column(String, nullable=False)

    users = relationship("User", back_populates="household")
    claims = relationship("Claim", back_populates="household")
    files = relationship("File", back_populates="household")

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name
        }
