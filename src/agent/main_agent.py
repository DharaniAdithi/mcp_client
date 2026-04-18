import logging
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from agent.system_prompt import SystemPrompt
from utils.helper import get_llm, log_error
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from constant.constant import DB_URI
from tools.tools import generate_quiz, evaluate_answers
from langgraph.types import Command
from models.models import QuizState
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

logger = logging.getLogger(__name__)


STEP_CONFIG={"question_generator":{
            "tools":[generate_quiz]
        },"answer_evaluator":{
            "tools":[evaluate_answers]
        },"END":{
            "tools":[]
        }
        }

class QuizMainAgent:                                  

    def __init__(self):
        logger.info("QuizMainAgent init")
        self.llm    = get_llm(max_tokens=500, temperature=0)
        self.agent  = None
        self.prompt = SystemPrompt()
        self.db_url = DB_URI


    # SQ 1.28 - SQ 1.31 : Read current_step from agent state, Load STEP_CONFIG entry for current_step to get allowed tools, Override request tools with step-restricted tool list, Pass overridden request to handler and return response
    @staticmethod
    @wrap_model_call
    async def apply_step_config(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        try:
            print("middleware called")
            """Read current_step from state and apply matching prompt + tools asynchronously."""
            print( request.state.get("current_step"))
            current_step = request.state.get("current_step") or "question_generator"
            print("current_step",current_step)
            step_cfg = STEP_CONFIG[current_step]
            print(step_cfg)
            request = request.override(
                tools=step_cfg["tools"],
            )
            return await handler(request)
        except Exception as e:
            raise e
    
    # SQ 1.32 : Create agent via create_agent() with LLM, tools, middleware, QuizState schema, orchestrator_prompt and checkpointer
    async def _setup_agent(self, checkpointer):
        try:
            logger.info("QuizMainAgent._setup_agent")
            self.agent = create_agent(
                model=self.llm,
                tools=[generate_quiz, evaluate_answers],
                middleware=[self.apply_step_config],               
                state_schema=QuizState,
                system_prompt=self.prompt.orchestrator_prompt,
                checkpointer=checkpointer,
            )
        except Exception as e:
            log_error("main_agent.py", "_setup_agent", e)
            raise

   # SQ 1.23 - SQ 1.80: Open async PostgreSQL connection, Call _setup_agent() if agent is not yet initialized, Build initial QuizState and invoke agent, Detect __interrupt__ in result after generate_quiz pauses graph, Extract questions, difficulty, num_q from interrupt_value, Build Command and re-invoke agent, Extract final message content from result

    async def ask(self, user_query: str, thread_id: str, num_questions: int, difficulty:str,
    ) -> str:
        try:
            logger.info(f"QuizMainAgent.ask - thread={thread_id} n={num_questions} diff={difficulty}")

            async with AsyncPostgresSaver.from_conn_string(self.db_url) as checkpointer:
                await checkpointer.setup()

                if self.agent is None:
                    await self._setup_agent(checkpointer)

                result = await self.agent.ainvoke(
                    {
                        "messages": [HumanMessage(content=user_query)],
                        "user_query": user_query,
                        "num_questions": num_questions,  
                        "difficulty": difficulty,       
                        "questions": [],
                        "answers":[],
                        "feedback": "",
                        "current_step":"question_generator",
                    },
                    {"configurable": {"thread_id": thread_id}},
                )

                print("RESULT=====================================================================",result)

                if "__interrupt__" in result:
                    interrupt_value = result["__interrupt__"][0].value

                    if interrupt_value["type"] == "quiz":
                        questions = interrupt_value["questions"]
                        difficulty = interrupt_value["difficulty"]
                        num_q = interrupt_value["num_questions"]

                        print(f"\n=============================================================")
                        print(f" quiz questions")
                        print(f"=======================================================================")
                        for q in questions:
                            print(f"{q}")
                        print(f"=========================================================================================\n")

                        user_answers = []
                        for i, _ in enumerate(questions, 1):
                            ans = input(f"Answer {i}: ").strip()
                            user_answers.append(ans)
                        print("USER ANSWERS===============",user_answers)

                    resume_command = Command(resume=user_answers)
                    result = await self.agent.ainvoke(
                        resume_command,
                        {"configurable": {"thread_id": thread_id}},
                    )

                response = result["messages"][-1].content
                print(response)
                return str(response)

        #SQ 1.82 - SQ 1.93 return log_error and raise
        except Exception as e:
            log_error("main_agent.py", "ask", e)
            raise