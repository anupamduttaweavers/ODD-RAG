"""Logging configuration for the application."""

import logging
import sys

from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    
    # Create logger
    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # Log format
    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # Prevent logs from propagating to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = "app") -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


# Initialize the main logger
logger = setup_logging()
