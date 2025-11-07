from flask import jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base application error class"""
    def __init__(self, message, status_code=400, error_code=None, details=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details

class ValidationError(AppError):
    """Input validation errors"""
    def __init__(self, message, details=None):
        super().__init__(message, 400, 'VALIDATION_ERROR', details)

class ModelError(AppError):
    """Model-related errors"""
    def __init__(self, message, details=None):
        super().__init__(message, 503, 'MODEL_ERROR', details)

class MedicalTermError(AppError):
    """Medical term detection errors"""
    def __init__(self, message, recognized_terms=None):
        super().__init__(message, 400, 'NO_MEDICAL_TERMS', {'recognized_terms': recognized_terms or []})

def create_error_response(message, status_code=400, error_code=None, details=None):
    """Standard error response format"""
    error_payload = {
        'status': 'error',
        'error': {
            'code': error_code or 'UNKNOWN_ERROR',
            'message': message,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
    }
    return jsonify(error_payload), status_code

def create_success_response(data=None, message=None, status_code=200):
    """Standard success response format"""
    response = {
        'status': 'success',
        'data': data,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    return jsonify(response), status_code

def handle_app_error(error):
    """Global error handler for AppError"""
    logger.warning(f"AppError: {error.message} (code: {error.error_code})")
    return create_error_response(
        message=error.message,
        status_code=error.status_code,
        error_code=error.error_code,
        details=error.details
    )

def handle_generic_error(error):
    """Global error handler for generic exceptions"""
    from flask import current_app
    logger.error(f"Unexpected error: {str(error)}")
    return create_error_response(
        message="Internal server error",
        status_code=500,
        error_code="INTERNAL_ERROR",
        details=str(error) if current_app.debug else None
    )

def handle_404_error(error):
    """Handle 404 errors"""
    return create_error_response(
        message="Endpoint not found",
        status_code=404,
        error_code="NOT_FOUND"
    )