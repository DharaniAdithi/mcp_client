import logging
import uuid
from typing import Any

from fastapi import APIRouter, Response, Depends

from src.models.models import AssistanceRequest, APIResponse
from src.services.service import QuizService
from src.utils.helper import get_current_timestamp
from src.repository.repository import ErrorLogRepository
from src.constant.constant import (SUMMARY, DESCRIPTION)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["quiz"],
    responses={
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"},
    }
)


@router.post(
    "/quiz",
    response_model=APIResponse,
    status_code=200,
    summary=SUMMARY,
    description=DESCRIPTION
)
async def create_and_evaluate_quiz(
    payload: AssistanceRequest,
    response: Response
) -> Any:
    """
    API endpoint for creating and evaluating quizzes.
    
    This endpoint orchestrates the complete quiz pipeline:
    1. Accepts quiz parameters from user
    2. Delegates to QuizService for processing
    3. Returns structured response with feedback or error
    
    The endpoint is fully stateless - state is managed by LangGraph
    checkpointing in the database using the user_id as a thread identifier.
    
    Args:
        payload: Quiz request payload with topic, parameters.
        response: FastAPI response object for status code setting.
        service: Injected QuizService instance.
    
    Returns:
        APIResponse: Structured response with quiz feedback or error details.
        
    Example Request:
        {
            "user_query": "Python programming basics",
            "user_id": "user_123",
            "num_questions": 5,
            "difficulty": "medium"
        }
        
    Example Response (Success):
        {
            "status_code": 200,
            "status": "success",
            "message": "Quiz completed successfully",
            "data": {
                "feedback": "Q1: correct\\nQ2: partial\\n..."
            },
            "request_id": "uuid-string",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    request_id = None
    timestamp = get_current_timestamp()
    
    try:
        request_id = str(uuid.uuid4())

        service = QuizService(error_repository=ErrorLogRepository())
        
        logger.info(
            f"Received quiz request - request_id={request_id}, "
            f"user_id={payload.user_id}, topic={payload.user_query[:50]}..."
        )
        
        result = await service.execute_quiz(
            user_query=payload.user_query,
            user_id=payload.user_id,
            num_questions=payload.num_questions,
            difficulty=payload.difficulty,
            request_id=request_id
        )
        
        response.status_code = result.status_code
        
        logger.info(
            f"Quiz request completed - request_id={request_id}, "
            f"status_code={result.status_code}"
        )
        
        return result
    
    except Exception as endpoint_error:
        logger.error(
            f"Unhandled error in quiz endpoint: {endpoint_error}",
            exc_info=True
        )
        
        response.status_code = 500
        
        return APIResponse(
            status_code=500,
            status="error",
            message="Internal server error",
            data=None,
            error={"error": "An unexpected error occurred"},
            request_id=request_id or "unknown",
            timestamp=timestamp
        )


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        dict: Health status.
    """
    return {
        "status": "healthy",
        "service": "Quiz Pipeline API"
    }