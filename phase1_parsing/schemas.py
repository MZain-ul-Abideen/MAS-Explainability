"""
Phase 1: Schemas for Parsed Data
Defines Pydantic models for norms and logs.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Any
from datetime import datetime
from enum import Enum


class NormType(str, Enum):
    """Types of norms in the system."""
    OBLIGATION = "obligation"
    PROHIBITION = "prohibition"
    PERMISSION = "permission"


class Norm(BaseModel):
    """
    Represents a single norm.
    
    A norm specifies what agents with certain roles must do, 
    must not do, or are permitted to do under specific conditions.
    """
    norm_id: str = Field(..., description="Unique identifier for this norm")
    norm_type: NormType = Field(..., description="Type of norm")
    role: Optional[str] = Field(None, description="Role this norm applies to (if role-based)")
    mission: Optional[str] = Field(None, description="Mission context (if mission-based)")
    condition: Optional[str] = Field(None, description="Condition under which norm applies")
    action: Optional[str] = Field(None, description="Action that is obligated/prohibited/permitted")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional norm metadata")

    class Config:
        use_enum_values = True


class ParsedNorms(BaseModel):
    """Collection of all parsed norms."""
    norms: list[Norm] = Field(default_factory=list)
    total_count: int = 0
    
    def model_post_init(self, __context):
        """Auto-calculate count after initialization."""
        self.total_count = len(self.norms)


class TemporalStrategy(str, Enum):
    """How to interpret temporal ordering."""
    TIMESTAMP = "timestamp"  # Use explicit timestamps
    SEQUENCE = "sequence"    # Use log entry order


class LogEntry(BaseModel):
    """
    Represents a single logged event.
    
    Can handle both timestamped and sequence-based logs.
    """
    entry_id: str = Field(..., description="Unique identifier for this log entry")
    agent_id: str = Field(..., description="Agent that performed the action")
    action: str = Field(..., description="Action performed")
    timestamp: Optional[datetime] = Field(None, description="When action occurred (if available)")
    sequence_number: Optional[int] = Field(None, description="Order in execution (if timestamps unavailable)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")

    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        """Parse various timestamp formats."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Try common formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S.%f",
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Could not parse timestamp: {v}")
        return v

    def get_temporal_marker(self) -> int | datetime:
        """Get the appropriate temporal marker based on what's available."""
        if self.timestamp is not None:
            return self.timestamp
        if self.sequence_number is not None:
            return self.sequence_number
        raise ValueError(f"LogEntry {self.entry_id} has neither timestamp nor sequence_number")


class ParsedLogs(BaseModel):
    """Collection of all parsed log entries."""
    entries: list[LogEntry] = Field(default_factory=list)
    temporal_strategy: TemporalStrategy = Field(..., description="How temporal ordering is determined")
    total_count: int = 0
    
    def model_post_init(self, __context):
        """Auto-calculate count and validate temporal consistency."""
        self.total_count = len(self.entries)
        
        # Validate temporal strategy matches data
        if self.temporal_strategy == TemporalStrategy.TIMESTAMP:
            if not all(entry.timestamp is not None for entry in self.entries):
                raise ValueError("Temporal strategy is TIMESTAMP but some entries lack timestamps")
        elif self.temporal_strategy == TemporalStrategy.SEQUENCE:
            if not all(entry.sequence_number is not None for entry in self.entries):
                raise ValueError("Temporal strategy is SEQUENCE but some entries lack sequence numbers")

    def get_sorted_entries(self) -> list[LogEntry]:
        """Return entries sorted by their temporal marker."""
        if self.temporal_strategy == TemporalStrategy.TIMESTAMP:
            return sorted(self.entries, key=lambda e: e.timestamp)
        else:
            return sorted(self.entries, key=lambda e: e.sequence_number)