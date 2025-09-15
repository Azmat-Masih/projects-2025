# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app
from app.agent import WellnessAnalysis

client = TestClient(app)

class TestCheckInAPI:
    """Test cases for the check-in API endpoint."""
    
    @patch('app.main.agent')
    @patch('app.main.get_session')
    def test_post_checkin_success(self, mock_get_session, mock_agent):
        """Test successful check-in submission."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.get.return_value = None  # User doesn't exist
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        # Mock agent analysis
        mock_analysis = WellnessAnalysis(
            mood=0.5,
            priority="medium",
            emergency=False,
            suggestions=["Get some rest"],
            follow_up_days=3,
            explanation="You're doing well"
        )
        mock_agent.analyze_checkin.return_value = mock_analysis
        
        # Test request
        response = client.post("/api/checkin", json={
            "user_id": 1,
            "text": "I'm feeling okay today",
            "contact_phone": "+1234567890",
            "contact_email": "test@example.com"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["mood"] == 0.5
        assert data["priority"] == "medium"
        assert data["emergency"] == False
        assert len(data["suggestions"]) == 1
        assert data["follow_up_days"] == 3
    
    def test_post_checkin_invalid_input(self):
        """Test check-in with invalid input."""
        response = client.post("/api/checkin", json={
            "user_id": 0,  # Invalid user ID
            "text": "",    # Empty text
            "contact_phone": "invalid-phone",
            "contact_email": "invalid-email"
        })
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.main.agent')
    @patch('app.main.get_session')
    def test_post_checkin_emergency(self, mock_get_session, mock_agent):
        """Test check-in with emergency detection."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.get.return_value = None
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        # Mock emergency analysis
        mock_analysis = WellnessAnalysis(
            mood=-0.9,
            priority="high",
            emergency=True,
            suggestions=["Call emergency services"],
            follow_up_days=0,
            explanation="This is a medical emergency"
        )
        mock_agent.analyze_checkin.return_value = mock_analysis
        
        response = client.post("/api/checkin", json={
            "user_id": 1,
            "text": "I have severe chest pain",
            "contact_phone": "+1234567890"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["emergency"] == True
        assert data["priority"] == "high"
    
    def test_post_checkin_missing_required_fields(self):
        """Test check-in with missing required fields."""
        response = client.post("/api/checkin", json={
            "user_id": 1
            # Missing text field
        })
        
        assert response.status_code == 422

class TestHealthAPI:
    """Test cases for the health check endpoint."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

class TestUserCheckinsAPI:
    """Test cases for the user check-ins endpoint."""
    
    @patch('app.main.get_session')
    def test_get_user_checkins(self, mock_get_session):
        """Test getting user check-ins."""
        # Mock database session and data
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_checkin = Mock()
        mock_checkin.id = 1
        mock_checkin.text = "Test check-in"
        mock_checkin.mood = 0.5
        mock_checkin.priority = "medium"
        mock_checkin.emergency = False
        mock_checkin.created_at = "2024-01-01T00:00:00"
        
        mock_session.exec.return_value = [mock_checkin]
        
        response = client.get("/api/users/1/checkins")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["text"] == "Test check-in"
    
    @patch('app.main.get_session')
    def test_get_user_checkins_with_limit(self, mock_get_session):
        """Test getting user check-ins with limit."""
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.exec.return_value = []
        
        response = client.get("/api/users/1/checkins?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestAPIValidation:
    """Test cases for API input validation."""
    
    def test_phone_validation(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_phones = ["+1234567890", "1234567890", "+44123456789"]
        
        for phone in valid_phones:
            response = client.post("/api/checkin", json={
                "user_id": 1,
                "text": "Test check-in",
                "contact_phone": phone
            })
            # Should not be a validation error (might be other errors)
            assert response.status_code != 422
    
    def test_email_validation(self):
        """Test email validation."""
        # Valid emails
        valid_emails = ["test@example.com", "user.name@domain.co.uk"]
        
        for email in valid_emails:
            response = client.post("/api/checkin", json={
                "user_id": 1,
                "text": "Test check-in",
                "contact_email": email
            })
            assert response.status_code != 422
    
    def test_text_validation(self):
        """Test text validation."""
        # Empty text should fail
        response = client.post("/api/checkin", json={
            "user_id": 1,
            "text": ""
        })
        assert response.status_code == 422
        
        # Whitespace-only text should fail
        response = client.post("/api/checkin", json={
            "user_id": 1,
            "text": "   "
        })
        assert response.status_code == 422
        
        # Valid text should pass validation
        response = client.post("/api/checkin", json={
            "user_id": 1,
            "text": "I'm feeling good today"
        })
        # Might fail for other reasons, but not validation
        assert response.status_code != 422
