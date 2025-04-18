from sqlalchemy import String, ForeignKey, UUID, DateTime, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime, timezone
import enum
from models.base import Base

class ReportStatus(enum.Enum):
    """
    Enum representing the possible statuses of a report.
    """
    REQUESTED = "REQUESTED"
    PROCESSING = "PROCESSING"
    AGGREGATING = "AGGREGATING"
    ORGANIZING = "ORGANIZING"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Report(Base):
    """
    Represents a report generated for a claim.
    
    Reports are requested by users and can be associated with specific claims.
    The report tracks its status through the generation process and stores
    information about where the final report file is located.
    """
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("households.id"), nullable=False, index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("claims.id"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(
        Enum(ReportStatus, native_enum=False), 
        default=ReportStatus.REQUESTED.value,
        nullable=False,
        index=True
    )
    
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    email_address: Mapped[str] = mapped_column(String, nullable=False)  # Email address for report delivery
    s3_key: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Tracking fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="reports")
    household = relationship("Household", backref="reports")
    claim = relationship("Claim", backref="reports")
    
    def to_dict(self):
        """
        Convert the report object to a dictionary representation.
        """
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "household_id": str(self.household_id),
            "claim_id": str(self.claim_id),
            "status": self.status,
            "report_type": self.report_type,
            "email_address": self.email_address,
            "s3_key": self.s3_key,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') else None,
            "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    def update_status(self, new_status: ReportStatus, error_message: str = None):
        """
        Update the status of the report and set the error message if provided.
        If the status is changed to COMPLETED, also set the completed_at timestamp.
        """
        self.status = new_status.value
        
        if error_message:
            self.error_message = error_message
            
        if new_status == ReportStatus.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)
            
        self.updated_at = datetime.now(timezone.utc)
