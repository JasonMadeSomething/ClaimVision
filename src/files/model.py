"""
File Model for Storing Metadata in DynamoDB

This module defines the `File` model, which represents metadata for files
stored in AWS S3. It is designed to ensure structured and validated data
storage in DynamoDB.

Features:
- Auto-generates UUIDs for file IDs if not provided.
- Ensures `uploaded_at` is always stored in ISO 8601 format.
- Converts Pydantic models to DynamoDB-compatible dictionaries.
- Supports metadata fields such as file size, MIME type, resolution, and detected objects.

Example Usage:
    ```
    from models import File

    file = File(
        user_id="user-123",
        file_name="image.jpg",
        s3_key="uploads/user-123/image.jpg",
        file_url="https://s3.amazonaws.com/bucket/uploads/user-123/image.jpg",
        mime_type="image/jpeg",
        size=204800,
    )

    dynamo_dict = file.to_dynamodb_dict()
    print(dynamo_dict)
    ```
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class File(BaseModel):
    """
    Represents a file stored in AWS S3, with metadata stored in DynamoDB.

    Attributes:
        id (Optional[str]): Unique file ID (UUID). Auto-generated if not provided.
        user_id (str): The ID of the user who owns the file.
        file_name (str): The original name of the uploaded file.
        s3_key (str): The file's path in the S3 bucket.
        uploaded_at (Optional[str]): Timestamp in ISO 8601 format. Defaults to current UTC time.
        description (Optional[str]): User-provided description of the file.
        claim_id (Optional[str]): Associated insurance claim ID, if applicable.
        labels (List[str]): List of labels from Rekognition or user-provided labels.
        status (str): The current status of the file (`uploaded`, `processing`, `processed`).
        file_url (str): URL to access the file.
        mime_type (str): The file’s MIME type (e.g., `image/jpeg`).
        size (int): The file size in bytes.
        resolution (Optional[str]): The file’s resolution (e.g., `1920x1080`).
        detected_objects (List[str]): List of detected objects in the file (if applicable).
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
        """
        Ensures `uploaded_at` is always stored as an ISO 8601 string.

        Args:
            v (str | datetime | None): The input timestamp.

        Returns:
            str: ISO 8601 formatted timestamp.
        """
        if isinstance(v, datetime):
            return v.isoformat()  # ✅ Convert datetime to string
        if isinstance(v, str):
            return v  # ✅ Keep string format
        return datetime.utcnow().isoformat()  # ✅ Default to now

    def to_dynamodb_dict(self) -> dict:
        """
        Converts the `File` model into a DynamoDB-compatible dictionary.

        Returns:
            dict: A dictionary representation of the file, suitable for DynamoDB storage.
        """
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
    def from_dynamodb_dict(cls, data: dict):
        """
        Converts a DynamoDB item back into a `File` model.

        Args:
            data (dict): The DynamoDB item.

        Returns:
            File: A `File` model instance.
        """
        if "metadata" in data:
            metadata = data["metadata"]
            data["metadata"] = {
                "mime_type": metadata.get("mime_type"),
                "size": int(metadata["size"]) if "size" in metadata and isinstance(
                    metadata["size"], Decimal
                ) else metadata["size"],
                "resolution": metadata.get("resolution"),
                "detected_objects": metadata.get("detected_objects", []),
            }
        return cls(**data)
