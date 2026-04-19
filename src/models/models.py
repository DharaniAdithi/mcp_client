from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from langgraph.graph import MessagesState


class AssistanceRequest(BaseModel):
    """
    Request model for quiz generation and evaluation.
    
    Attributes:
        user_query: Topic or subject for quiz generation.
        user_id: Unique user identifier (used as thread ID for conversation state).
        num_questions: Number of quiz questions to generate (1-20).
        difficulty: Quiz difficulty level.
    """
    
    user_query: str = Field(
        ...,
        description="Topic or subject the user wants to be quizzed on",
        min_length=1,
        max_length=500
    )
    user_id: str = Field(
        ...,
        description="Unique user identifier for conversation history isolation",
        min_length=1
    )
    num_questions: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of quiz questions to generate"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium",
        description="Difficulty level of quiz questions"
    )
    
    model_config = ConfigDict(str_strip_whitespace=True)


class ErrorInfo(BaseModel):
    """Error details in API response."""
    
    error: str = Field(..., description="Error message")


class AssistanceResponse(BaseModel):
    """
    Standard response model for quiz API endpoint.
    
    Attributes:
        status_code: HTTP status code.
        message: Human-readable status message.
        data: Response payload (optional).
        error: Error details if request failed.
        request_id: Unique request identifier.
        timestamp: Response timestamp.
    """
    
    status_code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Status message")
    data: Optional[dict] = Field(default=None, description="Response payload")
    error: Optional[str] = Field(default=None, description="Error message if applicable")
    request_id: Optional[str] = Field(default=None, description="Unique request identifier")
    timestamp: datetime = Field(..., description="Response timestamp")


class APIResponse(BaseModel):
    """
    Comprehensive API response model with error handling.
    
    Used for all API endpoints to provide consistent response format
    with proper error information and status tracking.
    """
    
    status_code: int = Field(..., description="HTTP status code")
    status: Literal["success", "error"] = Field(..., description="Response status")
    message: str = Field(..., description="Status message")
    data: Optional[dict] = Field(default=None, description="Response data")
    error: Optional[ErrorInfo] = Field(default=None, description="Error information")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(..., description="Response timestamp")
    
    model_config = ConfigDict(exclude_none=True)


class QuizState(MessagesState):
    """
    LangGraph state schema for quiz pipeline orchestration.
    
    Maintains conversation history and quiz-specific metadata throughout
    the multi-step quiz generation and evaluation workflow.
    
    Attributes:
        user_query: Original user query/topic.
        num_questions: Number of questions to generate.
        difficulty: Quiz difficulty level.
        questions: Generated quiz questions.
        answers: User-provided answers.
        feedback: Evaluation feedback from review agent.
        current_step: Current pipeline step identifier.
    """
    
    user_query: str = Field(default="", description="Original user query")
    num_questions: int = Field(default=3, description="Number of questions")
    difficulty: str = Field(default="medium", description="Difficulty level")
    questions: list[str] = Field(
        default_factory=list,
        description="Generated quiz questions"
    )
    answers: list[str] = Field(
        default_factory=list,
        description="User-provided answers"
    )
    feedback: str = Field(default="", description="Evaluation feedback")
    current_step: str = Field(
        default="question_generator",
        description="Current orchestration step"
    )