import logging
from langchain.agents import create_agent
from agent.system_prompt import SystemPrompt
from utils.helper import get_llm, log_error

logger = logging.getLogger(__name__)

# SQ 1.65 - SQ 1.72: Return existing singleton if already initialized, Instantiate QuizGeneratorAgent and call _setup(), Create agent with LLM, toolsand quiz_prompt, Store instance as class-level singleton
class ReviewAgent:                       
    _instance = None

    def __init__(self):
        self.llm = None
        self.prompt = None
        self.evaluator_agent = None            

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            instance = cls()
            await instance._setup()           
            cls._instance = instance
        return cls._instance

    async def _setup(self):
        logger.info("ReviewAgent._setup")
        self.llm  = get_llm(max_tokens=500, temperature=0)
        self.prompt  = SystemPrompt()
        self.evaluator_agent = await self._build_agent()   

    async def _build_agent(self):
        try:
            return create_agent(
                model=self.llm,
                tools=[],
                system_prompt=self.prompt.review_prompt,
            )
        except Exception as e:
            log_error("review_agent.py", "_build_agent", e)
            raise