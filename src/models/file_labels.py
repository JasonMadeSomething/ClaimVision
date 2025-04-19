from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, ForeignKey
from uuid import UUID
from models.base import Base

class FileLabel(Base):
    __tablename__ = "file_labels"

    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    label_id: Mapped[UUID] = mapped_column(ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    def to_dict(self):
        return {
            "file_id": str(self.file_id),
            "label_id": str(self.label_id),
            "deleted": self.deleted
        }
