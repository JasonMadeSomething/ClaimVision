from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, ForeignKey
from uuid import UUID
from models.base import Base


class ItemLabel(Base):
    __tablename__ = "item_labels"

    item_id: Mapped[UUID] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    label_id: Mapped[UUID] = mapped_column(ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)