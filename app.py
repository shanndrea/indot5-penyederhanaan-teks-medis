from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import pandas as pd
import re
import os
from model_loader import medical_text_simplifier
import logging
import traceback
import ftfy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def final_cleanup(sentence: str) -> str:
    cleaned_sentence = ftfy.fix_text(sentence)

    words = cleaned_sentence.split()
    if len(words) >= 7:
        for length in (4, 3, 2):
            end_phrase = " ".join(words[-length:])
            main_part = " ".join(words[:-length])
            if end_phrase in main_part:
                cleaned_sentence = main_part.strip()
                break
    
    cleaned_sentence = re.sub(r'\s+([.,?!])', r'\1', cleaned_sentence)
    
    cleaned_sentence = re.sub(r'\b(\w+)\s+\1\b', r'\1', cleaned_sentence, flags=re.IGNORECASE)

    if cleaned_sentence:
        cleaned_sentence = cleaned_sentence.lower().capitalize()

    return cleaned_sentence.strip()

class DictionaryPostProcessor:
    def __init__(self, dictionary_path="dictionary.csv"):
        self.dictionary = self.load_dictionary(dictionary_path)
    
    def load_dictionary(self, path):
        """Load dictionary from CSV with correct structure"""
        try:
            if not os.path.exists(path):
                logger.error(f"Dictionary file not found: {path}")
                return {}
                
            df = pd.read_csv(path)
            # Ensure correct columns are used
            if 'term' in df.columns and 'simplified' in df.columns:
                dictionary_dict = dict(zip(df['term'], df['simplified']))
                logger.info(f"Dictionary loaded successfully with {len(dictionary_dict)} entries")
                return dictionary_dict
            else:
                logger.error("Columns 'term' or 'simplified' not found in CSV")
                logger.error(f"Available columns: {df.columns.tolist()}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to load dictionary: {e}")
            logger.error(traceback.format_exc())
            return {}
    
    def post_process(self, text):
        """Apply dictionary replacement with case-insensitive matching"""
        if not self.dictionary:
            logger.warning("Dictionary is empty, skipping post-processing")
            return text
        
        result = text
        replacements_made = 0
        
        for term, replacement in self.dictionary.items():
            # Case-insensitive whole word replacement
            pattern = r'\b' + re.escape(term) + r'\b'
            original_result = result
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            if result != original_result:
                replacements_made += 1
        
        logger.debug(f"Dictionary replacements made: {replacements_made}")
        return result
    

# Initialize post-processor
post_processor = DictionaryPostProcessor()

