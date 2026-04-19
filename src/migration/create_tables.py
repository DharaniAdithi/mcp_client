"""
Database migration and table creation.

Handles schema initialization and table creation on application startup.
Inspects existing tables and creates missing ones as needed.
"""

import logging
from typing import List, Dict, Type

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase

from src.repository.schema.schema import ErrorLog, Base
from src.repository.database import database

logger = logging.getLogger(__name__)


TABLE_CREATION_ORDER: List[str] = [
    ErrorLog.__tablename__,
]

TABLE_MODEL_MAP: Dict[str, Type[DeclarativeBase]] = {
    ErrorLog.__tablename__: ErrorLog,
}


class Migration:
    """
    Database migration manager.
    
    Handles schema initialization by inspecting the current database state
    and creating any missing tables. Uses SQLAlchemy ORM models as the
    source of truth for schema definition.
    """
    
    def __init__(self, db_instance=None) -> None:
        """
        Initialize Migration.
        
        Args:
            db_instance: Database instance (optional, defaults to singleton).
        """
        self.database = db_instance or database
        self.engine = self.database.engine
        self.inspector = self.database.get_inspector()
    
    def create_tables(self) -> None:
        """
        Create missing database tables.
        
        Iterates through the defined table list and creates any tables that
        don't exist in the current database. This is safe to call multiple
        times as it checks for existence before creation.
        
        Raises:
            Exception: If table creation fails (propagates SQLAlchemy errors).
            
        Example:
            >>> migration = Migration()
            >>> migration.create_tables()  # Creates missing tables
        """
        try:
            logger.info("Starting database migration")
            
            created_count = 0
            for table_name in TABLE_CREATION_ORDER:
                if self._table_exists(table_name):
                    logger.info(f"Table '{table_name}' already exists")
                else:
                    self._create_table(table_name)
                    created_count += 1
            
            if created_count > 0:
                logger.info(f"Successfully created {created_count} table(s)")
            else:
                logger.info("All tables already exist, no migration needed")
                
        except Exception as migration_error:
            logger.error(
                f"Database migration failed: {migration_error}",
                exc_info=True
            )
            raise
    
    def _table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check.
        
        Returns:
            bool: True if table exists, False otherwise.
        """
        return self.inspector.has_table(table_name)
    
    def _create_table(self, table_name: str) -> None:
        """
        Create a single table.
        
        Args:
            table_name: Name of the table to create.
            
        Raises:
            KeyError: If table not found in model map.
            Exception: If table creation fails.
        """
        try:
            if table_name not in TABLE_MODEL_MAP:
                raise KeyError(f"No model defined for table: {table_name}")
            
            model_class = TABLE_MODEL_MAP[table_name]
            model_class.__table__.create(bind=self.engine)
            
            logger.info(f"Successfully created table: {table_name}")
            
        except Exception as table_creation_error:
            logger.error(
                f"Failed to create table '{table_name}': {table_creation_error}",
                exc_info=True
            )
            raise
    
    def drop_all_tables(self) -> None:
        """
        Drop all application tables.
        
        WARNING: This is a destructive operation that removes all tables.
        Use only for testing or development environments.
        
        Raises:
            Exception: If table drop fails.
        """
        try:
            logger.warning("Dropping all application tables")
            Base.metadata.drop_all(bind=self.engine)
            logger.info("All tables dropped successfully")
        except Exception as drop_error:
            logger.error(f"Failed to drop tables: {drop_error}", exc_info=True)
            raise
    
    def recreate_tables(self) -> None:
        """
        Drop and recreate all application tables.
        
        WARNING: This is a destructive operation that removes all data.
        Use only for development or testing.
        
        Raises:
            Exception: If operation fails.
        """
        try:
            logger.warning("Recreating all application tables")
            self.drop_all_tables()
            self.create_tables()
            logger.info("Tables recreated successfully")
        except Exception as recreate_error:
            logger.error(f"Failed to recreate tables: {recreate_error}", exc_info=True)
            raise