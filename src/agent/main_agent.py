import logging
import uuid

from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from psycopg_pool import AsyncConnectionPool

from src.agent.system_prompt import SystemPrompt
from src.utils.helper import initialize_language_model
from src.tools.tools import generate_quiz, evaluate_answers
from src.models.models import QuizState
from src.settings.settings import settings
from src.repository.repository import ErrorLogRepository
from src.utils.error_codes import (
    AgentInitializationError,
    ApplicationError,
    DatabaseError,
    ErrorCode
)

logger = logging.getLogger(__name__)


class QuizMainAgent:
    """
    Main orchestration agent for the quiz pipeline.

    Coordinates the two-step quiz workflow:
    1. Question generation with user answer collection (console input)
    2. Answer evaluation and feedback generation

    Attributes:
        llm: Language model instance for orchestration.
        prompt: System prompt container.
        database_uri: PostgreSQL connection URI.
        error_repository: Repository for error persistence.
        _pool: Long-lived AsyncConnectionPool instance.
        _checkpointer: AsyncPostgresSaver bound to the pool.
        _agent: Compiled LangGraph agent.
    """

    def __init__(self, error_repository: ErrorLogRepository = None) -> None:
        logger.info("Initializing QuizMainAgent")

        self.llm = initialize_language_model(
            max_tokens=500,
            temperature=0.0
        )
        self._agent = None
        self._checkpointer = None
        self._pool = None
        self.prompt = SystemPrompt()
        self.database_uri = settings.database.get_async_connection_uri()
        self.error_repository = error_repository or ErrorLogRepository()

    async def _get_agent(self):
        """
        Return a long-lived agent bound to a persistent connection pool.
        Initializes pool, checkpointer, and agent on first call only.
        """
        if self._agent is not None:
            return self._agent

        try:
            logger.info("Setting up LangGraph agent with PostgreSQL checkpointing")

            self._pool = AsyncConnectionPool(
                conninfo=self.database_uri,
                max_size=10,
                open=False,
                kwargs={"autocommit": True},  
            )
            await self._pool.open()

            self._checkpointer = AsyncPostgresSaver(self._pool)
            
            await self._checkpointer.setup()

            self._agent = create_agent(
                model=self.llm,
                tools=[generate_quiz, evaluate_answers],
                state_schema=QuizState,
                system_prompt=self.prompt.orchestrator_prompt,
                checkpointer=self._checkpointer,
            )

            logger.info("LangGraph agent setup completed successfully")
            return self._agent

        except Exception as setup_error:
            logger.error(f"Agent setup failed: {setup_error}", exc_info=True)
            self.error_repository.store_error(
                file_name="main_agent.py",
                function_name="_get_agent",
                error_message=str(setup_error)
            )
            raise AgentInitializationError(
                message="Failed to setup quiz orchestration agent",
                original_exception=setup_error
            )

    async def close(self) -> None:
        """Cleanly close the connection pool on application shutdown."""
        if self._pool is not None:
            try:
                await self._pool.close()
                logger.info("Connection pool closed successfully")
            except Exception as close_error:
                logger.warning(f"Error closing connection pool: {close_error}")
            finally:
                self._pool = None
                self._checkpointer = None
                self._agent = None

    async def ask_main_agent(
        self,
        user_query: str,
        thread_id: str,
        num_questions: int,
        difficulty: str
    ) -> str:
        """
        Execute the full console quiz pipeline.

        1. Generates questions (graph pauses at interrupt)
        2. Prints questions and collects answers via console input
        3. Resumes graph — generate_quiz detects answers in state and skips
        4. evaluate_answers runs and stores feedback in state
        5. Feedback read directly from state (not orchestrator message)
        6. Prints and returns feedback

        Args:
            user_query: Quiz topic from user.
            thread_id: User ID — unique suffix appended per session.
            num_questions: Number of questions to generate.
            difficulty: Quiz difficulty level.

        Returns:
            str: Final evaluation feedback.
        """
        try:
            session_thread_id = f"{thread_id}_{uuid.uuid4().hex}"

            logger.info(
                f"Starting quiz pipeline - thread_id={session_thread_id}, "
                f"questions={num_questions}, difficulty={difficulty}"
            )

            agent = await self._get_agent()
            config = {"configurable": {"thread_id": session_thread_id}}

            initial_state = {
                "messages": [HumanMessage(content=user_query)],
                "user_query": user_query,
                "num_questions": num_questions,
                "difficulty": difficulty,
                "questions": [],
                "answers": [],
                "feedback": "",
                "current_step": "question_generator",
            }

            result = await agent.ainvoke(initial_state, config)

            if "__interrupt__" not in result:
                raise ApplicationError(
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                    message="Agent did not interrupt for answer collection"
                )

            logger.info("Agent interrupted for answer collection")

            interrupt_data = result["__interrupt__"][0].value

            if interrupt_data.get("type") != "quiz":
                raise ApplicationError(
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                    message=f"Unexpected interrupt type: {interrupt_data.get('type')}"
                )

            questions = interrupt_data.get("questions", [])

            print(f"\n{'='*50}")
            print(f"  Quiz Topic : {user_query}")
            print(f"  Difficulty : {difficulty.upper()}")
            print(f"  Questions  : {num_questions}")
            print(f"{'='*50}\n")

            user_answers = []
            for i, question in enumerate(questions, 1):
                print(f"  {question}")
                answer = input("  Your answer: ").strip()
                user_answers.append(answer)
                print()

            logger.info(f"Collected {len(user_answers)} answers from user")

            result = await agent.ainvoke(
                    Command(
                        resume=user_answers,
                        update={
                            "current_step": "answer_evaluator",
                            "answers": user_answers,
                            "messages": [
                                HumanMessage(content=(
                                    f"Answers collected: {user_answers}. "
                                    f"current_step is now answer_evaluator. "
                                    f"Call evaluate_answers tool immediately."
                                ))
                            ]
                        }
                    ),
                    config,
                )


            feedback = result.get("feedback", "").strip()

            if not feedback:
                feedback = next(
                    (
                        msg.content
                        for msg in reversed(result.get("messages", []))
                        if hasattr(msg, "type") and msg.type == "tool"
                        and "Overall score" in msg.content
                    ),
                    None,
                )

            if not feedback:
                raise ApplicationError(
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                    message="No evaluation feedback found in pipeline result"
                )

            logger.info("Quiz pipeline completed successfully")

            print(f"\n{'='*50}")
            print("  QUIZ RESULTS & EVALUATION")
            print(f"{'='*50}\n")
            print(feedback)
            print(f"\n{'='*50}\n")

            return str(feedback)

        except DatabaseError:
            logger.error("Database error during quiz execution")
            self.error_repository.store_error(
                file_name="main_agent.py",
                function_name="ask",
                error_message="Database connection failed"
            )
            raise

        except ApplicationError:
            raise

        except Exception as execution_error:
            logger.error(
                f"Quiz pipeline failed: {execution_error}",
                exc_info=True
            )
            self.error_repository.store_error(
                file_name="main_agent.py",
                function_name="ask",
                error_message=str(execution_error)
            )
            raise ApplicationError(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Quiz pipeline execution failed",
                original_exception=execution_error
            )