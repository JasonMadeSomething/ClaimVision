"""Pydantic schema for File API requests/responses."""
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from enum import Enum

class FileStatus(Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"

class FileSchema(BaseModel):
    """
    Pydantic model for File data.

    Attributes
    ----------
    id : Optional[str]
        Unique file ID (UUID). Auto-generated if not provided.
    user_id : str
        The ID of the user who owns the file.
    file_name : str
        The original name of the uploaded file.
    s3_key : str
        The file's path in the S3 bucket.
    uploaded_at : Optional[str]
        Timestamp in ISO 8601 format. Defaults to current UTC time.
    description : Optional[str]
        User-provided description of the file.
    claim_id : Optional[str]
        Associated insurance claim ID (UUID string), if applicable.
    labels : List[str]
        List of labels from Rekognition or user-provided labels.
    status : str
        The current status of the file (`uploaded`, `processing`, `processed`).
    file_url : str
        URL to access the file.
    mime_type : str
        The file’s MIME type (e.g., `image/jpeg`).
    size : int
        The file size in bytes.
    resolution : Optional[str]
        The file’s resolution (e.g., `1920x1080`).
    detected_objects : List[str]
        List of detected objects in the file (if applicable).
    """

    id: Optional[str] = None  # Auto-generated UUID
    user_id: str
    file_name: str = Field(..., min_length=1, max_length=255)
    s3_key: str  # Path in S3 bucket
    uploaded_at: Optional[str] = None  # Will be set in Lambda function
    description: Optional[str] = None
    claim_id: Optional[str] = None  # If associated with a claim
    labels: List[str] = []  # Rekognition labels / user-provided labels
    status: str = "uploaded"  # uploaded, processing, processed
    file_url: str
    deleted: bool = False
    deleted_at: Optional[str] = None
    # Metadata
    mime_type: str
    size: int
    resolution: Optional[str] = None
    detected_objects: List[str] = []

    @field_validator("uploaded_at", mode="before")
    @classmethod
    def ensure_uploaded_at(cls, v):
        """
        Ensures `uploaded_at` is always stored as an ISO 8601 string.

        Parameters
        ----------
        v : str | datetime | None
            The input timestamp.

        Returns
        -------
        str
            ISO 8601 formatted timestamp.
        """
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, str):
            return v
        return datetime.now(timezone.utc).isoformat()
