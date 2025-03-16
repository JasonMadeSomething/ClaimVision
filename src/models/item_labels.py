from sqlalchemy import Column, ForeignKey, UUID, Boolean
from models.base import Base

class ItemLabel(Base):
    """
    Junction table that associates labels with items.
    
    This represents a many-to-many relationship between items and labels.
    The deleted flag allows for soft deletion of label associations.
    """
    __tablename__ = "item_labels"

    item_id = Column(UUID, ForeignKey("items.id"), primary_key=True, index=True)
    label_id = Column(UUID, ForeignKey("labels.id"), primary_key=True, index=True)
    deleted = Column(Boolean, default=False, index=True)  # Allows selective removal of labels per item
