# app/__init__.py
from flask import Flask
from flask_cors import CORS

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)

    from app.routes.api import api_bp
    from app.routes.health import health_bp
    from app.routes.pages import pages_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(pages_bp)
    
    
    # Register error handlers
    from app.utils.error_handler import handle_app_error, handle_generic_error, AppError
    app.register_error_handler(AppError, handle_app_error)
    app.register_error_handler(Exception, handle_generic_error)
    
    return app