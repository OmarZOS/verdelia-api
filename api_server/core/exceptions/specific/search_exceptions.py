# core/exceptions/specific/search_exceptions.py
"""
Search-specific exceptions for the Verdelia system.
"""

from typing import Optional, Dict, Any, List
from enum import Enum

from core.messages.error_codes import ErrorCode
from core.messages.error_messages import get_error_message
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_410_GONE,
    HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
    HTTP_417_EXPECTATION_FAILED,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_502_BAD_GATEWAY,
    HTTP_503_SERVICE_UNAVAILABLE,
    HTTP_504_GATEWAY_TIMEOUT,
    HTTP_511_NETWORK_AUTHENTICATION_REQUIRED
)
from core.exceptions.handler import APIException

# ==================== Base Search Exception ====================

class SearchException(APIException):
    """Base exception for all search-related errors"""
    
    def __init__(
        self,
        message: str = "Search service error",
        error_code: ErrorCode = ErrorCode.SEARCH_ERROR,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details or {}
        )


# ==================== Search Query Exceptions ====================

class SearchQueryTooShortException(SearchException):
    """Exception when search query is too short"""
    
    def __init__(
        self,
        min_length: int = 2,
        provided_length: int = None,
        query: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        error_details["min_length"] = min_length
        if provided_length is not None:
            error_details["provided_length"] = provided_length
        if query:
            error_details["query"] = query
        
        message = f"Search query must be at least {min_length} characters long"
        if provided_length is not None:
            message = f"Search query must be at least {min_length} characters long (provided: {provided_length} characters)"
        elif query:
            message = f"Search query '{query}' must be at least {min_length} characters long"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_QUERY_TOO_SHORT,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class SearchQueryTooLongException(SearchException):
    """Exception when search query is too long"""
    
    def __init__(
        self,
        max_length: int = 100,
        provided_length: int = None,
        query: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        error_details["max_length"] = max_length
        if provided_length is not None:
            error_details["provided_length"] = provided_length
        if query:
            error_details["query"] = query
        
        message = f"Search query must be at most {max_length} characters long"
        if provided_length is not None:
            message = f"Search query must be at most {max_length} characters long (provided: {provided_length} characters)"
        elif query:
            message = f"Search query '{query}' must be at most {max_length} characters long"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_QUERY_TOO_LONG,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class SearchQueryEmptyException(SearchException):
    """Exception when search query is empty"""
    
    def __init__(
        self,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        message = "Search query cannot be empty"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_QUERY_EMPTY,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


# ==================== Search Entity Exceptions ====================

class SearchEntityNotFoundException(SearchException):
    """Exception when an invalid entity type is requested"""
    
    def __init__(
        self,
        entity_type: str = None,
        valid_types: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if entity_type:
            error_details["invalid_entity"] = entity_type
        if valid_types:
            error_details["valid_entities"] = valid_types
        
        message = "Invalid search entity type"
        if entity_type:
            message = f"Invalid search entity type: '{entity_type}'"
        if valid_types and len(valid_types) > 0:
            message += f". Valid entity types: {', '.join(valid_types)}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_ENTITY_NOT_FOUND,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class SearchEntityNotSupportedException(SearchException):
    """Exception when search is not supported for an entity type"""
    
    def __init__(
        self,
        entity_type: str = None,
        reason: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if entity_type:
            error_details["entity_type"] = entity_type
        if reason:
            error_details["reason"] = reason
        
        message = "Search not supported for this entity type"
        if entity_type:
            message = f"Search is not supported for entity type '{entity_type}'"
        if reason:
            message += f" - {reason}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_ENTITY_NOT_SUPPORTED,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


# ==================== Search Field Exceptions ====================

class SearchFieldNotFoundException(SearchException):
    """Exception when a search field is not found"""
    
    def __init__(
        self,
        field_name: str = None,
        entity_type: str = None,
        available_fields: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if field_name:
            error_details["field_name"] = field_name
        if entity_type:
            error_details["entity_type"] = entity_type
        if available_fields:
            error_details["available_fields"] = available_fields
        
        message = "Search field not found"
        if field_name and entity_type:
            message = f"Search field '{field_name}' not found for entity type '{entity_type}'"
        elif field_name:
            message = f"Search field '{field_name}' not found"
        
        if available_fields and len(available_fields) > 0:
            message += f". Available fields: {', '.join(available_fields)}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_FIELD_NOT_FOUND,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class SearchFieldInvalidException(SearchException):
    """Exception when a search field is invalid"""
    
    def __init__(
        self,
        field_name: str = None,
        entity_type: str = None,
        reason: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if field_name:
            error_details["field_name"] = field_name
        if entity_type:
            error_details["entity_type"] = entity_type
        if reason:
            error_details["reason"] = reason
        
        message = "Invalid search field"
        if field_name and entity_type:
            message = f"Search field '{field_name}' is invalid for entity type '{entity_type}'"
        elif field_name:
            message = f"Search field '{field_name}' is invalid"
        if reason:
            message += f" - {reason}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_FIELD_INVALID,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


# ==================== Search Execution Exceptions ====================

class SearchExecutionException(SearchException):
    """Base exception for search execution errors"""
    
    def __init__(
        self,
        message: str = "Search operation failed",
        error_code: ErrorCode = ErrorCode.SEARCH_EXECUTION_FAILED,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class SearchTimeoutException(SearchExecutionException):
    """Exception when search operation times out"""
    
    def __init__(
        self,
        timeout_seconds: int = None,
        entity_type: str = None,
        query: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        if entity_type:
            error_details["entity_type"] = entity_type
        if query:
            error_details["query"] = query
        
        message = "Search operation timed out"
        if timeout_seconds:
            message = f"Search operation timed out after {timeout_seconds} seconds"
        elif entity_type:
            message = f"Search operation for entity type '{entity_type}' timed out"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_TIMEOUT,
            status_code=HTTP_504_GATEWAY_TIMEOUT,
            details=error_details
        )


class SearchIndexException(SearchExecutionException):
    """Exception when search index is unavailable or corrupted"""
    
    def __init__(
        self,
        index_name: str = None,
        error: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if index_name:
            error_details["index_name"] = index_name
        if error:
            error_details["index_error"] = error
        
        message = "Search index error"
        if index_name:
            message = f"Search index '{index_name}' is unavailable or corrupted"
        if error:
            message += f" - {error}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_INDEX_ERROR,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class SearchDatabaseConnectionException(SearchExecutionException):
    """Exception when database connection fails during search"""
    
    def __init__(
        self,
        entity_type: str = None,
        error: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if entity_type:
            error_details["entity_type"] = entity_type
        if error:
            error_details["connection_error"] = error
        
        message = "Database connection error during search"
        if entity_type:
            message = f"Failed to connect to database while searching for '{entity_type}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_DB_CONNECTION_ERROR,
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            details=error_details
        )


# ==================== Search Result Exceptions ====================

class NoSearchResultsException(SearchException):
    """Exception when no search results are found (optional - can be used for strict searches)"""
    
    def __init__(
        self,
        query: str = None,
        entity_type: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if query:
            error_details["query"] = query
        if entity_type:
            error_details["entity_type"] = entity_type
        
        message = "No search results found"
        if query and entity_type:
            message = f"No {entity_type} found matching '{query}'"
        elif query:
            message = f"No results found for '{query}'"
        elif entity_type:
            message = f"No {entity_type} found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NO_SEARCH_RESULTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class SearchResultsTruncatedException(SearchException):
    """Exception when search results are truncated due to limits"""
    
    def __init__(
        self,
        total_count: int = None,
        returned_count: int = None,
        max_limit: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if total_count is not None:
            error_details["total_count"] = total_count
        if returned_count is not None:
            error_details["returned_count"] = returned_count
        if max_limit is not None:
            error_details["max_limit"] = max_limit
        
        message = "Search results truncated"
        if total_count is not None and returned_count is not None:
            message = f"Search returned {returned_count} of {total_count} results (limited)"
        elif max_limit is not None:
            message = f"Search results limited to {max_limit} per request"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_RESULTS_TRUNCATED,
            status_code=HTTP_410_GONE,
            details=error_details
        )


# ==================== Rate Limiting Exceptions ====================

class SearchRateLimitException(SearchException):
    """Exception when search rate limit is exceeded"""
    
    def __init__(
        self,
        limit_per_minute: int = None,
        retry_after_seconds: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if limit_per_minute:
            error_details["limit_per_minute"] = limit_per_minute
        if retry_after_seconds:
            error_details["retry_after_seconds"] = retry_after_seconds
        
        message = "Search rate limit exceeded"
        if limit_per_minute:
            message = f"Search rate limit exceeded (max {limit_per_minute} requests per minute)"
        if retry_after_seconds:
            message += f". Please retry after {retry_after_seconds} seconds"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_RATE_LIMIT_EXCEEDED,
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            details=error_details
        )


# ==================== Geographic Search Exceptions ====================

class GeographicSearchException(SearchException):
    """Base exception for geographic search errors"""
    
    def __init__(
        self,
        message: str = "Geographic search error",
        error_code: ErrorCode = ErrorCode.SEARCH_ERROR,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class InvalidCoordinatesException(GeographicSearchException):
    """Exception when coordinates are invalid"""
    
    def __init__(
        self,
        longitude: float = None,
        latitude: float = None,
        reason: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if longitude is not None:
            error_details["longitude"] = longitude
        if latitude is not None:
            error_details["latitude"] = latitude
        if reason:
            error_details["reason"] = reason
        
        message = "Invalid coordinates"
        if longitude is not None and (longitude < -180 or longitude > 180):
            message = f"Longitude must be between -180 and 180 (provided: {longitude})"
        elif latitude is not None and (latitude < -90 or latitude > 90):
            message = f"Latitude must be between -90 and 90 (provided: {latitude})"
        elif reason:
            message = reason
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_INVALID_COORDINATES,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class InvalidSearchRadiusException(GeographicSearchException):
    """Exception when search radius is invalid"""
    
    def __init__(
        self,
        radius_km: float = None,
        min_radius: float = None,
        max_radius: float = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if radius_km is not None:
            error_details["radius_km"] = radius_km
        if min_radius is not None:
            error_details["min_radius"] = min_radius
        if max_radius is not None:
            error_details["max_radius"] = max_radius
        
        message = "Invalid search radius"
        if radius_km is not None and radius_km <= 0:
            message = f"Search radius must be positive (provided: {radius_km} km)"
        elif min_radius is not None and max_radius is not None:
            message = f"Search radius must be between {min_radius} and {max_radius} km"
        elif min_radius is not None and radius_km is not None and radius_km < min_radius:
            message = f"Search radius must be at least {min_radius} km (provided: {radius_km} km)"
        elif max_radius is not None and radius_km is not None and radius_km > max_radius:
            message = f"Search radius cannot exceed {max_radius} km (provided: {radius_km} km)"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_INVALID_RADIUS,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


# ==================== Multi-Search Exceptions ====================

class MultiSearchException(SearchException):
    """Base exception for multi-search operations"""
    
    def __init__(
        self,
        message: str = "Multi-search operation failed",
        error_code: ErrorCode = ErrorCode.SEARCH_ERROR,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class MultiSearchPartialFailureException(MultiSearchException):
    """Exception when some entity searches fail but others succeed"""
    
    def __init__(
        self,
        succeeded_entities: List[str] = None,
        failed_entities: List[str] = None,
        errors: Dict[str, str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if succeeded_entities:
            error_details["succeeded_entities"] = succeeded_entities
        if failed_entities:
            error_details["failed_entities"] = failed_entities
        if errors:
            error_details["errors"] = errors
        
        message = "Multi-search completed with partial failures"
        if failed_entities and succeeded_entities:
            message = f"Multi-search completed: {len(succeeded_entities)} succeeded, {len(failed_entities)} failed"
        elif failed_entities:
            message = f"Multi-search failed for entities: {', '.join(failed_entities)}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SEARCH_PARTIAL_FAILURE,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )