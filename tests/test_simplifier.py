import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import torch
from app.models.text_simplifier import MedicalTextSimplifier
from app.utils.post_processor import DictionaryPostProcessor, get_simplification_mapping, detect_recognized_terms
from app.utils.text_cleaner import final_cleanup

class TestMedicalTextSimplifier:
    """Test cases for MedicalTextSimplifier class"""
    
    @pytest.fixture
    def simplifier(self):
        return MedicalTextSimplifier(model_repo="test/model")
    
    def test_init(self, simplifier):
        assert simplifier.model_repo == "test/model"
        assert simplifier.model_loaded == False
        assert simplifier.tokenizer is None
        assert simplifier.model is None
    
    @patch('app.models.text_simplifier.T5Tokenizer')
    @patch('app.models.text_simplifier.T5ForConditionalGeneration')
    @patch('app.models.text_simplifier.torch')
    def test_load_model_success(self, mock_torch, mock_model_class, mock_tokenizer_class, simplifier):
        mock_torch.cuda.is_available.return_value = False
        mock_torch.device.return_value = 'cpu'
        
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        
        mock_model = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        result = simplifier.load_model()
        
        assert result == True
        assert simplifier.model_loaded == True
        assert simplifier.tokenizer == mock_tokenizer
        assert simplifier.model == mock_model
    
    @patch('app.models.text_simplifier.T5Tokenizer')
    def test_load_model_failure(self, mock_tokenizer_class, simplifier):
        """Test model loading failure"""
        mock_tokenizer_class.from_pretrained.side_effect = Exception("Download failed")
        
        result = simplifier.load_model()
        
        assert result == False
        assert simplifier.model_loaded == False
    
    def test_preprocess_input_text_valid(self, simplifier):
        """Test text preprocessing with valid input"""
        input_text = "  Pasien dengan hipertensi  "
        result = simplifier.preprocess_input_text(input_text)
        
        assert result == "Pasien dengan hipertensi"
    
    def test_preprocess_input_text_invalid(self, simplifier):
        """Test text preprocessing with invalid input"""
        with pytest.raises(ValueError):
            simplifier.preprocess_input_text("")
        
        with pytest.raises(ValueError):
            simplifier.preprocess_input_text(None)
    
    def test_create_prompt(self, simplifier):
        """Test prompt creation"""
        input_text = "Pasien dengan hipertensi"
        result = simplifier.create_prompt(input_text)
        
        assert result == "sederhanakan: Pasien dengan hipertensi"
    
    @patch('app.models.text_simplifier.torch')
    def test_simplify_medical_text_model_not_loaded(self, mock_torch, simplifier):
        """Test simplification when model is not loaded"""
        simplifier.model_loaded = False
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            simplifier.simplify_medical_text("Test text")

class TestDictionaryPostProcessor:
    """Test cases for DictionaryPostProcessor"""
    
    @pytest.fixture
    def sample_dictionary_csv(self, tmp_path):
        """Create a sample dictionary CSV file for testing"""
        dictionary_data = {
            'term': ['hipertensi', 'diabetes mellitus', 'infark miokard'],
            'simplified': ['tekanan darah tinggi', 'penyakit gula', 'serangan jantung']
        }
        df = pd.DataFrame(dictionary_data)
        csv_path = tmp_path / "test_dictionary.csv"
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    def test_load_dictionary_success(self, sample_dictionary_csv):
        """Test successful dictionary loading"""
        processor = DictionaryPostProcessor(sample_dictionary_csv)
        
        assert len(processor.dictionary) == 3
        assert processor.dictionary['hipertensi'] == 'tekanan darah tinggi'
        assert processor.dictionary['diabetes mellitus'] == 'penyakit gula'
    
    def test_load_dictionary_file_not_found(self):
        """Test dictionary loading with non-existent file"""
        processor = DictionaryPostProcessor("nonexistent.csv")
        
        assert processor.dictionary == {}
    
    def test_post_process_with_replacements(self):
        """Test post-processing with term replacements"""
        processor = DictionaryPostProcessor()
        processor.dictionary = {
            'hipertensi': 'tekanan darah tinggi',
            'diabetes': 'penyakit gula'
        }
        
        input_text = "Pasien dengan hipertensi dan diabetes"
        result = processor.post_process(input_text)
        
        assert "tekanan darah tinggi" in result
        assert "penyakit gula" in result
    
    def test_post_process_no_replacements(self):
        """Test post-processing with no matching terms"""
        processor = DictionaryPostProcessor()
        processor.dictionary = {
            'hipertensi': 'tekanan darah tinggi'
        }
        
        input_text = "Pasien dengan flu biasa"
        result = processor.post_process(input_text)
        
        assert result == input_text
    
    def test_post_process_case_insensitive(self):
        """Test case-insensitive term replacement"""
        processor = DictionaryPostProcessor()
        processor.dictionary = {
            'hipertensi': 'tekanan darah tinggi'
        }
        
        input_text = "Pasien dengan HIPERTENSI"
        result = processor.post_process(input_text)
        
        assert "tekanan darah tinggi" in result

