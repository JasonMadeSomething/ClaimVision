from sqlalchemy import Column, ForeignKey, UUID, Table
from models.base import Base

class ItemFile(Base):
    __tablename__ = "item_files"

    item_id = Column(UUID, ForeignKey("items.id"), primary_key=True)
    file_id = Column(UUID, ForeignKey("files.id"), primary_key=True)
