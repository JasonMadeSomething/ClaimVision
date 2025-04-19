from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from uuid import UUID
from models.base import Base

class ItemFile(Base):
    __tablename__ = "item_files"

    item_id: Mapped[UUID] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True, nullable=False)
