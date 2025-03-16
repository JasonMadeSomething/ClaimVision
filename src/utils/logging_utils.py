"""
Centralized logging utility for ClaimVision.

This module provides standardized logging configuration that adapts based on the environment.
- INFO+ logs for non-production environments
- WARN+ logs for production environments
"""
import os
import logging

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
