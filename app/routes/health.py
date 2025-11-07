from flask import Blueprint, jsonify
import os
import logging
from app.models.text_simplifier import medical_text_simplifier
from app.utils.post_processor import post_processor
from app.config import HEALTH_CHECK_TEXT

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

@health_bp.route('/health')
def health_check():
    try:
        test_text = HEALTH_CHECK_TEXT
        
        # Check model status
        model_loaded = medical_text_simplifier and medical_text_simplifier.model_loaded
        
        # Test model if loaded
        model_output = None
        final_output = None
        test_successful = False
        
        if model_loaded:
            try:
                model_output = medical_text_simplifier.simplify_medical_text(test_text)
                safe_model_output = str(model_output)
                final_output = post_processor.post_process(safe_model_output)
                test_successful = True
                logger.info("Health check: Model test successful")
            except Exception as e:
                logger.error(f"Health check: Model test failed: {str(e)}")
                test_successful = False
        
        status = 'healthy' if (model_loaded and test_successful) else 'unhealthy'
        
        return jsonify({
            'status': status,
            'model_loaded': model_loaded,
            'model_test_successful': test_successful,
            'dictionary_loaded': len(post_processor.dictionary) > 0,
            'dictionary_count': len(post_processor.dictionary),
            'test_input': test_text,
            'model_output': model_output,
            'final_output': final_output,
            'system_info': {
                'max_text_length': 2000,
                'max_batch_size': 50,
                'supports_batch_processing': True
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'model_loaded': False,
            'error': str(e)
        }), 500
    pass

@health_bp.route('/system-status')
def system_status():
    try:
        model_status = medical_text_simplifier.get_model_status() if medical_text_simplifier else {}
        
        return jsonify({
            'application': 'Medical Text Simplification API',
            'version': '1.0.0',
            'model': {
                'loaded': medical_text_simplifier and medical_text_simplifier.model_loaded,
                'repository': model_status.get('model_repo', 'Unknown'),
                'device': model_status.get('device', 'Unknown'),
                'vocab_size': model_status.get('vocab_size', 'Unknown')
            },
            'dictionary': {
                'loaded': len(post_processor.dictionary) > 0,
                'entry_count': len(post_processor.dictionary)
            },
            'system': {
                'python_version': os.sys.version,
                'working_directory': os.getcwd()
            },
            'endpoints': {
                'simplify': 'POST /simplify',
                'health': 'GET /health',
                'system_status': 'GET /system-status'
            }
        })
    except Exception as e:
        logger.error(f"System status check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

    pass