from datetime import datetime
import logging
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, Request
from dotenv import load_dotenv
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.routes.routes import router
from src.migration.create_tables import Migration
from src.utils.logger import setup_logger
from src.constant.constant import API_PREFIX

load_dotenv()

logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_database()
    yield
    service = app.state.quiz_service          
    await service.quiz_agent.close()

def initialize_database() -> None:
    """
    Initialize database by running migrations.
    
    Creates necessary tables if they don't exist. Logs warnings if migration fails
    but allows application to continue running.
    
    Raises:
        Exception: Propagates any unexpected errors during migration.
    """
    try:
        migration = Migration()
        migration.create_tables()
        logger.info("Database migrations completed successfully")
    except Exception as migration_error:
        logger.warning(
            f"Database migration completed with warning: {migration_error}",
            exc_info=True
        )


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Manage application lifecycle events.
    
    Handles startup initialization and graceful shutdown.
    
    Args:
        application: FastAPI application instance.
        
    Yields:
        None: Control is yielded back to the application.
    """
    
    logger.info("Starting Multi-Agent Quiz Pipeline application")
    initialize_database()
    yield
    logger.info("Shutting down Multi-Agent Quiz Pipeline application")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application instance.
    
    Initializes the FastAPI app with metadata, registers routes,
    and sets up lifecycle management.
    
    Returns:
        FastAPI: Configured application instance ready to accept requests.
    """
    application = FastAPI(
        title="Multi-Agent Quiz Pipeline",
        description="An intelligent quiz generation and evaluation system powered by LangGraph",
        version="1.0.0",
        lifespan=lifespan
    )

    application.include_router(prefix=API_PREFIX, router = router)

    logger.info("FastAPI application created and configured")
    return application


app = create_application()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = str(uuid.uuid4())

    error_details = [
        {
            "field": ".".join(map(str, err["loc"])),
            "message": err["msg"]
        }
        for err in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "status_code": 422,
            "status": "error",
            "message": "Validation Error",
            "error": {
                "type": "ValidationError",
                "details": error_details
            },
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global catch-all for unhandled exceptions within the MCP server.

    Args:
        request (Request): The incoming HTTP request.
        exc (Exception): The error instance raised.

    Returns:
        JSONResponse: A standardized 500 Internal Server Error response.
    """
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "status": "error",
            "message": "Internal Server Error",
            "error": str(exc),
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        },
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )