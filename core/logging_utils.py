"""
Logging utilities for consistent logging across the Maintenance Dashboard.
Provides standardized logging patterns and error handling.
"""

import logging
import functools
from typing import Optional, Any, Callable
from django.conf import settings

# Get logger for this module
logger = logging.getLogger(__name__)


def log_function_call(func: Callable) -> Callable:
    """
    Decorator to log function entry and exit with parameters and return values.
    
    Usage:
        @log_function_call
        def my_function(param1, param2):
            return result
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        module_name = func.__module__
        
        # Log function entry
        logger.debug(f"Entering {module_name}.{func_name} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            # Log successful exit
            logger.debug(f"Exiting {module_name}.{func_name} successfully")
            return result
        except Exception as e:
            # Log error and re-raise
            logger.error(f"Error in {module_name}.{func_name}: {e}", exc_info=True)
            raise
    
    return wrapper


def log_error(error: Exception, context: str = "", user: Optional[Any] = None, 
              request: Optional[Any] = None, **kwargs) -> None:
    """
    Standardized error logging with context and additional information.
    
    Args:
        error: The exception that occurred
        context: Description of what was being attempted
        user: User object if available
        request: Request object if available
        **kwargs: Additional context information
    """
    error_msg = f"Error in {context}: {str(error)}"
    
    # Add user information if available
    if user:
        error_msg += f" | User: {getattr(user, 'username', 'Unknown')}"
    
    # Add request information if available
    if request:
        error_msg += f" | Path: {getattr(request, 'path', 'Unknown')}"
        error_msg += f" | Method: {getattr(request, 'method', 'Unknown')}"
        if hasattr(request, 'META') and 'REMOTE_ADDR' in request.META:
            error_msg += f" | IP: {request.META['REMOTE_ADDR']}"
    
    # Add additional context
    if kwargs:
        context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        error_msg += f" | Context: {context_str}"
    
    logger.error(error_msg, exc_info=True)


def log_security_event(event_type: str, description: str, user: Optional[Any] = None,
                       request: Optional[Any] = None, severity: str = "WARNING", **kwargs) -> None:
    """
    Log security-related events with standardized format.
    
    Args:
        event_type: Type of security event (e.g., 'login_failed', 'permission_denied')
        description: Description of the event
        user: User object if available
        request: Request object if available
        severity: Log level (WARNING, ERROR, CRITICAL)
        **kwargs: Additional security context
    """
    security_logger = logging.getLogger('django.security')
    
    security_msg = f"SECURITY EVENT: {event_type} | {description}"
    
    # Add user information
    if user:
        security_msg += f" | User: {getattr(user, 'username', 'Unknown')}"
        security_msg += f" | User ID: {getattr(user, 'id', 'Unknown')}"
    
    # Add request information
    if request:
        security_msg += f" | Path: {getattr(request, 'path', 'Unknown')}"
        security_msg += f" | Method: {getattr(request, 'method', 'Unknown')}"
        if hasattr(request, 'META') and 'REMOTE_ADDR' in request.META:
            security_msg += f" | IP: {request.META['REMOTE_ADDR']}"
        if hasattr(request, 'META') and 'HTTP_USER_AGENT' in request.META:
            security_msg += f" | User-Agent: {request.META['HTTP_USER_AGENT']}"
    
    # Add additional security context
    if kwargs:
        context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        security_msg += f" | Additional: {context_str}"
    
    # Log with appropriate level
    if severity.upper() == "CRITICAL":
        security_logger.critical(security_msg)
    elif severity.upper() == "ERROR":
        security_logger.error(security_msg)
    else:
        security_logger.warning(security_msg)


def log_performance_issue(operation: str, duration: float, threshold: float = 1.0,
                          request: Optional[Any] = None, **kwargs) -> None:
    """
    Log performance issues when operations exceed thresholds.
    
    Args:
        operation: Description of the operation
        duration: Time taken in seconds
        threshold: Threshold for considering it a performance issue
        request: Request object if available
        **kwargs: Additional performance context
    """
    if duration > threshold:
        perf_msg = f"PERFORMANCE ISSUE: {operation} took {duration:.2f}s (threshold: {threshold}s)"
        
        # Add request information
        if request:
            perf_msg += f" | Path: {getattr(request, 'path', 'Unknown')}"
            perf_msg += f" | Method: {getattr(request, 'method', 'Unknown')}"
        
        # Add additional context
        if kwargs:
            context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            perf_msg += f" | Context: {context_str}"
        
        logger.warning(perf_msg)


def log_database_operation(operation: str, model: str, success: bool, 
                          duration: Optional[float] = None, **kwargs) -> None:
    """
    Log database operations for monitoring and debugging.
    
    Args:
        operation: Type of database operation (SELECT, INSERT, UPDATE, DELETE)
        model: Model name being operated on
        success: Whether the operation was successful
        duration: Time taken for the operation
        **kwargs: Additional database context
    """
    db_logger = logging.getLogger('django.db.backends')
    
    if success:
        level = logging.DEBUG
        status = "SUCCESS"
    else:
        level = logging.ERROR
        status = "FAILED"
    
    db_msg = f"DB {operation} on {model}: {status}"
    
    if duration is not None:
        db_msg += f" | Duration: {duration:.3f}s"
    
    # Add additional context
    if kwargs:
        context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        db_msg += f" | Context: {context_str}"
    
    db_logger.log(level, db_msg)


def setup_logging_for_module(module_name: str) -> logging.Logger:
    """
    Get a properly configured logger for a specific module.
    
    Args:
        module_name: Name of the module (e.g., 'core.views', 'equipment.models')
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(module_name)


# Convenience functions for common logging patterns
def log_view_access(view_name: str, request: Any, user: Optional[Any] = None) -> None:
    """Log when a view is accessed."""
    logger.info(f"View accessed: {view_name} | User: {getattr(user, 'username', 'Anonymous')} | "
                f"Path: {getattr(request, 'path', 'Unknown')} | "
                f"Method: {getattr(request, 'method', 'Unknown')}")


def log_api_call(api_name: str, method: str, success: bool, duration: Optional[float] = None,
                 user: Optional[Any] = None, **kwargs) -> None:
    """Log API calls for monitoring."""
    status = "SUCCESS" if success else "FAILED"
    api_msg = f"API {method} {api_name}: {status}"
    
    if duration is not None:
        api_msg += f" | Duration: {duration:.3f}s"
    
    if user:
        api_msg += f" | User: {getattr(user, 'username', 'Unknown')}"
    
    if kwargs:
        context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        api_msg += f" | Context: {context_str}"
    
    if success:
        logger.info(api_msg)
    else:
        logger.error(api_msg)


def log_file_operation(operation: str, file_path: str, success: bool, 
                       file_size: Optional[int] = None, **kwargs) -> None:
    """Log file operations for audit purposes."""
    status = "SUCCESS" if success else "FAILED"
    file_msg = f"FILE {operation}: {file_path} | {status}"
    
    if file_size is not None:
        file_msg += f" | Size: {file_size} bytes"
    
    if kwargs:
        context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        file_msg += f" | Context: {context_str}"
    
    if success:
        logger.info(file_msg)
    else:
        logger.error(file_msg)
