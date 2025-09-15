# tests/test_agent.py
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app.agent import WellnessAgent, WellnessAnalysis, extract_json_from_text
from openai import OpenAIError

class TestWellnessAgent:
    """Test cases for the WellnessAgent class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.agent = WellnessAgent()
    
    def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        assert self.agent.model == "gpt-4o-mini"
    
    @patch('app.agent.client')
    def test_analyze_checkin_success(self, mock_client):
        """Test successful check-in analysis."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "mood": 0.5,
            "priority": "medium",
            "emergency": False,
            "suggestions": ["Get some rest", "Stay hydrated"],
            "follow_up_days": 3,
            "explanation": "You seem to be doing well overall"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test analysis
        result = self.agent.analyze_checkin("I'm feeling okay today")
        
        assert isinstance(result, WellnessAnalysis)
        assert result.mood == 0.5
        assert result.priority == "medium"
        assert result.emergency == False
        assert len(result.suggestions) == 2
        assert result.follow_up_days == 3
    
    def test_analyze_checkin_empty_text(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Check-in text cannot be empty"):
            self.agent.analyze_checkin("")
    
    def test_analyze_checkin_whitespace_only(self):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="Check-in text cannot be empty"):
            self.agent.analyze_checkin("   ")
    
    @patch('app.agent.client')
    def test_analyze_checkin_openai_error(self, mock_client):
        """Test handling of OpenAI API errors."""
        mock_client.chat.completions.create.side_effect = OpenAIError("API Error")
        
        result = self.agent.analyze_checkin("I'm feeling sad")
        
        assert isinstance(result, WellnessAnalysis)
        assert result.mood == 0.0
        assert result.priority == "low"
        assert result.emergency == False
        assert "OpenAI API error occurred" in result.explanation
    
    @patch('app.agent.client')
    def test_analyze_checkin_json_retry(self, mock_client):
        """Test JSON parsing retry mechanism."""
        # First response with invalid JSON
        mock_response1 = Mock()
        mock_response1.choices = [Mock()]
        mock_response1.choices[0].message.content = "Invalid JSON response"
        
        # Second response with valid JSON
        mock_response2 = Mock()
        mock_response2.choices = [Mock()]
        mock_response2.choices[0].message.content = json.dumps({
            "mood": -0.3,
            "priority": "high",
            "emergency": False,
            "suggestions": ["Consider talking to someone"],
            "follow_up_days": 1,
            "explanation": "You might benefit from support"
        })
        
        mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]
        
        result = self.agent.analyze_checkin("I'm feeling down")
        
        assert result.mood == -0.3
        assert result.priority == "high"
        assert mock_client.chat.completions.create.call_count == 2
    
    def test_create_fallback_analysis(self):
        """Test fallback analysis creation."""
        result = self.agent._create_fallback_analysis("Test error")
        
        assert isinstance(result, WellnessAnalysis)
        assert result.mood == 0.0
        assert result.priority == "low"
        assert result.emergency == False
        assert "Test error" in result.explanation

class TestExtractJsonFromText:
    """Test cases for JSON extraction function."""
    
    def test_extract_json_simple(self):
        """Test extraction of simple JSON."""
        text = '{"mood": 0.5, "priority": "medium"}'
        result = extract_json_from_text(text)
        assert result == {"mood": 0.5, "priority": "medium"}
    
    def test_extract_json_with_text(self):
        """Test extraction of JSON with surrounding text."""
        text = 'Here is the analysis: {"mood": -0.2, "priority": "low"} and some more text'
        result = extract_json_from_text(text)
        assert result == {"mood": -0.2, "priority": "low"}
    
    def test_extract_json_code_block(self):
        """Test extraction of JSON from code block."""
        text = '```json\n{"mood": 0.8, "priority": "low"}\n```'
        result = extract_json_from_text(text)
        assert result == {"mood": 0.8, "priority": "low"}
    
    def test_extract_json_no_braces(self):
        """Test extraction when no JSON braces are found."""
        text = "This is just plain text with no JSON"
        with pytest.raises(ValueError, match="No JSON found"):
            extract_json_from_text(text)
    
    def test_extract_json_invalid(self):
        """Test extraction of invalid JSON."""
        text = '{"mood": 0.5, "priority": "medium"'  # Missing closing brace
        with pytest.raises(ValueError, match="Couldn't parse JSON"):
            extract_json_from_text(text)

