from sqlalchemy import Column, ForeignKey, UUID, Table
from models.base import Base

class ItemFile(Base):
    """
    Junction table that associates files with items.
    
    This represents a many-to-many relationship between items and files,
    allowing multiple files to be associated with multiple items.
    """
    __tablename__ = "item_files"

    item_id = Column(UUID, ForeignKey("items.id"), primary_key=True, index=True)
    file_id = Column(UUID, ForeignKey("files.id"), primary_key=True, index=True)
