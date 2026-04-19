import logging
import sys
from src.constant.constant import DATE_FORMAT, LOG_FORMAT

def setup_logger(
    name: str,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Create and configure a logger with standardized formatting.
    
    This function sets up a logger with consistent formatting and output
    handlers across the entire application. Multiple calls with the same
    name return the same logger instance.
    
    Args:
        name: Logger name (typically __name__).
        level: Logging level (default: INFO).
    
    Returns:
        logging.Logger: Configured logger instance.
    
    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Application started")
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(level)
    return logger


logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)]
)