class TestSimplificationMapping:
    """Test cases for simplification mapping functions"""
    
    def test_get_simplification_mapping(self):
        """Test simplification mapping detection"""
        dictionary = {
            'hipertensi': 'tekanan darah tinggi',
            'diabetes': 'penyakit gula'
        }
        
        original_text = "Pasien dengan hipertensi dan diabetes"
        simplified_text = "Pasien dengan tekanan darah tinggi dan penyakit gula"
        
        mapping = get_simplification_mapping(original_text, simplified_text, dictionary)
        
        assert mapping['hipertensi'] == 'tekanan darah tinggi'
        assert mapping['diabetes'] == 'penyakit gula'
        assert len(mapping) == 2
    
    def test_detect_recognized_terms(self):
        """Test medical term detection"""
        dictionary = {
            'hipertensi': 'tekanan darah tinggi',
            'diabetes': 'penyakit gula',
            'infark miokard': 'serangan jantung'
        }
        
        text = "Pasien dengan hipertensi dan diabetes"
        recognized = detect_recognized_terms(text, dictionary)
        
        assert 'hipertensi' in recognized
        assert 'diabetes' in recognized
        assert 'infark miokard' not in recognized
        assert len(recognized) == 2

class TestTextCleaner:
    """Test cases for text cleaning functions"""
    
    def test_final_cleanup_basic(self):
        """Test basic text cleanup"""
        input_text = "  pasien dengan hipertensi  .  "
        result = final_cleanup(input_text)
        
        assert result == "Pasien dengan hipertensi."
    
    def test_final_cleanup_redundant_parts(self):
        """Test removal of redundant parts"""
        input_text = "Kondisi dapat sebabkan hipertensi dan sebabkan diabetes"
        result = final_cleanup(input_text)
        
        # Should remove redundant causation phrases
        assert "sebabkan diabetes" not in result
    
    def test_final_cleanup_duplicate_words(self):
        """Test removal of duplicate words"""
        input_text = "Pasien dengan dengan hipertensi hipertensi"
        result = final_cleanup(input_text)
        
        assert result == "Pasien dengan hipertensi"
    
    def test_final_cleanup_encoding_fix(self):
        """Test encoding issue fixing"""
        # ftfy should handle encoding issues
        input_text = "Pasien dengan hipertensiâ€"  # Common encoding issue
        result = final_cleanup(input_text)
        
        # Result should be cleaned
        assert "â€" not in result
    
    def test_final_cleanup_empty_input(self):
        """Test cleanup with empty input"""
        result = final_cleanup("")
        assert result == ""
        
        result = final_cleanup("   ")
        assert result == ""

class TestIntegration:
    """Integration tests for the complete pipeline"""
    
    def test_complete_pipeline(self):
        """Test the complete text simplification pipeline"""
        # This would be a more complex integration test
        # For now, we'll test the coordination between components
        pass