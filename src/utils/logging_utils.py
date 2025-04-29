"""
Centralized logging utility for ClaimVision.

This module provides standardized logging configuration that adapts based on the environment.
- INFO+ logs for non-production environments
- WARN+ logs for production environments
"""
import os
import logging
import json
from enum import Enum
from typing import Any, Dict

class LogLevel(Enum):
    """Enum for log levels to use with log_structured function."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

def configure_logging():
    """
    Configure logging based on environment variables.
    
    In production, only WARNING and above logs are shown.
    In non-production environments, INFO and above logs are shown.
    
    Returns:
        logging.Logger: Configured logger
    """
    # Get environment from Lambda environment variables
    environment = os.environ.get("ENVIRONMENT", "dev").lower()
    
    # Set log level based on environment
    if environment == "prod":
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
        
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return logging.getLogger()

def get_logger(name):
    """
    Get a logger with the specified name, properly configured based on environment.
    
    Args:
        name (str): Name for the logger, typically __name__
        
    Returns:
        logging.Logger: Configured logger
    """
    # Get environment from Lambda environment variables
    environment = os.environ.get("ENVIRONMENT", "dev").lower()
    
    # Set log level based on environment
    if environment == "prod":
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    # Get logger with specified name
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Only add handler if not already added to avoid duplicate logs
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    return logger

def log_structured(logger: logging.Logger, level: LogLevel, message: str, **kwargs: Any) -> None:
    """
    Log a structured message with additional context data.
    
    In development environments, this will log the full structured data.
    In production, it will only log the message to reduce verbosity.
    
    Args:
        logger (logging.Logger): The logger to use
        level (LogLevel): Log level enum value
        message (str): The log message
        **kwargs: Additional context data to include in the structured log
    """
    # Get environment from Lambda environment variables
    environment = os.environ.get("ENVIRONMENT", "dev").lower()
    
    # Create structured log data
    log_data: Dict[str, Any] = {
        "message": message,
        **kwargs
    }
    
    # Convert log level enum to string if it's an enum
    if isinstance(level, LogLevel):
        level_str = level.value
    else:
        level_str = str(level).lower()
        # Warn about incorrect usage in development
        if environment != "prod":
            logger.warning(f"log_structured called with non-enum level: {level}. Please use LogLevel enum.")
    
    # Get the logging method
    log_method = getattr(logger, level_str)
    
    if environment != "prod":
        # In non-production, log the full structured data
        try:
            structured_message = f"{message} | Context: {json.dumps(log_data, default=str)}"
            log_method(structured_message)
        except Exception as e:
            logger.warning(f"Failed to serialize log data: {str(e)}")
            log_method(message)
    else:
        # In production, just log the message to reduce verbosity
        log_method(message)
