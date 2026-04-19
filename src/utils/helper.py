from datetime import datetime, timezone
from typing import Dict, Optional, Any
import logging

from src.models.models import APIResponse, ErrorInfo
from src.settings.settings import settings
from src.utils.error_codes import ApplicationError, ErrorCode

logger = logging.getLogger(__name__)


def create_success_response(
    status_code: int,
    message: str,
    data: Optional[Dict[str, Any]],
    request_id: str,
    timestamp: datetime
) -> APIResponse:
    """
    Create a successful API response.
    
    Args:
        status_code: HTTP status code (typically 200).
        message: Human-readable success message.
        data: Response payload data.
        request_id: Unique request identifier.
        timestamp: Request timestamp.
    
    Returns:
        APIResponse: Structured success response object.
    """
    return APIResponse(
        status_code=status_code,
        status="success",
        message=message,
        data=data,
        error=None,
        request_id=request_id,
        timestamp=timestamp
    )


def create_error_response(
    status_code: int,
    message: str,
    error_message: str,
    request_id: str,
    timestamp: datetime
) -> APIResponse:
    """
    Create an error API response.
    
    Args:
        status_code: HTTP status code (4xx or 5xx).
        message: Summary message.
        error_message: Detailed error message.
        request_id: Unique request identifier.
        timestamp: Request timestamp.
    
    Returns:
        APIResponse: Structured error response object.
    """
    return APIResponse(
        status_code=status_code,
        status="error",
        message=message,
        data=None,
        error=ErrorInfo(error=error_message),
        request_id=request_id,
        timestamp=timestamp
    )


def get_bedrock_client():
    """
    Create and configure AWS Bedrock runtime client.
    
    Uses AWS credentials from settings. Client is configured with the
    appropriate region for Bedrock API calls.
    
    Returns:
        boto3.client: Configured Bedrock runtime client.
        
    Raises:
        ImportError: If boto3 is not installed.
    """
    try:
        import boto3
    except ImportError as import_error:
        logger.error("boto3 library is required for AWS Bedrock integration")
        raise ImportError(
            "boto3 is not installed. Install it with: pip install boto3"
        ) from import_error
    
    try:
        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.aws.region
        )
        logger.debug(f"Bedrock client created for region: {settings.aws.region}")
        return client
    except Exception as bedrock_error:
        logger.error(f"Failed to create Bedrock client: {bedrock_error}")
        raise


def initialize_language_model(
    max_tokens: int = 500,
    temperature: float = 0.7
):
    """
    Initialize and configure the language model client.
    
    Creates a ChatBedrock instance configured with the specified parameters.
    The model ID and provider are sourced from application settings.
    
    Args:
        max_tokens: Maximum tokens for model output (default: 500).
        temperature: Sampling temperature for generation (default: 0.7).
    
    Returns:
        ChatBedrock: Configured language model instance.
        
    Raises:
        ImportError: If langchain_aws module is not installed.
        LLMError: If LLM client initialization fails.
    
    Example:
        >>> llm = initialize_language_model(max_tokens=1000, temperature=0.5)
        >>> response = llm.invoke("What is Python?")
    """
    try:
        from langchain_aws import ChatBedrock
    except ImportError as import_error:
        logger.error("langchain_aws module is required for Bedrock integration")
        raise ImportError(
            "langchain_aws is not installed. Install it with: pip install langchain-aws"
        ) from import_error
    
    try:
        bedrock_client = get_bedrock_client()
        
        llm = ChatBedrock(
            client=bedrock_client,
            model_id=settings.aws.model_id,
            provider=settings.aws.provider,
            model_kwargs={
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        
        logger.info(
            f"Language model initialized: {settings.aws.provider} - "
            f"max_tokens={max_tokens}, temperature={temperature}"
        )
        return llm
        
    except Exception as llm_error:
        logger.error(f"Failed to initialize language model: {llm_error}", exc_info=True)
        raise ApplicationError(
            error_code=ErrorCode.LLMODEL_ERROR,
            message="Failed to initialize language model",
            details={"model_id": settings.aws.model_id},
            original_exception=llm_error
        )


def get_current_timestamp() -> datetime:
    """
    Get current UTC timestamp.
    
    Returns:
        datetime: Current UTC datetime.
    """
    return datetime.now(timezone.utc)