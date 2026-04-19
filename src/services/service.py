import logging
from datetime import datetime
from typing import Type, Optional

from src.models.models import APIResponse
from src.utils.helper import (
    create_success_response,
    create_error_response,
    get_current_timestamp
)
from src.utils.error_codes import ApplicationError, ErrorCode
from src.repository.repository import ErrorLogRepository
from src.agent.main_agent import QuizMainAgent

logger = logging.getLogger(__name__)


class QuizService:
    """
    Service layer for quiz operations.
    
    Orchestrates the quiz workflow by delegating to agents and handling
    business logic. Provides a clean interface between API layer and
    agent/repository layers.
    
    Attributes:
        agent_class: Quiz agent class for instantiation.
        quiz_agent: Initialized quiz agent instance.
        error_repository: Repository for error logging.
    """
    
    def __init__(
        self,
        agent_class: Type[QuizMainAgent] = None,
        error_repository: ErrorLogRepository = None
    ) -> None:
        """
        Initialize QuizService with dependency injection.
        
        Args:
            agent_class: Quiz agent class (default: QuizMainAgent).
            error_repository: Error repository instance (optional).
                If not provided, creates new instance.
        """
        logger.info("Initializing QuizService")
        
        self.agent_class = agent_class or QuizMainAgent
        self.quiz_agent = self.agent_class(error_repository)
        self.error_repository = error_repository or ErrorLogRepository()
    
    async def execute_quiz(
        self,
        user_query: str,
        user_id: str,
        num_questions: int,
        difficulty: str,
        request_id: str,
    ) -> APIResponse:
        """
        Execute the complete quiz pipeline.
        
        Validates input, delegates to quiz agent, and returns structured response.
        Handles all errors gracefully and logs them appropriately.
        
        Args:
            user_query: Quiz topic from user.
            user_id: Unique user identifier (used as thread_id).
            num_questions: Number of questions to generate.
            difficulty: Quiz difficulty level.
            request_id: Unique request identifier for tracking.
        
        Returns:
            APIResponse: Structured response with quiz results or error details.
        """
        timestamp = get_current_timestamp()
        
        try:
            logger.info(
                f"Executing quiz service - request_id={request_id}, "
                f"user_id={user_id}, num_questions={num_questions}, "
                f"difficulty={difficulty}"
            )
            
            self._validate_quiz_request(user_query, num_questions, difficulty)
            
            result = await self.quiz_agent.ask_main_agent(
                user_query=user_query,
                thread_id=user_id,
                num_questions=num_questions,
                difficulty=difficulty
            )
            
            logger.info(f"Quiz execution completed successfully for {request_id}")
            
            return create_success_response(
                status_code=200,
                message="Quiz completed successfully",
                data={"feedback": result},
                request_id=request_id,
                timestamp=timestamp
            )
        
        except ApplicationError as app_error:
            logger.warning(
                f"Application error in quiz service: {app_error}",
                exc_info=True
            )
            self.error_repository.store_error(
                file_name="service.py",
                function_name="execute_quiz",
                error_message=str(app_error)
            )
            
            return create_error_response(
                status_code=app_error.http_status,
                message="Quiz execution failed",
                error_message=str(app_error),
                request_id=request_id,
                timestamp=timestamp
            )
        
        except Exception as unexpected_error:
            logger.error(
                f"Unexpected error in quiz service: {unexpected_error}",
                exc_info=True
            )
            self.error_repository.store_error(
                file_name="service.py",
                function_name="execute_quiz",
                error_message=str(unexpected_error)
            )
            
            return create_error_response(
                status_code=500,
                message="Internal server error",
                error_message="An unexpected error occurred",
                request_id=request_id,
                timestamp=timestamp
            )
    
    def _validate_quiz_request(
        self,
        user_query: str,
        num_questions: int,
        difficulty: str
    ) -> None:
        """
        Validate quiz request parameters.
        
        Args:
            user_query: Quiz topic.
            num_questions: Number of questions.
            difficulty: Difficulty level.
        
        Raises:
            ApplicationError: If validation fails.
        """
        if not user_query or not user_query.strip():
            raise ApplicationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="User query cannot be empty"
            )
        
        if len(user_query) > 500:
            raise ApplicationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="User query exceeds maximum length of 500 characters"
            )

        if not isinstance(num_questions, int):
            raise ApplicationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Number of questions must be an integer"
            )
        
        if num_questions < 1 or num_questions > 20:
            raise ApplicationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Number of questions must be between 1 and 20"
            )

        valid_difficulties = ["easy", "medium", "hard"]
        if difficulty not in valid_difficulties:
            raise ApplicationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"Difficulty must be one of: {', '.join(valid_difficulties)}"
            )
        
        logger.debug("Quiz request validation passed")