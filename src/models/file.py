from sqlalchemy import String, ForeignKey, JSON, Enum, Boolean, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import text
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from models.base import Base

class FileStatus(PyEnum):
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    FAILED = "failed"
    ANALYZED = "analyzed"
    SKIPPED_ANALYSIS = "skipped_analysis"
    ERROR = "error"

class File(Base):
    """
    Represents a file uploaded by a user.

    Files can be associated with claims and items, and can have labels attached.
    Files are stored in S3 with their metadata tracked in the database.
    """
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    s3_key: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=FileStatus.UPLOADED,
        index=True
    )
    claim_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True, index=True)
    file_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # For any additional metadata
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)  # MIME type of the file
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Size in bytes
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=text('now()'), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_hash: Mapped[str] = mapped_column(String, nullable=False, default="")
    room_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)
    group = relationship("Group")
    user = relationship("User")
    claim = relationship("Claim", back_populates="files")
    items = relationship("Item", secondary="item_files", back_populates="files")
    room = relationship("Room", back_populates="files")
    labels = relationship("Label", secondary="file_labels", back_populates="files")

    __table_args__ = (
        # Ensure only one active (not deleted) file per file_hash, allow unlimited duplicates when deleted=true
        Index('uq_files_file_hash_active', 'file_hash', unique=True, postgresql_where=text('deleted = false')),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "uploaded_by": str(self.uploaded_by),
            "group_id": str(self.group_id),
            "file_name": self.file_name,
            "s3_key": self.s3_key,
            "status": self.status.value if isinstance(self.status, FileStatus) else self.status,
            "claim_id": str(self.claim_id) if self.claim_id else None,
            "file_metadata": self.file_metadata,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "deleted": self.deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
