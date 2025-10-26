import torch
import os
import sys
from transformers import T5Tokenizer, T5ForConditionalGeneration
import logging
import time
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('medical_simplifier.log')
    ]
)
logger = logging.getLogger(__name__)

class MedicalTextSimplifier:
    
    def __init__(self, model_repo: str = "shanndrea/indoT5-small-penyederhanaan-teks-medis"):
        # Inisialisasi komponen model
        self.model_repo = model_repo
        self.tokenizer = None
        self.model = None
        self.device = None
        self.model_loaded = False
        self.load_start_time = None
        self.load_end_time = None
        
        # Konfigurasi generasi teks
        self.generation_config = {
            'max_length': 256,
            'min_length': 20,
            'num_beams': 6,
            'length_penalty': 1.5,
            'no_repeat_ngram_size': 3,
            'early_stopping': True,
            'temperature': 0.8,
            'do_sample': False
        }
    
    def _detect_compute_device(self) -> torch.device:
        # Deteksi device yang tersedia (GPU -> MPS -> CPU)
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU detected: {gpu_name} (count: {gpu_count})")
            return torch.device("cuda")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Apple Silicon MPS detected")
            return torch.device("mps")
        else:
            logger.info("Using CPU for computation")
            return torch.device("cpu")
    
    def _verify_model_components(self) -> bool:
        # Verifikasi semua komponen model terload dengan benar
        checks_passed = True
        
        if self.tokenizer is None:
            logger.error("Tokenizer not initialized")
            checks_passed = False
        
        if self.model is None:
            logger.error("Model not initialized")
            checks_passed = False
            
        if self.device is None:
            logger.error("Device not detected")
            checks_passed = False
            
        return checks_passed
    
    def _get_model_size_info(self) -> Dict[str, Any]:
        # Ambil informasi ukuran dan parameter model
        if self.model is None:
            return {}
            
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        
        return {
            'total_parameters': f"{total_params:,}",
            'trainable_parameters': f"{trainable_params:,}",
            'model_layers': len(list(self.model.modules())),
            'vocab_size': getattr(self.tokenizer, 'vocab_size', 'Unknown')
        }
    
    def load_model(self) -> bool:
        # Load model dan tokenizer dari Hugging Face Hub
        self.load_start_time = time.time()
        
        try:
            logger.info(f"Starting model loading process from: {self.model_repo}")
            
            # Deteksi hardware
            self.device = self._detect_compute_device()
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = T5Tokenizer.from_pretrained(
                self.model_repo,
                local_files_only=False,
                use_fast=True
            )
            
            # Load model
            logger.info("Loading model...")
            self.model = T5ForConditionalGeneration.from_pretrained(
                self.model_repo,
                local_files_only=False,
                torch_dtype=torch.float32
            )
            
            # Pindahkan model ke device
            logger.info(f"Moving model to {self.device}...")
            self.model = self.model.to(self.device)
            
            # Set model ke mode evaluasi
            self.model.eval()
            
            # Verifikasi komponen
            logger.info("Verifying model components...")
            if not self._verify_model_components():
                raise RuntimeError("Model component verification failed")
            
            # Dapatkan info model
            model_info = self._get_model_size_info()
            
            self.load_end_time = time.time()
            load_duration = self.load_end_time - self.load_start_time
            
            self.model_loaded = True
            
            logger.info("=" * 60)
            logger.info("MODEL LOADING SUCCESSFUL")
            logger.info(f"Repository: {self.model_repo}")
            logger.info(f"Device: {self.device}")
            logger.info(f"Loading duration: {load_duration:.2f} seconds")
            logger.info(f"Total parameters: {model_info.get('total_parameters', 'Unknown')}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as error:
            self.model_loaded = False
            logger.error(f"MODEL LOADING FAILED: {str(error)}")
            
            # Cleanup resources pada error
            self.tokenizer = None
            self.model = None
            
            return False
    
    def preprocess_input_text(self, text: str) -> str:
        # Preprocess input text sebelum diproses model
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be non-empty string")
        
        # Bersihkan text
        cleaned_text = text.strip()
        
        # Log karakteristik input
        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)
        
        logger.debug(f"Input text: {word_count} words, {char_count} characters")
        
        return cleaned_text
    
    def create_prompt(self, text: str) -> str:
        # Buat prompt optimal untuk model T5
        base_prompt = f"sederhanakan: {text}"
        return base_prompt
    
    def simplify_medical_text(self, complex_text: str, **generation_kwargs) -> str:
        # Sederhanakan teks medis kompleks
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Preprocess input
        processed_text = self.preprocess_input_text(complex_text)
        
        # Buat prompt
        prompt = self.create_prompt(processed_text)
        
        try:
            # Tokenize input
            input_tokens = self.tokenizer(
                prompt,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            # Siapkan konfigurasi generasi
            gen_config = self.generation_config.copy()
            gen_config.update(generation_kwargs)
            
            # Generate output
            with torch.no_grad():
                start_time = time.time()
            
            output_tokens = self.model.generate(
                **input_tokens,
                **gen_config
            )

            inference_time = time.time() - start_time

            try:
                # Coba decode sebagai tensor biasa
                simplified_text = self.tokenizer.decode(
                    output_tokens[0], 
                    skip_special_tokens=True
                )
            except (TypeError, AttributeError) as decode_error:
                logger.warning(f"Primary decode failed, trying alternative: {decode_error}")
            
            # Fallback 1: Convert to numpy array dulu
            if hasattr(output_tokens[0], 'cpu'):
                token_array = output_tokens[0].cpu().numpy()
                simplified_text = self.tokenizer.decode(
                    token_array, 
                    skip_special_tokens=True
                )
            # Fallback 2: Convert to list
            elif hasattr(output_tokens[0], 'tolist'):
                token_list = output_tokens[0].tolist()
                simplified_text = self.tokenizer.decode(
                    token_list, 
                    skip_special_tokens=True
                )
            else:
                # Final fallback: return original text
                logger.error(f"All decode attempts failed. Output type: {type(output_tokens[0])}")
                return processed_text
                
            logger.debug(f"Inference completed: {inference_time:.3f} seconds")
            return simplified_text.strip()
        
        except Exception as error:
            logger.error(f"Error during inference: {str(error)}")
            logger.error(f"Output tokens type: {type(output_tokens[0]) if 'output_tokens' in locals() else 'N/A'}")
            return processed_text

    def batch_simplify(self, texts: list, batch_size: int = 4) -> list:
        # Sederhanakan multiple texts sekaligus (batch processing)
        if not self.model_loaded:
            raise RuntimeError("Model not loaded")
        
        if not texts:
            return []
        
        simplified_texts = []
        total_texts = len(texts)
        
        logger.info(f"Processing {total_texts} texts in batches ({batch_size}/batch)")
        
        for i in range(0, total_texts, batch_size):
            batch = texts[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, total_texts)
            
            logger.info(f"Processing batch {batch_start}-{batch_end} of {total_texts}")
            
            for text in batch:
                try:
                    simplified = self.simplify_medical_text(text)
                    simplified_texts.append(simplified)
                except Exception as error:
                    logger.error(f"Failed to process text in batch: {str(error)}")
                    simplified_texts.append(text)
        
        return simplified_texts
    
    def get_model_status(self) -> Dict[str, Any]:
        # Dapatkan informasi status model saat ini
        return {
            'model_loaded': self.model_loaded,
            'device': str(self.device) if self.device else None,
            'model_repo': self.model_repo,
            'tokenizer_loaded': self.tokenizer is not None,
            'model_components_loaded': self.model is not None,
            'generation_config': self.generation_config
        }


# Global instance dengan error handling
try:
    medical_text_simplifier = MedicalTextSimplifier()
    model_load_success = medical_text_simplifier.load_model()
    
    if not model_load_success:
        logger.warning("Failed to load model. Instance created but cannot be used.")
        
except Exception as critical_error:
    logger.critical(f"Failed to create global instance: {str(critical_error)}")
    medical_text_simplifier = None