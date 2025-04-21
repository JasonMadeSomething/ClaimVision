from sqlalchemy import String, ForeignKey, UUID, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
import os
import csv
from datetime import datetime, timezone
from models.base import Base  
from models.item import Item
from models.file import File
from models.room import Room
class Claim(Base):
    """
    Represents an insurance claim filed by a household.
    
    Claims contain multiple items and can have files directly associated with them.
    Each claim belongs to a specific household and tracks information about the loss event.
    """
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("groups.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_loss: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now(timezone.utc), index=True)  # Added index for date queries
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)

    creator: Mapped["User"] = relationship("User", back_populates="claims_created")
    group = relationship("Group", back_populates="claims")
    files = relationship("File", back_populates="claim")
    items = relationship("Item", back_populates="claim", cascade="all, delete-orphan")
    __table_args__ = (
        # Create a composite unique constraint on title and deleted per household
        # This allows the same title to exist if one is deleted and one is not
        UniqueConstraint('title', 'deleted', 'group_id', name='uq_title_deleted_group'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "group_id": str(self.group_id),
            "title": self.title,
            "description": self.description,
            "date_of_loss": self.date_of_loss.isoformat(),
            "deleted": self.deleted,
            "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None
        }
        
    def generate_report_data(self, session):
        """
        Generate structured data for a claim report.
        
        This method collects and structures all data needed for a claim report,
        but does not create any files. File creation is handled by downstream processes.
        
        Args:
            session: SQLAlchemy database session
            
        Returns:
            dict: Structured report data
        """
        # Initialize report data structure
        report_data = {
            'claim': {
                'id': str(self.id),
                'title': self.title,
                'description': self.description,
                'date_of_loss': self.date_of_loss.isoformat() if self.date_of_loss else None,
                'created_at': self.created_at.isoformat() if self.created_at else None
            },
            'rooms': {},
            'files': [],
            'items': []
        }
        
        # Get all items associated with the claim
        items = session.query(Item).filter(
            Item.claim_id == self.id,
            Item.deleted.is_(False)
        ).all()
        
        # Process items
        for i, item in enumerate(items, 1):
            room_name = 'N/A'
            if item.room_id:
                room = session.query(Room).filter(Room.id == item.room_id).first()
                if room:
                    room_name = room.name
                    
            # Create room entry if it doesn't exist
            if room_name != 'N/A' and room_name not in report_data['rooms']:
                report_data['rooms'][room_name] = {
                    'name': room_name,
                    'items': []
                }
            
            # Create item data structure
            item_data = {
                'id': str(item.id),
                'number': i,
                'name': item.name,
                'room': room_name,
                'brand_manufacturer': item.brand_manufacturer or 'N/A',
                'model_number': item.model_number or 'N/A',
                'description': item.description or item.name,
                'original_vendor': item.original_vendor or 'N/A',
                'quantity': item.quantity or 1,
                'age_years': item.age_years or 'N/A',
                'age_months': item.age_months or 'N/A',
                'condition': item.condition or 'N/A',
                'unit_cost': item.unit_cost,
                'total_cost': item.total_cost
            }
            
            # Add item to main items list
            report_data['items'].append(item_data)
            
            # Add item reference to room data
            if room_name != 'N/A' and room_name in report_data['rooms']:
                report_data['rooms'][room_name]['items'].append({
                    'id': str(item.id),
                    'number': i,
                    'name': item.name,
                    'description': item.description
                })
        
        # Get all files associated with the claim
        claim_files = session.query(File).filter(
            File.claim_id == self.id,
            File.deleted.is_(False)
        ).all()
        
        # Add files to the report data
        for file in claim_files:
            report_data['files'].append({
                'id': str(file.id),
                'filename': file.file_name,
                's3_key': file.s3_key,
                'content_type': file.content_type
            })
        
        return report_data
