from sqlalchemy import Column, String, UUID, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from models.base import Base

class Label(Base):
    __tablename__ = "labels"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("files.id"), nullable=False)
    label_text: Mapped[str] = mapped_column(String, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)  # ✅ Tracks AI vs. user labels
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # ✅ Soft delete for AI labels

    file = relationship("File", back_populates="labels")
