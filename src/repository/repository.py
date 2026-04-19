import logging
import traceback
from typing import Optional

from sqlalchemy.orm import Session

from src.repository.schema.schema import ErrorLog
from src.repository.database import database
from src.utils.error_codes import DatabaseError

logger = logging.getLogger(__name__)


class ErrorLogRepository:
    """
    Repository for error log persistence and retrieval.
    
    Handles all database operations related to error logging including
    storing new error records and querying error history.
    """
    
    def __init__(self, db_instance=None) -> None:
        """
        Initialize ErrorLogRepository.
        
        Args:
            db_instance: Database instance (optional, defaults to singleton).
        """
        self.database = db_instance or database
    
    def store_error(
        self,
        file_name: str,
        function_name: str,
        error_message: str,
        created_by: str = "SYSTEM"
    ) -> Optional[ErrorLog]:
        """
        Persist an error record to the database.
        
        Captures the full error details including file name, function name,
        error message, and stack trace. Stores the record in the error_logs table.
        
        Args:
            file_name: Source file where error occurred.
            function_name: Function name where error occurred.
            error_message: Error message or exception message.
            created_by: System component creating the log (default: SYSTEM).
        
        Returns:
            Optional[ErrorLog]: Stored error log record, or None if storage failed.
            
        Example:
            >>> repo = ErrorLogRepository()
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     repo.store_error("module.py", "risky_operation", str(e))
        """
        session = None
        try:
            stack_trace = traceback.format_exc()
            full_error_message = f"{error_message}\n\nSTACK TRACE:\n{stack_trace}"
    
            session = self.database.session_factory()
            
            error_log = ErrorLog(
                file_name=file_name,
                function_name=function_name,
                error=full_error_message,
                created_by=created_by,
                is_active=True
            )
            
            session.add(error_log)
            session.commit()
            
            logger.debug(
                f"Error logged successfully: {file_name}.{function_name}"
            )
            return error_log
            
        except Exception as storage_error:
            if session:
                session.rollback()
            logger.error(
                f"Failed to store error log: {storage_error}",
                exc_info=True
            )

            return None
            
        finally:
            if session:
                session.close()
    
    def get_recent_errors(
        self,
        limit: int = 10,
        file_name: Optional[str] = None,
        function_name: Optional[str] = None
    ) -> list[ErrorLog]:
        """
        Retrieve recent error logs from the database.
        
        Args:
            limit: Maximum number of records to retrieve (default: 10).
            file_name: Optional filter by source file.
            function_name: Optional filter by function name.
        
        Returns:
            list[ErrorLog]: List of error log records.
            
        Raises:
            DatabaseError: If query fails.
        """
        session = None
        try:
            session = self.database.session_factory()
            
            query = session.query(ErrorLog).filter(ErrorLog.is_active == True)
            
            if file_name:
                query = query.filter(ErrorLog.file_name == file_name)
            
            if function_name:
                query = query.filter(ErrorLog.function_name == function_name)
            
            errors = query.order_by(ErrorLog.created_at.desc()).limit(limit).all()
            
            return errors
            
        except Exception as query_error:
            logger.error(f"Failed to retrieve error logs: {query_error}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve error logs",
                original_exception=query_error
            )
        finally:
            if session:
                session.close()
    
    def clear_old_errors(self, days: int = 30) -> int:
        """
        Soft-delete error logs older than specified days.
        
        Args:
            days: Age threshold in days (default: 30).
        
        Returns:
            int: Number of records marked as inactive.
            
        Raises:
            DatabaseError: If operation fails.
        """
        from datetime import datetime, timedelta
        
        session = None
        try:
            session = self.database.session_factory()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = session.query(ErrorLog).filter(
                ErrorLog.created_at < cutoff_date,
                ErrorLog.is_active == True
            ).update({"is_active": False})
            
            session.commit()
            
            logger.info(f"Marked {result} old error records as inactive")
            return result
            
        except Exception as deletion_error:
            if session:
                session.rollback()
            logger.error(f"Failed to clear old errors: {deletion_error}", exc_info=True)
            raise DatabaseError(
                message="Failed to clear old error logs",
                original_exception=deletion_error
            )
        finally:
            if session:
                session.close()