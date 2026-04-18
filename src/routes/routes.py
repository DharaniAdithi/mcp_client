from fastapi import APIRouter, Response, Depends
from typing import Any
import uuid
from models.models import AssistanceRequest, AssistanceResponse
from services.service import QuizService  
from utils.helper import error_response, log_error
from agent.main_agent import QuizMainAgent 
import datetime 

router = APIRouter(prefix="/api/v1", tags=["multi-agent pipeline"])

def get_code_pipeline_service() -> QuizService:
    return QuizService(QuizMainAgent)

# SQ 1.10 - SQ 1.13 : Receive POST /api/v1/quiz request from client, Generate unique request_id and timestamp, Instantiate QuizService with QuizMainAgent via Depends, Call quiz_service() with all request fields, Return AssistanceResponse to client

@router.post("/quiz", response_model=AssistanceResponse, status_code=200)
async def run_quiz( 
    payload:  AssistanceRequest,
    response: Response,
     service: QuizService = Depends(get_code_pipeline_service) 
) -> Any:
    request_id = None
    try:
        request_id = str(uuid.uuid4()) 
        timestamp = datetime.datetime.now().isoformat()
        result = await service.quiz_service(user_query=payload.user_query, user_id=payload.user_id,
            num_questions=payload.num_questions, difficulty=payload.difficulty, timestamp= timestamp, request_id=request_id,
        )
        response.status_code = result.status_code
        return result

    except Exception as e:
        response.status_code = 500
        log_error(file_name="routes.py", function_name="run_quiz", exception=e)
        return error_response(
            status_code=500,
            message=str(e),
            error=str(e),
            timestamp = timestamp,
            request_id=request_id,
        )