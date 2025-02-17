from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from models import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=True)

    files = relationship("File", back_populates="claim")
