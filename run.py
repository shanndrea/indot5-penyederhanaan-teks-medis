import os
import sys
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.config import SERVER_HOST, SERVER_PORT, SERVER_DEBUG, LOG_LEVEL

def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/app.log')
        ]
    )
    return logging.getLogger(__name__)

def check_system_status(logger):
    """Check and display system status"""
    try:
        from app.utils.post_processor import post_processor
        from app.models.text_simplifier import medical_text_simplifier
        
        dict_count = len(post_processor.dictionary)
        model_loaded = medical_text_simplifier and medical_text_simplifier.model_loaded
        
        logger.info("SYSTEM STATUS CHECK")
        logger.info("========================================================================")
        logger.info("Model Status: %s", "LOADED" if model_loaded else "FAILED")
        logger.info("Dictionary: %d entries", dict_count)
        
        if model_loaded:
            model_status = medical_text_simplifier.get_model_status()
            logger.info("Model Repository: %s", model_status.get('model_repo', 'Unknown'))
            logger.info("Model Device: %s", model_status.get('device', 'Unknown'))
        
        logger.info("Server: %s:%s", SERVER_HOST, SERVER_PORT)
        logger.info("Debug Mode: %s", "ON" if SERVER_DEBUG else "OFF")
        logger.info("========================================================================")
        
        return model_loaded, dict_count
        
    except Exception as e:
        logger.error("Error checking system status: %s", str(e))
        return False, 0

def main():
    """Main application entry point"""
    try:
        # Setup logging
        logger = setup_logging()
        
        # Check requirements
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        # Create Flask application
        app = create_app()
        
        # Print startup information
        logger.info("========================================================================")
        logger.info("                   MEDICAL TEXT SIMPLIFICATION API                     ")
        logger.info("                         STARTING SERVER...                            ")
        logger.info("========================================================================")
        
        # Check system status
        model_loaded, dict_count = check_system_status(logger)
        
        # Print available endpoints
        logger.info("AVAILABLE ENDPOINTS:")
        logger.info("  POST /simplify           - Simplify medical text")
        logger.info("  POST /validate-text      - Validate if text contains medical terms") 
        logger.info("  GET  /health             - Health check")
        logger.info("  GET  /system-status      - Detailed system status")
        logger.info("========================================================================")
        
        # Start the server
        logger.info("Starting server on http://%s:%s", SERVER_HOST, SERVER_PORT)
        logger.info("Start time: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        logger.info("========================================================================")
        
        app.run(
            host=SERVER_HOST,
            port=SERVER_PORT,
            debug=SERVER_DEBUG,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
        
    except Exception as e:
        logger.critical("Failed to start server: %s", str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()