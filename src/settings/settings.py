from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseSettings:
    """Database connection configuration."""
    
    port: str
    host: str
    name: str
    username: str
    password: str
    checkpoint_database_name: str
    
    def get_connection_uri(self) -> str:
        """
        Generate PostgreSQL connection URI.
        
        Returns:
            str: PostgreSQL connection string.
        """
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.name}"
        )
    
    def get_async_connection_uri(self) -> str:
        """
        Generate async PostgreSQL connection URI for LangGraph state management.
        
        Returns:
            str: Async PostgreSQL connection string.
        """
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.checkpoint_database_name}"
        )


@dataclass
class AWSSettings:
    """AWS Bedrock configuration for LLM access."""
    
    region: str
    model_id: str
    provider: str
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None


@dataclass
class APISettings:
    """API server configuration."""
    
    port: int
    host: str
    log_level: str


@dataclass
class Settings:
    """Complete application configuration."""
    
    database: DatabaseSettings
    aws: AWSSettings
    api: APISettings
    context7_api_key: Optional[str] = None
    pylint_mcp_server_url: Optional[str] = None
    pep8_mcp_server_url: Optional[str] = None
    duckduckgo_mcp_server_url: Optional[str] = None

@lru_cache
def load_settings() -> Settings:
    """
    Load and construct settings from environment variables.
    
    All required environment variables must be set in .env file
    or as system environment variables.
    
    Returns:
        Settings: Fully configured settings object.
        
    Raises:
        ValueError: If any required environment variable is missing.
    """
    # Database configuration
    database = DatabaseSettings(
        port=os.getenv("DB_PORT", "5432"),
        host=os.getenv("DB_HOST", "localhost"),
        name=os.getenv("DB_NAME", "quiz_assistant"),
        username=os.getenv("DB_USERNAME", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        checkpoint_database_name=os.getenv("DB_NAME_CHECKPOINT", "quiz_assistant")
    )
    
    # AWS configuration
    aws = AWSSettings(
        region=os.getenv("AWS_REGION", "us-east-1"),
        model_id=os.getenv("MODEL_ID", ""),
        provider=os.getenv("PROVIDER", "amazon"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    
    # API configuration
    api = APISettings(
        port=int(os.getenv("PORT", "8080")),
        host=os.getenv("HOST", "0.0.0.0"),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # Complete settings
    settings = Settings(
        database=database,
        aws=aws,
        api=api,
        context7_api_key=os.getenv("CONTEXT_7_API_KEY"),
        pylint_mcp_server_url=os.getenv("PYLINT_MCP_SERVER_URL"),
        pep8_mcp_server_url=os.getenv("PEP_8_MCP_SERVER_URL"),
        duckduckgo_mcp_server_url=os.getenv("DUCK_DUCK_GO")
    )
    
    return settings


settings = load_settings()