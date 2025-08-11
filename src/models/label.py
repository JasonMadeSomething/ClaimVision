from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from models.base import Base

class Label(Base):
    """✅ Represents a shared label that can be linked to multiple files."""
    __tablename__ = "labels"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label_text: Mapped[str] = mapped_column(String, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    group_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    group = relationship("Group")

    files = relationship("File", secondary="file_labels", back_populates="labels")

    __table_args__ = (
        UniqueConstraint('label_text', 'is_ai_generated', 'group_id', name='label_text_is_ai_generated_unique'),
    )
    def to_dict(self):
        return {
            "id": str(self.id),
            "label_text": self.label_text,
            "is_ai_generated": self.is_ai_generated,
            "deleted": self.deleted,
            "group_id": str(self.group_id),
        }