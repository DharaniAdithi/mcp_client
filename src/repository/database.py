import logging
from typing import Generator

from sqlalchemy import create_engine, inspect, text, Engine
from sqlalchemy.orm import sessionmaker, Session

from src.settings.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """
    Singleton database connection manager.
    
    Manages SQLAlchemy engine creation, session factory initialization,
    and connection validation. Implements the singleton pattern to ensure
    only one database instance exists throughout the application lifecycle.
    """
    
    _instance: Database = None
    _engine: Engine = None
    _session_local: sessionmaker = None
    
    def __new__(cls) -> Database:
        """
        Create or return singleton instance.
        
        Returns:
            Database: Singleton database instance.
        """
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """
        Initialize database engine and session factory.
        
        Creates SQLAlchemy engine with connection pooling and
        configures session factory with proper settings.
        
        Raises:
            Exception: If engine creation fails.
        """
        try:
            connection_uri = settings.database.get_connection_uri()
            
            self._engine = create_engine(
                connection_uri,
                pool_pre_ping=True,  
                echo=False,
                pool_size=10,
                max_overflow=20
            )
            
            self._session_local = sessionmaker(
                bind=self._engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=True
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as database_error:
            logger.error(f"Failed to initialize database: {database_error}", exc_info=True)
            raise
    
    @property
    def engine(self) -> Engine:
        """
        Get SQLAlchemy engine instance.
        
        Returns:
            Engine: Configured SQLAlchemy engine.
        """
        if self._engine is None:
            self._initialize()
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """
        Get session factory.
        
        Returns:
            sessionmaker: Configured session factory.
        """
        if self._session_local is None:
            self._initialize()
        return self._session_local
    
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session context manager.
        
        Yields a new database session and ensures proper cleanup.
        Use with 'with' statement for automatic session closure.
        
        Yields:
            Session: SQLAlchemy session instance.
            
        Example:
            >>> with database.get_session() as session:
            ...     result = session.query(ErrorLog).first()
        """
        session = self.session_factory()
        try:
            yield session
        except Exception as session_error:
            logger.error(f"Session error: {session_error}", exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_inspector(self):
        """
        Get database inspector for schema introspection.
        
        Returns:
            Inspector: SQLAlchemy inspector instance.
        """
        return inspect(self.engine)
    
    def test_connection(self) -> bool:
        """
        Test database connectivity.
        
        Executes a simple query to verify the database connection
        is working properly.
        
        Returns:
            bool: True if connection is successful, False otherwise.
            
        Example:
            >>> database = Database()
            >>> is_connected = database.test_connection()
        """
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection test passed")
            return True
        except Exception as connection_error:
            logger.error(f"Database connection test failed: {connection_error}")
            return False
    
    def dispose_pool(self) -> None:
        """
        Close all database connections in the pool.
        
        Useful for graceful shutdown or connection pool refresh.
        """
        if self._engine is not None:
            self._engine.dispose()
            logger.info("Database connection pool disposed")


database = Database()