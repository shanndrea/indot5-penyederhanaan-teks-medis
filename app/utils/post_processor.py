import pandas as pd
import re
import os
import traceback
import logging
from app.config import DICTIONARY_PATH

logger = logging.getLogger(__name__)

class DictionaryPostProcessor:
    def __init__(self, dictionary_path=DICTIONARY_PATH):
        self.dictionary = self.load_dictionary(dictionary_path)
    
    def load_dictionary(self, path):
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
        if not self.dictionary:
            logger.warning("Dictionary is empty, skipping post-processing")
            return text
        
        result = text
        replacements_made = 0
        
        for term, replacement in self.dictionary.items():
            pattern = r'\b' + re.escape(term) + r'\b'
            model_result = result
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            if result != model_result:
                replacements_made += 1
        
        logger.debug(f"Dictionary replacements made: {replacements_made}")
        return result
    
    def __init__(self, dictionary_path=DICTIONARY_PATH):
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
            model_result = result
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            if result != model_result:
                replacements_made += 1
        
        logger.debug(f"Dictionary replacements made: {replacements_made}")
        return result

def get_simplification_mapping(text, simplified_text, dictionary):
    """Get mapping of original terms to simplified terms"""
    simplification_map = {}
    
    for term, replacement in dictionary.items():
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            replacement_pattern = r'\b' + re.escape(replacement) + r'\b'
            if re.search(replacement_pattern, simplified_text, re.IGNORECASE):
                simplification_map[term] = replacement
            elif not re.search(pattern, simplified_text, re.IGNORECASE):
                simplification_map[term] = replacement
    
    return simplification_map

def detect_recognized_terms(text, dictionary):
    """Detect recognized medical terms in text"""
    recognized = []
    for term in dictionary.keys():
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            recognized.append(term)
    return recognized

# Global instance
post_processor = DictionaryPostProcessor()