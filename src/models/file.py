from sqlalchemy import Column, String, ForeignKey, UUID, JSON, Enum
from sqlalchemy.orm import relationship
import uuid
from enum import Enum as PyEnum
from models.item import Item
from models.item_files import item_files
from models.base import Base  # ✅ Restored Base import

class FileStatus(PyEnum):
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    FAILED = "failed"

class File(Base):
    __tablename__ = "files"

    id: uuid.UUID = Column(UUID, primary_key=True, default=uuid.uuid4)
    uploaded_by: uuid.UUID = Column(UUID, ForeignKey("users.id"), nullable=False)
    household_id: uuid.UUID = Column(UUID, ForeignKey("households.id"), nullable=False)
    file_name: str = Column(String, nullable=False)
    room_name: str = Column(String, nullable=True)  # ✅ Room is stored as a field, not a separate table
    s3_key: str = Column(String, nullable=False)
    labels: list[str] = Column(JSON, nullable=True)  # ✅ Restored as list of strings
    status: FileStatus = Column(Enum(FileStatus), default=FileStatus.UPLOADED)
    claim_id: uuid.UUID = Column(UUID, ForeignKey("claims.id"), nullable=True)
    file_metadata: dict = Column(JSON, nullable=True)  # ✅ Restored metadata field

    household = relationship("Household")
    user = relationship("User")
    claim = relationship("Claim", back_populates="files")
    items = relationship("Item", secondary="item_files", back_populates="files")

    def to_dict(self):
        return {
            "id": str(self.id),
            "uploaded_by": str(self.uploaded_by),
            "household_id": str(self.household_id),
            "file_name": self.file_name,
            "room_name": self.room_name,
            "s3_key": self.s3_key,
            "labels": self.labels,
            "status": self.status.value,
            "claim_id": str(self.claim_id) if self.claim_id else None,
            "file_metadata": self.file_metadata
        }
