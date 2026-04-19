import logging
from typing import Optional

from langchain.agents import create_agent

from src.agent.system_prompt import SystemPrompt
from src.utils.helper import initialize_language_model
from src.utils.error_codes import AgentInitializationError

logger = logging.getLogger(__name__)


class QuizGeneratorAgent:
    """
    Quiz question generation agent.
    
    Responsible for generating quiz questions on any topic at specified
    difficulty levels. Implements singleton pattern to ensure only one
    instance exists throughout the application lifetime.
    
    Attributes:
        llm: Language model instance for question generation.
        prompt: System prompt template for the agent.
        agent: LangChain agent instance.
    """
    
    _instance: Optional['QuizGeneratorAgent'] = None
    
    def __init__(self) -> None:
        """Initialize QuizGeneratorAgent attributes."""
        self.llm = None
        self.prompt = None
        self.agent = None
    
    @classmethod
    async def get_instance(cls) -> 'QuizGeneratorAgent':
        """
        Get singleton instance of QuizGeneratorAgent.
        
        Creates and initializes the agent on first call, then returns
        the same instance on subsequent calls.
        
        Returns:
            QuizGeneratorAgent: Singleton instance of the agent.
            
        Raises:
            AgentInitializationError: If agent setup fails.
            
        Example:
            >>> generator = await QuizGeneratorAgent.get_instance()
            >>> result = await generator.agent.ainvoke(...)
        """
        if cls._instance is None:
            instance = cls()
            await instance._setup()
            cls._instance = instance
        return cls._instance
    
    async def _setup(self) -> None:
        """
        Initialize the quiz generator agent.
        
        Configures the language model and builds the agent instance
        with appropriate system prompts.
        
        Raises:
            AgentInitializationError: If initialization fails.
        """
        try:
            logger.info("Initializing QuizGeneratorAgent")
            
            self.llm = initialize_language_model(
                max_tokens=500,
                temperature=0.7
            )
            
            self.prompt = SystemPrompt()
            
            self.agent = await self._build_agent()
            
            logger.info("QuizGeneratorAgent initialized successfully")
            
        except Exception as setup_error:
            logger.error(
                f"QuizGeneratorAgent initialization failed: {setup_error}",
                exc_info=True
            )
            raise AgentInitializationError(
                message="Failed to initialize QuizGeneratorAgent",
                original_exception=setup_error
            )
    
    async def _build_agent(self):
        """
        Build the quiz generator LangChain agent.
        
        Creates a ReAct-style agent with the quiz prompt as system context.
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
                system_prompt=self.prompt.quiz_prompt,
            )
            
            logger.debug("Quiz generator agent built successfully")
            return agent
            
        except Exception as build_error:
            logger.error(
                f"Failed to build quiz generator agent: {build_error}",
                exc_info=True
            )
            raise AgentInitializationError(
                message="Failed to build quiz generator agent",
                original_exception=build_error
            )