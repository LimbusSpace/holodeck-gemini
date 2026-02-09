"""Session-related schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_serializer


class SessionStatus(str, Enum):
    """Session status enumeration with detailed tracking."""
    INIT = "init"
    ANALYZING = "analyzing"
    GENERATING_REF = "generating_ref"  # Scene reference image
    EXTRACTING_OBJECTS = "extracting_objects"
    GENERATING_CARDS = "generating_cards"
    QC_CARDS = "qc_cards"
    GENERATING_ASSETS = "generating_assets"
    SOLVING_LAYOUT = "solving_layout"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Partial success with some failures


class SessionRequest(BaseModel):
    """User request for scene generation."""
    text: str = Field(..., description="Scene description text")
    style: Optional[str] = Field(None, description="Artistic style")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Additional constraints")


class Session(BaseModel):
    """Main session data structure with comprehensive tracking."""
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    status: SessionStatus = Field(default=SessionStatus.INIT, description="Current status")
    request: SessionRequest = Field(..., description="User request")

    # Progress tracking
    current_step: Optional[str] = Field(None, description="Current processing step")
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage")

    # Statistics
    objects_count: int = Field(0, ge=0, description="Number of objects in scene")
    generation_time: float = Field(0.0, ge=0.0, description="Total generation time (seconds)")

    # Error handling
    error_history: list[Dict[str, Any]] = Field(default_factory=list, description="History of errors encountered")
    retry_count: int = Field(0, ge=0, description="Number of retries attempted")
    max_retries: int = Field(3, ge=1, description="Maximum allowed retries")

    # File paths tracking
    workspace_path: Optional[str] = Field(None, description="Path to session workspace")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    def add_error(self, error: Dict[str, Any]) -> None:
        """Add an error to the error history."""
        error['timestamp'] = datetime.now(timezone.utc).isoformat()
        self.error_history.append(error)
        self.updated_at = datetime.now(timezone.utc)

    def can_retry(self) -> bool:
        """Check if session can be retried."""
        return self.retry_count < self.max_retries and self.status in [SessionStatus.FAILED, SessionStatus.PARTIAL]

    def increment_retry(self) -> None:
        """Increment retry count and reset status."""
        self.retry_count += 1
        self.status = SessionStatus.INIT
        self.updated_at = datetime.now(timezone.utc)