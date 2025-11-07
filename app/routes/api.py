from flask import Blueprint, request, jsonify
import logging
import traceback
import re
from app.utils.error_handler import create_success_response, ValidationError, MedicalTermError
from app.utils.post_processor import post_processor, get_simplification_mapping, detect_recognized_terms
from app.utils.text_cleaner import final_cleanup
from app.models.text_simplifier import medical_text_simplifier
from app.config import (
    MAX_TEXT_LENGTH, SAFETY_CHECK_RATIO,MODEL_REPETITION_PENALTY, MODEL_NO_REPEAT_NGRAM_SIZE, 
    MODEL_TEMPERATURE, MODEL_TOP_K, MODEL_TOP_P, MODEL_NUM_BEAMS, MODEL_MAX_NEW_TOKENS
)

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/simplify', methods=['POST'])
def simplify_text():
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
        
        if len(text) > MAX_TEXT_LENGTH:
            logger.error(f"Text too long: {len(text)} characters")
            return jsonify({'error': 'Text too long (maximum {MAX_TEXT_LENGTH} characters)'}), 400
        
        if not medical_text_simplifier or not medical_text_simplifier.model_loaded:
            logger.error("Model not loaded when processing request")
            return jsonify({'error': 'Model not loaded. Please try again later.'}), 503

        recognized_terms = detect_recognized_terms(text, post_processor.dictionary)

        if not recognized_terms:
            return jsonify({
                'status': 'blocked',
                'message': 'Tidak ada istilah medis yang dikenali. Proses dihentikan.',
                'recognized_terms': []
            }), 400
        
        logger.info("Starting model inference...")
        
        try:
           model_output = medical_text_simplifier.simplify_medical_text(
                text,
                repetition_penalty=MODEL_REPETITION_PENALTY,  
                no_repeat_ngram_size=MODEL_NO_REPEAT_NGRAM_SIZE,
                do_sample=True,  
                temperature=MODEL_TEMPERATURE,        
                top_k=MODEL_TOP_K,                
                top_p=MODEL_TOP_P,              
                num_beams=MODEL_NUM_BEAMS,
                max_new_tokens=MODEL_MAX_NEW_TOKENS
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
        
        final_output = post_processor.post_process(model_output)
        logger.info(f"After post-processing: {final_output}")
        final_output = final_cleanup(final_output)

        if len(final_output) < len(text) * SAFETY_CHECK_RATIO:  
            logger.warning(f"Output significantly shorter than input. Input: {len(text)}, Output: {len(final_output)}")
            final_output += " [Information may be incomplete - medical consultation recommended]"
        
        # Step 4: Dapatkan mapping penyederhanaan
        simplification_map = get_simplification_mapping(text, final_output, post_processor.dictionary)
        
        logger.info("Simplification completed successfully")

        # Response berdasarkan ada/tidak simplification mapping
        if simplification_map:
            return jsonify({
                'original_text': text,
                'model_text': model_output,
                'simplified_text': final_output,
                'status': 'success',
                'simplification_map': simplification_map,
                'processing_steps': {
                    'model_processing': True,
                    'dictionary_processing': True
                }
            })
        else:
            # Fallback jika tidak ada mapping terdeteksi
            return jsonify({
                'original_text': text,
                'simplified_text': final_output,
                'status': 'success',
                'simplification_map': {},
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
    pass

@api_bp.route('/validate-text', methods=['POST']) 
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
    pass