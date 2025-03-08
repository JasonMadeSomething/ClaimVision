from sqlalchemy import Table, Column, UUID, ForeignKey
from models.base import Base

file_labels = Table(
    "file_labels",
    Base.metadata,
    Column("file_id", UUID, ForeignKey("files.id"), primary_key=True),
    Column("label_id", UUID, ForeignKey("labels.id"), primary_key=True)
)
