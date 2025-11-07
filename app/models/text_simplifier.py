# app/models/text_simplifier.py
import torch
import os
import sys
import time
import logging
from typing import Dict, Any, Optional
from transformers import T5Tokenizer, T5ForConditionalGeneration
from app.config import (
    MODEL_REPO, MODEL_MAX_LENGTH, MODEL_MIN_LENGTH, MODEL_NUM_BEAMS,
    MODEL_REPETITION_PENALTY, MODEL_NO_REPEAT_NGRAM_SIZE,
    MODEL_TEMPERATURE, MODEL_TOP_K, MODEL_TOP_P, MODEL_MAX_NEW_TOKENS
)

logger = logging.getLogger(__name__)

class MedicalTextSimplifier:
    
    def __init__(self, model_repo: str = MODEL_REPO):
        self.model_repo = model_repo
        self.tokenizer = None
        self.model = None
        self.device = None
        self.model_loaded = False
        
        self.generation_config = {
            'max_length': MODEL_MAX_LENGTH,
            'min_length': MODEL_MIN_LENGTH,
            'num_beams': MODEL_NUM_BEAMS,
            'length_penalty': 1.5,
            'no_repeat_ngram_size': MODEL_NO_REPEAT_NGRAM_SIZE,
            'early_stopping': True,
            'temperature': MODEL_TEMPERATURE,
            'do_sample': False
        }
    
    def _detect_compute_device(self) -> torch.device:
        try:
            if torch.cuda.is_available():
                logger.info("Using CUDA (GPU) for computation")
                return torch.device("cuda")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                logger.info("Using MPS (Apple Silicon) for computation")
                return torch.device("mps")
            else:
                logger.info("Using CPU for computation")
                return torch.device("cpu")
        except Exception as e:
            logger.warning(f"Error detecting device, using CPU: {e}")
            return torch.device("cpu")
    
    def load_model(self) -> bool:
        try:
            logger.info(f"Starting model loading process from: {self.model_repo}")
            
            self.device = self._detect_compute_device()
            
            logger.info("Loading tokenizer...")
            self.tokenizer = T5Tokenizer.from_pretrained(
                self.model_repo,
                local_files_only=False
            )
            
            logger.info("Loading model...")
            self.model = T5ForConditionalGeneration.from_pretrained(
                self.model_repo,
                local_files_only=False,
                torch_dtype=torch.float32
            )
            
            logger.info(f"Moving model to {self.device}...")
            self.model = self.model.to(self.device)
            
            self.model.eval()
            self.model_loaded = True
            
            logger.info("Model loaded successfully")
            return True
            
        except Exception as error:
            self.model_loaded = False
            logger.error(f"Model loading failed: {str(error)}")
            # Clean up on failure
            self.tokenizer = None
            self.model = None
            return False
    
    def simplify_medical_text(self, complex_text: str, **generation_kwargs) -> str:
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            processed_text = complex_text.strip()
            prompt = f"sederhanakan: {processed_text}"
            
            input_tokens = self.tokenizer(
                prompt,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            gen_config = self.generation_config.copy()
            gen_config.update(generation_kwargs)
            
            with torch.no_grad():
                output_tokens = self.model.generate(**input_tokens, **gen_config)

            simplified_text = self.tokenizer.decode(output_tokens[0], skip_special_tokens=True)
            
            return simplified_text.strip()
        
        except Exception as error:
            logger.error(f"Error during text simplification: {str(error)}")
            # Return original text as fallback
            return complex_text

    def get_model_status(self) -> Dict[str, Any]:
        return {
            'model_loaded': self.model_loaded,
            'device': str(self.device) if self.device else None,
            'model_repo': self.model_repo,
            'tokenizer_loaded': self.tokenizer is not None,
            'model_components_loaded': self.model is not None
        }


medical_text_simplifier = None

try:
    medical_text_simplifier = MedicalTextSimplifier()
    logger.info("MedicalTextSimplifier instance created successfully")
    
    # Try to load model but don't crash if it fails
    model_load_success = medical_text_simplifier.load_model()
    if not model_load_success:
        logger.warning("Model loading failed, but instance created. Some features may not work.")
        
except Exception as critical_error:
    logger.error(f"Failed to create MedicalTextSimplifier instance: {str(critical_error)}")
    medical_text_simplifier = None