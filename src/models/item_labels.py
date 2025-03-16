from sqlalchemy import Column, ForeignKey, UUID, Boolean
from models.base import Base

class ItemLabel(Base):
    __tablename__ = "item_labels"

    item_id = Column(UUID, ForeignKey("items.id"), primary_key=True)
    label_id = Column(UUID, ForeignKey("labels.id"), primary_key=True)
    deleted = Column(Boolean, default=False)  # Allows selective removal of labels per item
