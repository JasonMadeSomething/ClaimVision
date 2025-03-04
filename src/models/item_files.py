from sqlalchemy import Table, Column, ForeignKey, UUID
from models.base import Base  # ✅ Restored Base import

item_files = Table(
    "item_files",
    Base.metadata,
    Column("item_id", UUID, ForeignKey("items.id"), primary_key=True),
    Column("file_id", UUID, ForeignKey("files.id"), primary_key=True)
)
