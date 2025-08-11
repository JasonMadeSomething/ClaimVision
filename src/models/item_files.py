from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from models.base import Base

class ItemFile(Base):
    __tablename__ = "item_files"

    item_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    file_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), index=True, nullable=False)
