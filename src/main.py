from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn
from routes.routes import router
from migration.create_tables import Migration
from utils.logger import logger

# SQ 1.0 - SQ 1.8 : Load environment variables from .env file, Instantiate Migration and call create_tables(), Initialize FastAPI app with title and version, Register all API routes under prefix /api/v1

load_dotenv()

try:
    migration = Migration()
    migration.create_tables()
    logger.info("Database tables created successfully")
except Exception as e:
    logger.warning(f"Migration failed: {e}")

app = FastAPI(
    title="Multi-Agent Code Pipeline",
    version="1.0.0"
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )