from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class Claim(BaseModel):
    id: Optional[str] = None  # Auto-generated UUID
    user_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    loss_date: date = Field(..., description="Date of the loss")
    status: str = "pending"
    created_at: Optional[str] = None  # Will be set in Lambda function
