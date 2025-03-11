from sqlalchemy import Column, UUID, ForeignKey
from sqlalchemy.orm import Mapped
import uuid
from models.base import Base

class FileLabel(Base):
    """✅ Join table associating files with labels."""
    __tablename__ = "file_labels"

    file_id: Mapped[uuid.UUID] = Column(UUID, ForeignKey("files.id"), primary_key=True)
    label_id: Mapped[uuid.UUID] = Column(UUID, ForeignKey("labels.id"), primary_key=True)
