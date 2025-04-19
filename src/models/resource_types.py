from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base

class ResourceType(Base):
    __tablename__ = "resource_types"

    id: Mapped[str] = mapped_column(primary_key=True)  # e.g. 'claim', 'file'
    label: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
