from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id: str = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )  # ✅ Ensure this is a String
    email: str = Column(String, unique=True, nullable=False)
    first_name: str = Column(String, nullable=False)
    last_name: str = Column(String, nullable=False)
    full_name: str = Column(String, nullable=False)
    household_id: str = Column(String, ForeignKey("households.id"), nullable=True)

    household = relationship("Household", back_populates="users")
