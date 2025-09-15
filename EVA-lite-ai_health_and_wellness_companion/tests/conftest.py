# tests/conftest.py
import pytest
import os
import tempfile
from unittest.mock import patch, Mock
from sqlmodel import SQLModel, create_engine
from app.db import User, CheckIn, Memory

@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    # Create test engine
    test_engine = create_engine(f"sqlite:///{db_path}")
    
    # Create all tables
    SQLModel.metadata.create_all(test_engine)
    
    yield test_engine
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id=1,
        name="Test User",
        phone="+1234567890",
        email="test@example.com",
        timezone="UTC"
    )

@pytest.fixture
def sample_checkin():
    """Create a sample check-in for testing."""
    return CheckIn(
        id=1,
        user_id=1,
        text="I'm feeling good today",
        mood=0.5,
        priority="medium",
        emergency=False
    )

@pytest.fixture
def sample_memory():
    """Create a sample memory for testing."""
    return Memory(
        id=1,
        user_id=1,
        type="checkin_summary",
        data='{"mood": 0.5, "priority": "medium"}'
    )

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch('app.agent.client') as mock_client:
        yield mock_client

@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client for testing."""
    with patch('app.notifications.Client') as mock_client:
        yield mock_client

@pytest.fixture
def mock_smtp():
    """Mock SMTP for testing."""
    with patch('app.notifications.smtplib.SMTP') as mock_smtp:
        yield mock_smtp

@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    env_vars = {
        'OPENAI_API_KEY': 'test-openai-key',
        'TWILIO_ACCOUNT_SID': 'test-account-sid',
        'TWILIO_AUTH_TOKEN': 'test-auth-token',
        'TWILIO_FROM_PHONE': '+1234567890',
        'SMTP_HOST': 'smtp.test.com',
        'SMTP_PORT': '587',
        'SMTP_USER': 'test@test.com',
        'SMTP_PASS': 'test-password'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def sample_wellness_analysis():
    """Create a sample wellness analysis for testing."""
    from app.agent import WellnessAnalysis
    
    return WellnessAnalysis(
        mood=0.5,
        priority="medium",
        emergency=False,
        suggestions=["Get some rest", "Stay hydrated"],
        follow_up_days=3,
        explanation="You're doing well overall"
    )

@pytest.fixture
def sample_emergency_analysis():
    """Create a sample emergency analysis for testing."""
    from app.agent import WellnessAnalysis
    
    return WellnessAnalysis(
        mood=-0.9,
        priority="high",
        emergency=True,
        suggestions=["Call emergency services immediately"],
        follow_up_days=0,
        explanation="This appears to be a medical emergency"
    )
