"""File model for storing file metadata in DynamoDB"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class File(BaseModel):
    """File model
    Attributes:
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
        mime_type: str
        size: int
        resolution: Optional[str] = None
        detected_objects: Optional[List[str]] = None
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

    # Metadata
    mime_type: str
    size: int
    resolution: Optional[str] = None
    detected_objects: List[str] = []

    @field_validator("uploaded_at", mode="before")
    @classmethod
    def ensure_uploaded_at(cls, v):
        """Ensure `uploaded_at` is stored as a string (ISO 8601)"""
        if isinstance(v, datetime):
            return v.isoformat()  # ✅ Convert datetime to string
        if isinstance(v, str):
            return v  # ✅ Keep string format
        return datetime.utcnow().isoformat()  # ✅ Default to now

    def to_dynamodb_dict(self):
        """Convert Pydantic model to a format suitable for DynamoDB"""
        return {
           "id": self.id or str(uuid.uuid4()),  # Generate UUID if not provided
            "user_id": self.user_id,
            "file_name": self.file_name,
            "s3_key": self.s3_key,
            "uploaded_at": self.uploaded_at or datetime.utcnow().isoformat(),
            "description": self.description,
            "claim_id": self.claim_id,
            "labels": self.labels,
            "status": self.status,
            "file_url": self.file_url,
            "metadata": {
                "mime_type": self.mime_type,
                "size": int(self.size),  # Ensure this is always stored as an int
                "resolution": self.resolution,
                "detected_objects": self.detected_objects,
        },
    }


    @classmethod
    def from_dynamodb_dict(cls, data):
        """Convert DynamoDB item back into a Pydantic model"""
        if "metadata" in data:
            metadata = data["metadata"]
            data["metadata"] = {
                "mime_type": metadata.get("mime_type"),
                "size": int(metadata["size"]) if "size" in metadata and isinstance(
                    metadata["size"],
                    Decimal
                ) else metadata["size"],
                "resolution": metadata.get("resolution"),
                "detected_objects": metadata.get("detected_objects", []),
            }
        return cls(**data)
