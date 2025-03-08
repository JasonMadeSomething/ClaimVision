from sqlalchemy import Column, String, ForeignKey, UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from models.base import Base  # ✅ Restored Base import

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("households.id"), nullable=False)
    
    household = relationship("Household", back_populates="users")

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "household_id": str(self.household_id)
        }
