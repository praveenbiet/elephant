import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any

from src.common.config import get_settings

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {}
        
        # Standard log record attributes
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["name"] = record.name
        log_record["message"] = record.getMessage()
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Add extra attributes passed via the extra parameter
        if hasattr(record, "props"):
            log_record["props"] = record.props
        
        # Add standard attributes useful for debugging
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno
        
        return json.dumps(log_record)

def setup_logging() -> None:
    """
    Configure logging settings for the application.
    
    Uses JSON formatting in production and standard formatting in development.
    """
    settings = get_settings()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Clear existing handlers
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Use different formatters based on environment
    if settings.DEBUG:
        # Pretty format for development
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # JSON format for production
        formatter = JsonFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Suppress logs from noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Log the application startup
    logging.info(f"Logging set up with level: {settings.LOG_LEVEL}")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name for the logger, typically __name__ from the calling module
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
