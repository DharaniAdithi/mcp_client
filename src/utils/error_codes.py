from enum import Enum
from typing import Optional, Dict, Any


class ErrorCode(Enum):
    """Enumeration of all application error codes."""
    
    DATABASE_ERROR = "DATABASE_001"
    AGENT_INITIALIZATION_ERROR = "AGENT_001"
    QUIZ_GENERATION_ERROR = "QUIZ_002"
    QUIZ_EVALUATION_ERROR = "QUIZ_003"
    LLMODEL_ERROR = "LLM_001"
    CHECKPOINT_ERROR = "CHECKPOINT_001"
    VALIDATION_ERROR = "VALIDATION_001"
    INTERNAL_SERVER_ERROR = "INTERNAL_001"


ERROR_HTTP_STATUS_MAP: Dict[ErrorCode, int] = {
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.AGENT_INITIALIZATION_ERROR: 500,
    ErrorCode.QUIZ_GENERATION_ERROR: 422,
    ErrorCode.QUIZ_EVALUATION_ERROR: 422,
    ErrorCode.LLMODEL_ERROR: 503,
    ErrorCode.CHECKPOINT_ERROR: 500,
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
}


class ApplicationError(Exception):
    """
    Base exception class for all application-specific errors.
    
    Provides structured error information with error codes, HTTP status codes,
    and detailed error messages.
    """
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> None:
        """
        Initialize ApplicationError.
        
        Args:
            error_code: ErrorCode enum value.
            message: Human-readable error message.
            details: Additional context about the error.
            original_exception: The underlying exception that caused this error.
        """
        self.error_code = error_code
        self.code_value = error_code.value
        self.http_status = ERROR_HTTP_STATUS_MAP.get(error_code, 500)
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary representation.
        
        Returns:
            Dict[str, Any]: Structured error information.
        """
        return {
            "error": {
                "code": self.code_value,
                "message": self.message,
                "details": self.details,
                "http_status": self.http_status
            }
        }
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"[{self.code_value}] {self.message}"


class DatabaseError(ApplicationError):
    """Exception raised for database-related errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(
            ErrorCode.DATABASE_ERROR,
            message,
            details,
            original_exception
        )


class AgentInitializationError(ApplicationError):
    """Exception raised when agent initialization fails."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(
            ErrorCode.AGENT_INITIALIZATION_ERROR,
            message,
            details,
            original_exception
        )


class QuizGenerationError(ApplicationError):
    """Exception raised during quiz question generation."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(
            ErrorCode.QUIZ_GENERATION_ERROR,
            message,
            details,
            original_exception
        )


class QuizEvaluationError(ApplicationError):
    """Exception raised during quiz answer evaluation."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(
            ErrorCode.QUIZ_EVALUATION_ERROR,
            message,
            details,
            original_exception
        )


class LLMError(ApplicationError):
    """Exception raised for LLM-related errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(
            ErrorCode.LLMODEL_ERROR,
            message,
            details,
            original_exception
        )


class ValidationError(ApplicationError):
    """Exception raised for validation errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> None:
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            message,
            details,
            original_exception
        )