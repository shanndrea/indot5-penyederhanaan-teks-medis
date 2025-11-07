import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from app.utils.error_handler import ValidationError, MedicalTermError

@pytest.fixture
def app():
    """Create and configure a Flask app for testing"""
    app = create_app()
    app.config['TESTING'] = True
    
    yield app

@pytest.fixture
def client(app):
    """Test client for the app"""
    return app.test_client()

class TestSimplifyAPI:
    """Test cases for /simplify endpoint"""
    
    def test_simplify_success(self, client):
        """Test successful text simplification"""
        test_data = {
            'text': 'Pasien mengalami hipertensi dan diabetes mellitus tipe 2'
        }
        
        # Mock the model and post-processor
        with patch('app.routes.api.medical_text_simplifier') as mock_model, \
             patch('app.routes.api.post_processor') as mock_processor:
            
            # Setup mocks
            mock_model.model_loaded = True
            mock_model.simplify_medical_text.return_value = 'Pasien memiliki tekanan darah tinggi dan penyakit gula tipe 2'
            mock_processor.dictionary = {
                'hipertensi': 'tekanan darah tinggi',
                'diabetes mellitus tipe 2': 'penyakit gula tipe 2'
            }
            mock_processor.post_process.return_value = 'Pasien memiliki tekanan darah tinggi dan penyakit gula tipe 2'
            
            response = client.post(
                '/simplify',
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert 'tekanan darah tinggi' in data['data']['simplified_text']
    
    def test_simplify_no_medical_terms(self, client):
        """Test text with no medical terms"""
        test_data = {
            'text': 'Hari ini cuaca sangat cerah dan indah'
        }
        
        with patch('app.routes.api.post_processor') as mock_processor:
            mock_processor.dictionary = {
                'hipertensi': 'tekanan darah tinggi'
            }
            
            response = client.post(
                '/simplify',
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['status'] == 'error'
            assert data['error']['code'] == 'NO_MEDICAL_TERMS'
    
    def test_simplify_empty_text(self, client):
        """Test with empty text"""
        test_data = {
            'text': ''
        }
        
        response = client.post(
            '/simplify',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'VALIDATION_ERROR'
    
    def test_simplify_text_too_long(self, client):
        """Test with text exceeding length limit"""
        long_text = 'a' * 2001  # Exceeds MAX_TEXT_LENGTH
        
        test_data = {
            'text': long_text
        }
        
        response = client.post(
            '/simplify',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'VALIDATION_ERROR'
    
    def test_simplify_model_not_loaded(self, client):
        """Test when model is not loaded"""
        test_data = {
            'text': 'Pasien dengan hipertensi'
        }
        
        with patch('app.routes.api.medical_text_simplifier') as mock_model, \
             patch('app.routes.api.post_processor') as mock_processor:
            
            mock_model.model_loaded = False
            mock_processor.dictionary = {'hipertensi': 'tekanan darah tinggi'}
            
            response = client.post(
                '/simplify',
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['error']['code'] == 'MODEL_ERROR'

class TestValidateTextAPI:
    """Test cases for /validate-text endpoint"""
    
    def test_validate_medical_text(self, client):
        """Test validation with medical text"""
        test_data = {
            'text': 'Pasien mengalami hipertensi'
        }
        
        with patch('app.routes.api.post_processor') as mock_processor:
            mock_processor.dictionary = {
                'hipertensi': 'tekanan darah tinggi'
            }
            
            response = client.post(
                '/validate-text',
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['data']['is_medical'] == True
    
    def test_validate_non_medical_text(self, client):
        """Test validation with non-medical text"""
        test_data = {
            'text': 'Hari ini cuaca sangat cerah'
        }
        
        with patch('app.routes.api.post_processor') as mock_processor:
            mock_processor.dictionary = {
                'hipertensi': 'tekanan darah tinggi'
            }
            
            response = client.post(
                '/validate-text',
                data=json.dumps(test_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['data']['is_medical'] == False
    
    def test_validate_empty_text(self, client):
        """Test validation with empty text"""
        test_data = {
            'text': ''
        }
        
        response = client.post(
            '/validate-text',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['is_medical'] == False

class TestHealthAPI:
    """Test cases for health check endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        with patch('app.routes.health.medical_text_simplifier') as mock_model, \
             patch('app.routes.health.post_processor') as mock_processor:
            
            mock_model.model_loaded = True
            mock_model.simplify_medical_text.return_value = 'Simplified text'
            mock_processor.post_process.return_value = 'Processed text'
            mock_processor.dictionary = {'test': 'value'}
            
            response = client.get('/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'status' in data
    
    def test_system_status(self, client):
        """Test system status endpoint"""
        with patch('app.routes.health.medical_text_simplifier') as mock_model:
            mock_model.get_model_status.return_value = {
                'model_loaded': True,
                'model_repo': 'test/repo',
                'device': 'cpu'
            }
            
            response = client.get('/system-status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['application'] == 'Medical Text Simplification API'

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_404_not_found(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_method_not_allowed(self, client):
        """Test 405 method not allowed"""
        response = client.get('/simplify')  # GET instead of POST
        
        assert response.status_code == 405