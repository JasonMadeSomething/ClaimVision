from models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
class GroupType(Base):
    __tablename__ = "group_types"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    groups: Mapped[list["Group"]] = relationship("Group", back_populates="group_type") # noqa: F821
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active
        }
