# config.py

MAX_TEXT_LENGTH = 2000
MIN_TEXT_LENGTH = 30 
SAFETY_CHECK_RATIO = 0.3 

# Model Configuration
MODEL_REPO = "shanndrea/indot5-small-medical-simplifier"
MODEL_MAX_LENGTH = 256
MODEL_MIN_LENGTH = 20
MODEL_NUM_BEAMS = 5
MODEL_REPETITION_PENALTY = 1.5
MODEL_NO_REPEAT_NGRAM_SIZE = 3
MODEL_TEMPERATURE = 0.7
MODEL_TOP_K = 50
MODEL_TOP_P = 0.95
MODEL_MAX_NEW_TOKENS = 128

# Server Configuration
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000
SERVER_DEBUG = False

# Dictionary Configuration
DICTIONARY_PATH = "data/dictionary.csv"

# Health Check
HEALTH_CHECK_TEXT = "Pasien memiliki penyakit hipertensi dan anemia"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'