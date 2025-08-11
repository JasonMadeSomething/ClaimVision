from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import text
from uuid import UUID
from models.base import Base

class FileLabel(Base):
    __tablename__ = "file_labels"

    file_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    label_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), index=True, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    __table_args__ = (
        Index(
            "uq_file_labels_active",
            "group_id",
            "file_id",
            "label_id",
            unique=True,
            postgresql_where=text("deleted = false"),
        ),
    )
    def to_dict(self):
        return {
            "file_id": str(self.file_id),
            "label_id": str(self.label_id),
            "deleted": self.deleted
        }