class TestWellnessAnalysis:
    """Test cases for WellnessAnalysis Pydantic model."""
    
    def test_valid_analysis(self):
        """Test creation of valid WellnessAnalysis."""
        analysis = WellnessAnalysis(
            mood=0.5,
            priority="medium",
            emergency=False,
            suggestions=["Get some rest"],
            follow_up_days=3,
            explanation="You're doing well"
        )
        assert analysis.mood == 0.5
        assert analysis.priority == "medium"
        assert analysis.emergency == False
    
    def test_mood_validation(self):
        """Test mood value validation."""
        # Valid mood values
        WellnessAnalysis(mood=-1.0, priority="low", emergency=False)
        WellnessAnalysis(mood=0.0, priority="low", emergency=False)
        WellnessAnalysis(mood=1.0, priority="low", emergency=False)
        
        # Invalid mood values
        with pytest.raises(ValueError):
            WellnessAnalysis(mood=-1.1, priority="low", emergency=False)
        
        with pytest.raises(ValueError):
            WellnessAnalysis(mood=1.1, priority="low", emergency=False)
    
    def test_priority_validation(self):
        """Test priority value validation."""
        # Valid priorities
        WellnessAnalysis(mood=0.0, priority="low", emergency=False)
        WellnessAnalysis(mood=0.0, priority="medium", emergency=False)
        WellnessAnalysis(mood=0.0, priority="high", emergency=False)
        
        # Invalid priority
        with pytest.raises(ValueError):
            WellnessAnalysis(mood=0.0, priority="invalid", emergency=False)
    
    def test_suggestions_validation(self):
        """Test suggestions validation and cleaning."""
        analysis = WellnessAnalysis(
            mood=0.0,
            priority="low",
            emergency=False,
            suggestions=["  suggestion 1  ", "", "  suggestion 2  "]
        )
        assert analysis.suggestions == ["suggestion 1", "suggestion 2"]
    
    def test_follow_up_days_validation(self):
        """Test follow-up days validation."""
        # Valid days
        WellnessAnalysis(mood=0.0, priority="low", emergency=False, follow_up_days=0)
        WellnessAnalysis(mood=0.0, priority="low", emergency=False, follow_up_days=30)
        
        # Invalid days
        with pytest.raises(ValueError):
            WellnessAnalysis(mood=0.0, priority="low", emergency=False, follow_up_days=-1)
        
        with pytest.raises(ValueError):
            WellnessAnalysis(mood=0.0, priority="low", emergency=False, follow_up_days=31)

# Integration tests
class TestAgentIntegration:
    """Integration tests for the agent system."""
    
    @patch('app.agent.client')
    def test_emergency_detection(self, mock_client):
        """Test emergency situation detection."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "mood": -0.9,
            "priority": "high",
            "emergency": True,
            "suggestions": ["Call emergency services immediately"],
            "follow_up_days": 0,
            "explanation": "This appears to be a medical emergency"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        agent = WellnessAgent()
        result = agent.analyze_checkin("I have severe chest pain and can't breathe")
        
        assert result.emergency == True
        assert result.priority == "high"
        assert result.mood == -0.9
        assert "emergency" in result.explanation.lower()
    
    @patch('app.agent.client')
    def test_positive_mood_analysis(self, mock_client):
        """Test analysis of positive mood check-in."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "mood": 0.8,
            "priority": "low",
            "emergency": False,
            "suggestions": ["Keep up the great work!", "Share your positivity"],
            "follow_up_days": 7,
            "explanation": "You're in a great mood today!"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        agent = WellnessAgent()
        result = agent.analyze_checkin("I'm feeling fantastic today!")
        
        assert result.mood == 0.8
        assert result.priority == "low"
        assert result.emergency == False
        assert len(result.suggestions) == 2
        assert result.follow_up_days == 7
