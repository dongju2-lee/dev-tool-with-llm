"""
Logging configuration utility for the GitHub Issue Assistant Bot.
"""
import logging
import os
import sys

def setup_logger(name, level=None):
    """
    Set up a logger with specified name and level.
    
    Args:
        name (str): The name for the logger.
        level (str, optional): The logging level. Defaults to None which will use INFO.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    # Convert string level to logging level constant
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Create console handler if not already added
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger 