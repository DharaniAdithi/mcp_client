import logging
from typing import Optional

from langchain.agents import create_agent

from src.agent.system_prompt import SystemPrompt
from src.utils.helper import initialize_language_model
from src.utils.error_codes import AgentInitializationError

logger = logging.getLogger(__name__)


class ReviewAgent:
    """
    Quiz answer evaluation and review agent.
    
    Evaluates user-provided answers against quiz questions and generates
    detailed feedback with verdicts, explanations, and improvement tips.
    Implements singleton pattern to ensure only one instance exists.
    
    Attributes:
        llm: Language model instance for answer evaluation.
        prompt: System prompt template for the agent.
        agent: LangChain agent instance.
    """
    
    _instance: Optional['ReviewAgent'] = None
    
    def __init__(self) -> None:
        """Initialize ReviewAgent attributes."""
        self.llm = None
        self.prompt = None
        self.agent = None
    
    @classmethod
    async def get_instance(cls) -> 'ReviewAgent':
        """
        Get singleton instance of ReviewAgent.
        
        Creates and initializes the agent on first call, then returns
        the same instance on subsequent calls.
        
        Returns:
            ReviewAgent: Singleton instance of the agent.
            
        Raises:
            AgentInitializationError: If agent setup fails.
            
        Example:
            >>> reviewer = await ReviewAgent.get_instance()
            >>> result = await reviewer.agent.ainvoke(...)
        """
        if cls._instance is None:
            instance = cls()
            await instance._setup()
            cls._instance = instance
        return cls._instance
    
    async def _setup(self) -> None:
        """
        Initialize the review agent.
        
        Configures the language model and builds the agent instance
        with appropriate system prompts for answer evaluation.
        
        Raises:
            AgentInitializationError: If initialization fails.
        """
        try:
            logger.info("Initializing ReviewAgent")

            self.llm = initialize_language_model(
                max_tokens=1000,
                temperature=0.0 
            )
            
            self.prompt = SystemPrompt()
            
            self.agent = await self._build_agent()
            
            logger.info("ReviewAgent initialized successfully")
            
        except Exception as setup_error:
            logger.error(
                f"ReviewAgent initialization failed: {setup_error}",
                exc_info=True
            )
            raise AgentInitializationError(
                message="Failed to initialize ReviewAgent",
                original_exception=setup_error
            )
    
    async def _build_agent(self):
        """
        Build the review/evaluation LangChain agent.
        
        Creates a ReAct-style agent with the review prompt as system context.
        The agent has no external tools and relies purely on the LLM.
        
        Returns:
            Agent: Configured LangChain agent.
            
        Raises:
            AgentInitializationError: If agent creation fails.
        """
        try:
            agent = create_agent(
                model=self.llm,
                tools=[],  
                system_prompt=self.prompt.review_prompt,
            )
            
            logger.debug("Review agent built successfully")
            return agent
            
        except Exception as build_error:
            logger.error(
                f"Failed to build review agent: {build_error}",
                exc_info=True
            )
            raise AgentInitializationError(
                message="Failed to build review agent",
                original_exception=build_error
            )