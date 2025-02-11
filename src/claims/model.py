from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional

class Claim(BaseModel):
    id: Optional[str] = None  # Auto-generated UUID
    user_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    loss_date: str = Field(..., description="Date of the loss in YYYY-MM-DD format")  # ✅ Stored as a string
    status: str = "pending"
    created_at: Optional[str] = None  # Will be set in Lambda function

    @field_validator("loss_date", mode="before")
    @classmethod
    def convert_loss_date(cls, v):
        """Ensure `loss_date` is stored as a string (YYYY-MM-DD)"""
        if isinstance(v, date):
            return v.strftime("%Y-%m-%d")  # ✅ Convert date to string
        if isinstance(v, str):
            return v  # ✅ Keep string format
        raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

    def to_dynamodb_dict(self):
        """Convert Pydantic model to a format suitable for DynamoDB"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "loss_date": self.loss_date,  # ✅ Already a string
            "status": self.status,
            "created_at": self.created_at,
        }
