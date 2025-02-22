from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from models.base import Base
import uuid

class Household(Base):
    __tablename__ = "households"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # ✅ Ensure ID is String
    name = Column(String, nullable=False)

    users = relationship("User", back_populates="household")
    claims = relationship("Claim", back_populates="household")