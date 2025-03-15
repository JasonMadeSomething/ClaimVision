from sqlalchemy import UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean
import uuid
from models.base import Base

class FileLabel(Base):
    __tablename__ = "file_labels"

    file_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    label_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self):
        return {
            "file_id": str(self.file_id),
            "label_id": str(self.label_id),
            "deleted": self.deleted
        }
