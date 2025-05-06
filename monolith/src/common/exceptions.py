from typing import Dict, Any, Optional, List, Type, Union
import traceback

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from src.common.logger import get_logger

logger = get_logger(__name__)

# Custom exception classes
class ApplicationError(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.code = code or "application_error"
        self.details = details
        super().__init__(self.message)

class NotFoundError(ApplicationError):
    """Resource not found error."""
    
    def __init__(
        self, 
        message: str = "Resource not found",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code=code or "not_found",
            details=details
        )

class ValidationError(ApplicationError):
    """Validation error on input data."""
    
    def __init__(
        self, 
        message: str = "Validation error",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code or "validation_error",
            details=details
        )

class AuthenticationError(ApplicationError):
    """Authentication error."""
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=code or "authentication_error",
            details=details
        )

class AuthorizationError(ApplicationError):
    """Authorization error (insufficient permissions)."""
    
    def __init__(
        self, 
        message: str = "Not authorized to perform this action",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code=code or "authorization_error",
            details=details
        )

class ConflictError(ApplicationError):
    """Conflict error (duplicate data)."""
    
    def __init__(
        self, 
        message: str = "Resource already exists",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code=code or "conflict_error",
            details=details
        )

class DependencyError(ApplicationError):
    """External dependency error."""
    
    def __init__(
        self, 
        message: str = "External service unavailable",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=code or "dependency_error",
            details=details
        )

# Exception handlers
def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request, exc: ApplicationError
    ) -> JSONResponse:
        """Handle all application errors."""
        # Log the error, exclude stack trace for 4xx errors
        log_message = f"Application error: {exc.message}"
        log_data = {
            "status_code": exc.status_code,
            "error_code": exc.code,
            "path": request.url.path,
            "method": request.method,
        }
        
        if exc.details:
            log_data["details"] = exc.details
            
        if exc.status_code >= 500:
            logger.error(log_message, extra={"props": log_data}, exc_info=True)
        else:
            logger.warning(log_message, extra={"props": log_data})
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details or {}
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle pydantic validation errors from request body/params."""
        errors = []
        for error in exc.errors():
            error_data = {
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", "")
            }
            errors.append(error_data)
        
        logger.warning(
            "Request validation error",
            extra={
                "props": {
                    "path": request.url.path,
                    "method": request.method,
                    "errors": errors
                }
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request data validation error",
                    "details": {
                        "errors": errors
                    }
                }
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle SQLAlchemy errors."""
        error_message = str(exc)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "database_error"
        
        # Handle integrity errors specially
        if isinstance(exc, IntegrityError):
            status_code = status.HTTP_409_CONFLICT
            error_code = "data_integrity_error"
            
            # Try to extract specific constraint violation
            error_details = {}
            if "unique constraint" in error_message.lower():
                error_code = "unique_constraint_violation"
                # Try to extract the constraint name
                # This is PostgreSQL specific
                if "Key" in error_message and "already exists" in error_message:
                    error_details["constraint"] = "unique"
            elif "foreign key constraint" in error_message.lower():
                error_code = "foreign_key_constraint_violation"
                error_details["constraint"] = "foreign_key"
            
        logger.error(
            f"Database error: {error_message}",
            extra={
                "props": {
                    "path": request.url.path,
                    "method": request.method,
                }
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": "Database operation failed",
                    "details": {
                        "error": error_message[:200]  # Limit the error message length
                    }
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all unhandled exceptions."""
        error_message = str(exc)
        
        logger.error(
            f"Unhandled exception: {error_message}",
            extra={
                "props": {
                    "path": request.url.path,
                    "method": request.method,
                    "traceback": traceback.format_exc()
                }
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "details": {}
                }
            }
        )
