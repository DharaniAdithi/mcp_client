
import logging
from utils.helper import success_response, error_response, log_error, get_llm
from utils.error_codes import ApplicationError
from agent.system_prompt import SystemPrompt
from langchain_core.messages import HumanMessage
import datetime 

logger = logging.getLogger(__name__)

# SQ 1.14 - SQ 1.21 : Load SystemPrompt instance, Instantiate QuizMainAgent

class QuizService:       

    def __init__(self, AgentClass):
        logger.info("QuizService init")
        self.prompt = SystemPrompt()
        self.main_agent = AgentClass()
        self.llm = get_llm(max_tokens=100, temperature=0.7)

    # SQ 1.22 - SQ 1.81 : Call main_agent.ask() with user_query, thread_id, num_questions, difficulty, Build success_response with feedback result and return
    async def quiz_service(self, user_query: str, user_id: str,
        num_questions:int, difficulty: str, timestamp:datetime, request_id: str,
    ):
        try:
            logger.info(f"QuizService.execute | query={user_query} n={num_questions} diff={difficulty}")

            result = await self.main_agent.ask(user_query=user_query, thread_id=user_id,
                num_questions=num_questions, difficulty=difficulty)

            return success_response(
                status_code=200,
                message="Quiz conducted successfully",
                data={"output": result},
                request_id=request_id,
                timestamp = timestamp
            )

        except ApplicationError as e:
            logger.error(e)
            log_error("service.py", "quiz_service", e)
            return error_response(
                status_code=400, message=str(e), error=str(e), request_id=request_id, timestamp = timestamp
            )

        except Exception as e:
            logger.error(e)
            log_error("service.py", "quiz_service", e)
            return error_response(
                status_code=500, message="Pipeline failed", error=str(e), request_id=request_id, timestamp = timestamp
            )