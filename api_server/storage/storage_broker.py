# storage/storage_broker.py

import logging
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_417_EXPECTATION_FAILED,
    HTTP_500_INTERNAL_SERVER_ERROR
)
from constants import DB_URI

from core.logging_config import get_logger
from core.logging_config import get_logger

logger = get_logger(__name__)



class StorageError(Exception):
    """Base exception for storage-related errors"""
    pass


class DatabaseManager:
    """
    Singleton manager for database engine with connection pooling.
    """
    _instance = None
    _engine = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_engine(self, uri: str = None, force_reconnect: bool = False):
        """Get or create database engine"""
        if force_reconnect and self._engine:
            self._engine.dispose()
            self._engine = None
        
        if self._engine is None:
            uri = uri or DB_URI
            self._engine = self._create_engine(uri)
            logger.info("Database engine initialized successfully")
        
        return self._engine
    
    def _create_engine(self, uri: str):
        """Create engine with connection pooling"""
        try:
            engine = create_engine(
                uri,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,    # Recycle connections every hour
                echo=False
            )
            
            # Test connection - FIX: Use text() for raw SQL
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            
            return engine
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise StorageError(f"Database connection failed: {e}")
    
    def is_healthy(self) -> bool:
        """Check if database connection is healthy"""
        if self._engine is None:
            return False
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def reset(self):
        """Reset the engine (useful for testing)"""
        if self._engine:
            self._engine.dispose()
        self._engine = None


# Global instance
_db_manager = DatabaseManager()


def get_engine(uri: str = None, force_reconnect: bool = False):
    """Convenience function to get database engine"""
    return _db_manager.get_engine(uri, force_reconnect)


