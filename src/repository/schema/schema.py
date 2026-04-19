from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    func,
    text,
    Index
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def generate_uuid() -> str:
    """
    Generate a new UUID string.
    
    Returns:
        str: UUID4 string representation.
    """
    return str(uuid.uuid4())


class ErrorLog(Base):
    """
    Error log record for audit trail and debugging.
    
    Persists all application errors with contextual information including
    file name, function name, error message, and stack trace.
    
    Attributes:
        error_id: Auto-incrementing primary key.
        id: Unique UUID identifier.
        file_name: Source file where error occurred.
        function_name: Function name where error occurred.
        error: Full error message and stack trace.
        created_at: Timestamp when error was logged.
        created_by: System component that created the log.
        updated_at: Timestamp of last update.
        updated_by: System component that last updated the log.
        is_active: Soft delete flag.
    """
    
    __tablename__ = "error_logs"
    
    error_id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )
    
    id = Column(
        String(36),
        unique=True,
        nullable=False,
        default=generate_uuid,
        index=True
    )
    
    file_name = Column(
        String(255),
        nullable=False,
        index=True
    )
    function_name = Column(
        String(255),
        nullable=False,
        index=True
    )
    error = Column(
        Text,
        nullable=False
    )
    
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True
    )
    created_by = Column(
        String(100),
        nullable=False,
        default="SYSTEM"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    updated_by = Column(
        String(100),
        nullable=False,
        default="SYSTEM"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )
    
    __table_args__ = (
        Index("idx_error_file_function", "file_name", "function_name"),
        Index("idx_error_created_at", "created_at"),
        Index("idx_error_is_active", "is_active"),
    )
    
    def __repr__(self) -> str:
        """Return string representation of error log."""
        return (
            f"<ErrorLog(error_id={self.error_id}, "
            f"file_name={self.file_name}, "
            f"function_name={self.function_name})>"
        )