from dataclasses import dataclass
import os
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Settings:
    db_port: str
    db_host: str
    db_name: str
    db_username: str
    db_password: str
    port: int
    host: str
    log_level: str
    model_id:str
    provider:str
    context_7_mcp_server_url:str 
    pep_8_mcp_server_url:str
    context_7_api_key:str
    pylint_mcp_server_url:str
    duckduckgo:str
    db_name_checkpoint:str

def get_setting():
    return Settings(
        db_port=os.getenv('DB_PORT', '5432'),
        db_host=os.getenv('DB_HOST', 'localhost'),
        db_name=os.getenv('DB_NAME', 'code_assistant'),
        db_username=os.getenv('DB_USERNAME', 'postgres'),
        db_password=os.getenv('DB_PASSWORD', '123456'),
        port=int(os.getenv('PORT', '8080')),
        host=os.getenv('HOST', '0.0.0.0'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        model_id=os.getenv('MODEL_ID'),
        provider=os.getenv("PROVIDER"),
        context_7_mcp_server_url=os.getenv("CONTEXT_7_MCP_SERVER_URL"),
        pep_8_mcp_server_url=os.getenv("PEP_8_MCP_SERVER_URL"),
        context_7_api_key=os.getenv("CONTEXT_7_API_KEY"),
        duckduckgo=os.getenv("DUCK_DUCK_GO"),
        pylint_mcp_server_url=os.getenv("PYLINT_MCP_SERVER_URL"),
        db_name_checkpoint=os.getenv("DB_NAME_CHECKPOINT")
    )

settings = get_setting()