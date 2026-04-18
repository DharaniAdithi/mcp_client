from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from langgraph.graph import MessagesState
from datetime import datetime


class AssistanceRequest(BaseModel):
    user_query: str = Field(..., description="Topic the user wants to be quizzed on")
    user_id: str = Field(..., description="Used as thread_id for memory isolation")
    num_questions: int = Field(default=3, ge=1, le=20, description="How many questions to generate")
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium", description="Difficulty level of the quiz")

class AssistanceResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[dict]= None
    error: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime

class QuizState(MessagesState):
    user_query:str = ""
    num_questions: int = 3        
    difficulty: str = "medium"
    questions: list[str] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    feedback:str  = ""
    current_step: str = "question_generator"

class Error(BaseModel):
    error: str

class APIResponse(BaseModel):
    status_code: int
    status: str
    message: str
    data: Optional[object]
    error: Optional[Error]
    request_id: str
    timestamp: datetime
    model_config = ConfigDict(
        exclude_none=True   
    )