@app.route('/')
def index():
    """Serve index.html from templates folder"""
    logger.info("Serving index.html")
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@app.route('/simplify', methods=['POST', 'OPTIONS'])
@app.route('/sederhanakan', methods=['POST', 'OPTIONS'])  # Keep Indonesian endpoint for compatibility
def simplify_text():
    """Endpoint for text simplification"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Log request details
        logger.info(f"Received request from {request.remote_addr}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        logger.info(f"Text to simplify: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        if not text:
            logger.error("Empty text received")
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        if len(text) > 2000:
            logger.error(f"Text too long: {len(text)} characters")
            return jsonify({'error': 'Text too long (maximum 2000 characters)'}), 400
        
        # Check if model is loaded
        if not medical_text_simplifier or not medical_text_simplifier.model_loaded:
            logger.error("Model not loaded when processing request")
            return jsonify({'error': 'Model not loaded. Please try again later.'}), 503
        
        logger.info("Starting model inference...")
        
        try:
           model_output = medical_text_simplifier.simplify_medical_text(
                text,
                repetition_penalty=1.5,  
                no_repeat_ngram_size=3,
                do_sample=True,  
                temperature=0.7,        
                top_k=50,                
                top_p=0.95,              
                num_beams=5,
                max_new_tokens=128
            )
           logger.info(f"Model output type: {type(model_output)}")
           logger.info(f"Model output: {model_output}")
           
        except Exception as model_error:
            logger.error(f"Model inference failed: {str(model_error)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'error': f'Model processing failed: {str(model_error)}',
                'status': 'error'
            }), 500
        
        # Step 2: Dictionary post-processing
        final_output = post_processor.post_process(model_output)
        logger.info(f"After post-processing: {final_output}")

        final_output = post_processor.post_process(model_output) 
        final_output = final_cleanup(final_output)
        
        # Step 3: Safety check for truncated information
        if len(final_output) < len(text) * 0.3:  # If more than 70% is lost
            logger.warning(f"Output significantly shorter than input. Input: {len(text)}, Output: {len(final_output)}")
            final_output += " [Information may be incomplete - medical consultation recommended]"
        
        logger.info("Simplification completed successfully")
        
        return jsonify({
            'original_text': text,
            'simplified_text': final_output,
            'status': 'success',
            'processing_steps': {
                'model_processing': True,
                'dictionary_processing': True
            }
        })
        
    except Exception as e:
        logger.error(f"Error in simplify endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f'System error occurred: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/batch-simplify', methods=['POST'])
def batch_simplify():
    """Endpoint for batch text simplification"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        texts = data.get('texts', [])
        
        if not texts:
            return jsonify({'error': 'Texts list cannot be empty'}), 400
        
        if len(texts) > 50:
            return jsonify({'error': 'Too many texts (maximum 50 per request)'}), 400
        
        # Validate each text
        for i, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                return jsonify({'error': f'Text at index {i} is invalid'}), 400
            if len(text) > 2000:
                return jsonify({'error': f'Text at index {i} exceeds 2000 characters'}), 400
        
        logger.info(f"Processing batch of {len(texts)} texts")
        
        # Check if model is loaded
        if not medical_text_simplifier or not medical_text_simplifier.model_loaded:
            return jsonify({'error': 'Model not loaded. Please try again later.'}), 503
        
        # Process all texts
        results = []
        for i, text in enumerate(texts):
            try:
                logger.info(f"Processing text {i+1}/{len(texts)}")
                model_output = medical_text_simplifier.simplify_medical_text(text)
                final_output = post_processor.post_process(model_output)
                
                # Safety check for truncated information
                if len(final_output) < len(text) * 0.3:
                    final_output += " [Information may be incomplete - medical consultation recommended]"
                
                results.append({
                    'original_text': text,
                    'simplified_text': final_output,
                    'status': 'success'
                })
            except Exception as e:
                logger.error(f"Error processing text {i+1}: {str(e)}")
                results.append({
                    'original_text': text,
                    'simplified_text': text,  # Fallback to original
                    'status': 'error',
                    'error': str(e)
                })
        
        logger.info(f"Batch processing completed: {len([r for r in results if r['status'] == 'success'])} successful, {len([r for r in results if r['status'] == 'error'])} failed")
        
        return jsonify({
            'results': results,
            'total_processed': len(results),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in batch simplify endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f'System error occurred: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/validate-text', methods=['POST'])
def validate_text():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text_input = data.get('text', '')
        
        if not text_input:
            return jsonify({'is_medical': False})

        medical_terms = set(post_processor.dictionary.keys())

        simplified_terms = set(post_processor.dictionary.values())

        all_medical_phrases = medical_terms.union(simplified_terms)
        
        is_medical = False
        for term in all_medical_phrases:
            pattern = r'\b' + re.escape(term) + r'\b'

            if re.search(pattern, text_input, re.IGNORECASE):
                is_medical = True
                logger.info(f"Validation success: Found term '{term}' in input.")
                break 

        logger.info(f"Validation result for text '{text_input[:50]}...': {is_medical}")
        return jsonify({'is_medical': is_medical})

    except Exception as e:
        logger.error(f"Error in validate-text endpoint: {str(e)}")
        logger.error(traceback.format_exc()) 
        return jsonify({'error': 'Server error during validation'}), 500

@app.route('/health')
def health_check():
    """Endpoint to check model and dictionary status"""
    try:
        test_text = "Patient has hypertension and anemia"
        
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

@app.route('/system-status')
def system_status():
    """Detailed system status endpoint"""
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
                'sederhanakan': 'POST /sederhanakan (legacy)',
                'batch_simplify': 'POST /batch-simplify',
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

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check system status
    dict_count = len(post_processor.dictionary)
    model_loaded = medical_text_simplifier and medical_text_simplifier.model_loaded
    
    logger.info("=" * 60)
    logger.info("MEDICAL TEXT SIMPLIFICATION API STARTING UP")
    logger.info("=" * 60)
    logger.info(f"Model Status: {'LOADED' if model_loaded else 'FAILED'}")
    logger.info(f"Dictionary: {dict_count} entries")
    
    if model_loaded:
        model_status = medical_text_simplifier.get_model_status()
        logger.info(f"Model Repository: {model_status.get('model_repo', 'Unknown')}")
        logger.info(f"Model Device: {model_status.get('device', 'Unknown')}")
    
    logger.info(f"Available Endpoints:")
    logger.info(f"  POST /simplify (and /sederhanakan)")
    logger.info(f"  POST /batch-simplify")
    logger.info(f"  GET  /health")
    logger.info(f"  GET  /system-status")
    logger.info("=" * 60)
    logger.info(f"Starting server on http://0.0.0.0:5000")
    logger.info("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        raise