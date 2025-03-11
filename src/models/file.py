from sqlalchemy import Column, String, ForeignKey, UUID, JSON, Enum, Boolean, DateTime
from sqlalchemy.orm import Mapped, relationship, mapped_column
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from models.item import Item
from models.item_files import item_files
from models.base import Base 
from models.label import Label
from models.file_labels import FileLabel

class FileStatus(PyEnum):
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    FAILED = "failed"

class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("households.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    room_name: Mapped[str | None] = mapped_column(String, nullable=True)  # ✅ Room is stored as a field, not a separate table
    s3_key: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[FileStatus] = mapped_column(Enum(FileStatus), default=FileStatus.UPLOADED)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("claims.id"), nullable=True)
    file_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ✅ Restored metadata field
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, default="")
    household = relationship("Household")
    user = relationship("User")
    claim = relationship("Claim", back_populates="files")
    items = relationship("Item", secondary="item_files", back_populates="files")
    labels = relationship("Label", secondary="file_labels", back_populates="files")  # ✅ Many-to-Many

    def to_dict(self):
        return {
            "id": str(self.id),
            "uploaded_by": str(self.uploaded_by),
            "household_id": str(self.household_id),
            "file_name": self.file_name,
            "room_name": self.room_name,
            "s3_key": self.s3_key,
            "status": self.status.value,
            "claim_id": str(self.claim_id) if self.claim_id else None,
            "file_metadata": self.file_metadata,
            "deleted": self.deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