@contextmanager
def session_scope():
    """Context manager for database sessions"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session error: {e}")
        raise
    finally:
        session.close()


def _handle_storage_exception(error: Exception, operation: str, **context) -> None:
    """Centralized storage exception handler"""
    logger.error(f"Storage error during {operation}: {error}", extra=context)
    
    error_msg = str(error).lower()
    
    if isinstance(error, StorageError):
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.DATABASE_ERROR,
            message=str(error),
            details=context
        )
    elif "integrity" in error_msg or "duplicate" in error_msg:
        raise APIException(
            status_code=HTTP_417_EXPECTATION_FAILED,
            error_code=ErrorCode.INTEGRITY_ERROR,
            message="Database integrity constraint violated",
            details={"operation": operation, "error": str(error), **context}
        )
    elif "not found" in error_msg:
        raise APIException(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.DATA_ERROR,
            message="Record not found",
            details={"operation": operation, "error": str(error), **context}
        )
    else:
        raise APIException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.DATABASE_ERROR,
            message=f"Database operation failed: {operation}",
            details={"error": str(error), **context}
        )


def validate_pagination(offset: int, limit: int, max_limit: int = 1000) -> None:
    """Validate pagination parameters"""
    if offset < 0:
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Offset must be non-negative",
            details={"offset": offset}
        )
    
    if limit < 1 or limit > max_limit:
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Limit must be between 1 and {max_limit}",
            details={"limit": limit, "max_limit": max_limit}
        )


def get_engine_with_retry(uri: str = DB_URI, retry_count: int = 3, retry_delay: int = 1):
    """Get database engine with retry logic - DEPRECATED, use get_engine() instead"""
    logger.warning("get_engine_with_retry is deprecated, use get_engine() instead")
    return get_engine(uri)


# Import the SQL wrapper functions
import storage.wrappers.sql_wrapper as medicom_store


def insert_record(item: Any) -> Any:
    """Insert a record into the database"""
    try:
        engine = get_engine()
        result = medicom_store.add_record(engine, item)
        logger.debug(f"Record inserted successfully: {type(item).__name__}")
        return result
    except Exception as e:
        _handle_storage_exception(e, "insert_record", record_type=type(item).__name__)


def get(
    table: Any,
    conditions: Optional[Dict] = None,
    join_tables: Optional[List] = None,
    eager_load_depth: Optional[int] = None,
    offset: int = 0,
    limit: int = 10,
    serialize: bool = False
) -> List[Any]:
    """Fetch records from the database"""
    validate_pagination(offset, limit)
    
    try:
        engine = get_engine()
        # logger.info("Attempting to get objects")
        result = medicom_store.get_records(
            engine, table, conditions, join_tables, 
            eager_load_depth, offset, limit, serialize
        )
        # logger.debug(f"Retrieved {len(result)} records")
        return result
    except Exception as e:
        _handle_storage_exception(
            e, "get_records", 
            table=str(table), 
            offset=offset, 
            limit=limit
        )


def get_by_id(
    table: Any,
    record_id: Union[int, str],
    serialize: bool = False
) -> Optional[Any]:
    """Fetch a single record by ID"""
    try:
        engine = get_engine()
        result = medicom_store.get_record_by_id(engine, table, record_id, serialize)
        return result
    except Exception as e:
        _handle_storage_exception(
            e, "get_record_by_id",
            table=str(table),
            record_id=record_id
        )


def count(
    table: Any,
    conditions: Optional[Dict] = None,
    join_tables: Optional[List] = None,
    group_by: Optional[List] = None
) -> int:
    """Count records in the database"""
    try:
        engine = get_engine()
        result = medicom_store.count_records(engine, table, conditions, join_tables, group_by)
        return result
    except Exception as e:
        _handle_storage_exception(e, "count_records", table=str(table))


def delete_record(item: Any) -> bool:
    """Delete a record from the database"""
    try:
        engine = get_engine()
        medicom_store.delete_record(engine, item)
        logger.debug(f"Record deleted successfully: {type(item).__name__}")
        return True
    except Exception as e:
        _handle_storage_exception(e, "delete_record", record_type=type(item).__name__)


def delete_by_id(table: Any, record_id: Union[int, str]) -> bool:
    """Delete a record by its ID"""
    try:
        engine = get_engine()
        result = medicom_store.delete_record_by_id(engine, table, record_id)
        logger.debug(f"Record {record_id} deleted")
        return result
    except Exception as e:
        _handle_storage_exception(e, "delete_record_by_id", table=str(table), record_id=record_id)


def update_record(item: Any) -> Any:
    """Update a record in the database"""
    try:
        engine = get_engine()
        result = medicom_store.update_record(engine, item)
        logger.debug(f"Record updated successfully: {type(item).__name__}")
        return result
    except Exception as e:
        _handle_storage_exception(e, "update_record", record_type=type(item).__name__)


def batch_insert(records: List[Any]) -> List[Any]:
    """Insert multiple records in batch"""
    if not records:
        return []
    
    try:
        engine = get_engine()
        result = medicom_store.add_records(engine, records)
        logger.debug(f"Batch inserted {len(result)} records")
        return result
    except Exception as e:
        _handle_storage_exception(e, "batch_insert", record_count=len(records))


def search_records(
    table: Any,
    join_tables: Optional[List] = None,
    eager_load_depth: Optional[int] = None,
    search_query: Optional[str] = None,
    search_fields: Optional[List[str]] = None,
    offset: int = 0,
    limit: int = 20
) -> List[Any]:
    """Search records using full-text search"""
    if limit > 100:
        limit = 100
    
    if search_query and len(search_query) < 2:
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Search query must be at least 2 characters long",
            details={"search_query": search_query, "min_length": 2}
        )
    
    try:
        engine = get_engine()
        result = medicom_store.search_records(
            engine, table, join_tables, eager_load_depth,
            search_query, search_fields, offset, limit
        )
        return result
    except Exception as e:
        _handle_storage_exception(e, "search_records", table=str(table))


def search_by_filter(
    table: Any,
    join_tables: Optional[List] = None,
    conditions: Optional[Dict] = None,
    labeled_attrs: Optional[List] = None,
    ordering_attr: Optional[str] = None,
    selected_fields: Optional[List] = None,
    eager_load_depth: Optional[int] = None,
    offset: int = 0,
    limit: int = 20
) :
    """Search records by geographic location"""
    if limit > 100:
        limit = 100
    
    try:
        engine = get_engine()
        result = medicom_store.get_records_by_filter(
            engine, table,
            join_tables=join_tables,
            conditions=conditions,
            labeled_attrs=labeled_attrs,
            ordering_attr=ordering_attr,
            selected_fields=selected_fields,
            eager_load_depth=eager_load_depth,
            offset=offset,
            limit=limit
        )
        return result
    except Exception as e:
        _handle_storage_exception(e, "search_by_filter", table=str(table))


def health_check() -> Dict[str, Any]:
    """Check database health"""
    return {
        "status": "healthy" if _db_manager.is_healthy() else "unhealthy",
        "engine_initialized": _db_manager._engine is not None
    }


def reset_engine():
    """Reset the database engine (mainly for testing)"""
    _db_manager.reset()