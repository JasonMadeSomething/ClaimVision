"""Household model for PostgreSQL database."""
import uuid
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from models import Base

class Household(Base):
    """
    Represents a household that owns files and claims.

    Attributes
    ----------
    id : int
        Unique identifier for the household.
    name : str
        Name of the household (optional).
    """
    
    __tablename__ = "households"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(255), nullable=True)  # Optional household name

    # ✅ Establish relationships
    users = relationship("User", back_populates="household")
    files = relationship("File", back_populates="household")
    claims = relationship("Claim", back_populates="household")
