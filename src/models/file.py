"""File model for PostgreSQL database."""

from datetime import datetime, UTC
import uuid
from typing import Dict, List, Optional, Union
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base


class File(Base):
    """
    Represents a file stored in the system.

    Attributes
    ----------
    id : str
        Unique identifier for the file (UUID).
    user_id : str
        ID of the user who owns the file.
    file_name : str
        Name of the file.
    s3_key : str
        The key to retrieve the file from S3.
    uploaded_at : str
        Timestamp in ISO 8601 format (UTC).
    description : Optional[str], default=None
        Optional description of the file.
    claim_id : Optional[int], default=None
        Associated insurance claim ID (if applicable).
    labels : List[str], default=[]
        List of labels from Rekognition or user-provided labels.
    status : str, default="uploaded"
        The current status of the file.
    file_url : str
        The URL to access the file.
    mime_type : str
        The file’s MIME type.
    size : int
        The file size in bytes.
    resolution : Optional[str], default=None
        The file’s resolution.
    detected_objects : List[str], default=[]
        List of detected objects in the file.
    """

    __tablename__: str = "files"
    __table_args__ = (UniqueConstraint("user_id", "file_name", name="uq_user_file"),)

    id: str = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: str = Column(String, nullable=False)
    file_name: str = Column(String(255), nullable=False)
    s3_key: str = Column(String, nullable=False)
    uploaded_at: str = Column(String, default=lambda: datetime.now(UTC).isoformat())
    description: Optional[str] = Column(String, nullable=True)
    claim_id: Optional[int] = Column(Integer, ForeignKey("claims.id"), nullable=True)
    labels: List[str] = Column(JSON, nullable=False, default=[])
    status: str = Column(String, nullable=False, default="uploaded")
    file_url: str = Column(String, nullable=False)

    # Metadata
    mime_type: str = Column(String, nullable=False)
    size: int = Column(Integer, nullable=False)
    resolution: Optional[str] = Column(String, nullable=True)
    detected_objects: List[str] = Column(JSON, nullable=False, default=[])

    # Relationship
    claim = relationship("Claim", back_populates="files")

    def to_dict(self) -> Dict[str, Union[str, int, List[str], None]]:
        """
        Converts the SQLAlchemy model instance to a dictionary.

        Returns
        -------
        Dict[str, Union[str, int, List[str], None]]
            A dictionary representation of the file instance.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "s3_key": self.s3_key,
            "uploaded_at": self.uploaded_at,
            "description": self.description,
            "claim_id": self.claim_id,
            "labels": self.labels,
            "status": self.status,
            "file_url": self.file_url,
            "mime_type": self.mime_type,
            "size": self.size,
            "resolution": self.resolution,
            "detected_objects": self.detected_objects,
        }
