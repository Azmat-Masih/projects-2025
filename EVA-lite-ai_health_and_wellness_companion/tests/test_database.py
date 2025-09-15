# tests/test_database.py
import pytest
from unittest.mock import Mock, patch
from app.db import (
    User, CheckIn, Memory, 
    get_user_by_id, get_user_checkins, get_user_memories,
    init_db, get_session
)

class TestDatabaseModels:
    """Test cases for database models."""
    
    def test_user_model_creation(self):
        """Test User model creation with valid data."""
        user = User(
            name="Test User",
            phone="+1234567890",
            email="test@example.com",
            timezone="UTC"
        )
        
        assert user.name == "Test User"
        assert user.phone == "+1234567890"
        assert user.email == "test@example.com"
        assert user.timezone == "UTC"
        assert user.id is None  # Not set until saved
    
    def test_checkin_model_creation(self):
        """Test CheckIn model creation with valid data."""
        checkin = CheckIn(
            user_id=1,
            text="I'm feeling good today",
            mood=0.5,
            priority="medium",
            emergency=False
        )
        
        assert checkin.user_id == 1
        assert checkin.text == "I'm feeling good today"
        assert checkin.mood == 0.5
        assert checkin.priority == "medium"
        assert checkin.emergency == False
        assert checkin.id is None
    
    def test_memory_model_creation(self):
        """Test Memory model creation with valid data."""
        memory = Memory(
            user_id=1,
            type="checkin_summary",
            data='{"mood": 0.5, "priority": "medium"}'
        )
        
        assert memory.user_id == 1
        assert memory.type == "checkin_summary"
        assert memory.data == '{"mood": 0.5, "priority": "medium"}'
        assert memory.id is None

class TestDatabaseFunctions:
    """Test cases for database helper functions."""
    
    @patch('app.db.Session')
    def test_get_user_by_id_existing_user(self, mock_session_class):
        """Test getting an existing user by ID."""
        # Mock session and user
        mock_session = Mock()
        mock_user = User(id=1, name="Test User")
        mock_session.get.return_value = mock_user
        mock_session_class.return_value = mock_session
        
        result = get_user_by_id(mock_session, 1)
        
        assert result == mock_user
        mock_session.get.assert_called_once_with(User, 1)
    
    @patch('app.db.Session')
    def test_get_user_by_id_nonexistent_user(self, mock_session_class):
        """Test getting a non-existent user by ID."""
        mock_session = Mock()
        mock_session.get.return_value = None
        mock_session_class.return_value = mock_session
        
        result = get_user_by_id(mock_session, 999)
        
        assert result is None
        mock_session.get.assert_called_once_with(User, 999)
    
    @patch('app.db.Session')
    def test_get_user_checkins(self, mock_session_class):
        """Test getting user check-ins."""
        mock_session = Mock()
        mock_checkin1 = CheckIn(id=1, user_id=1, text="Check-in 1", mood=0.5)
        mock_checkin2 = CheckIn(id=2, user_id=1, text="Check-in 2", mood=-0.2)
        mock_checkins = [mock_checkin1, mock_checkin2]
        
        mock_session.exec.return_value = mock_checkins
        mock_session_class.return_value = mock_session
        
        result = get_user_checkins(mock_session, 1, limit=10)
        
        assert len(result) == 2
        assert result[0] == mock_checkin1
        assert result[1] == mock_checkin2
        mock_session.exec.assert_called_once()
    
    @patch('app.db.Session')
    def test_get_user_memories(self, mock_session_class):
        """Test getting user memories."""
        mock_session = Mock()
        mock_memory1 = Memory(id=1, user_id=1, type="checkin_summary", data="data1")
        mock_memory2 = Memory(id=2, user_id=1, type="other_type", data="data2")
        mock_memories = [mock_memory1, mock_memory2]
        
        mock_session.exec.return_value = mock_memories
        mock_session_class.return_value = mock_session
        
        result = get_user_memories(mock_session, 1)
        
        assert len(result) == 2
        assert result[0] == mock_memory1
        assert result[1] == mock_memory2
        mock_session.exec.assert_called_once()
    
    @patch('app.db.Session')
    def test_get_user_memories_with_type_filter(self, mock_session_class):
        """Test getting user memories with type filter."""
        mock_session = Mock()
        mock_memory = Memory(id=1, user_id=1, type="checkin_summary", data="data1")
        mock_memories = [mock_memory]
        
        mock_session.exec.return_value = mock_memories
        mock_session_class.return_value = mock_session
        
        result = get_user_memories(mock_session, 1, memory_type="checkin_summary")
        
        assert len(result) == 1
        assert result[0] == mock_memory
        mock_session.exec.assert_called_once()

class TestDatabaseSessionManagement:
    """Test cases for database session management."""
    
    @patch('app.db.SQLModel.metadata.create_all')
    def test_init_db_success(self, mock_create_all):
        """Test successful database initialization."""
        init_db()
        mock_create_all.assert_called_once()
    
    @patch('app.db.SQLModel.metadata.create_all')
    def test_init_db_error(self, mock_create_all):
        """Test database initialization with error."""
        mock_create_all.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            init_db()
    
    @patch('app.db.Session')
    def test_get_session_context_manager_success(self, mock_session_class):
        """Test successful session context manager."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        with get_session() as session:
            assert session == mock_session
        
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
    
    @patch('app.db.Session')
    def test_get_session_context_manager_with_error(self, mock_session_class):
        """Test session context manager with error."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        with pytest.raises(Exception):
            with get_session() as session:
                raise Exception("Test error")
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

class TestDatabaseValidation:
    """Test cases for database model validation."""
    
    def test_user_validation(self):
        """Test User model validation."""
        # Valid user
        user = User(name="Test User")
        assert user.name == "Test User"
        assert user.timezone == "UTC"  # Default value
        
        # Test with all fields
        user = User(
            name="Full User",
            phone="+1234567890",
            email="test@example.com",
            timezone="America/New_York"
        )
        assert user.name == "Full User"
        assert user.phone == "+1234567890"
        assert user.email == "test@example.com"
        assert user.timezone == "America/New_York"
    
    def test_checkin_validation(self):
        """Test CheckIn model validation."""
        # Valid check-in
        checkin = CheckIn(
            user_id=1,
            text="Test check-in",
            mood=0.5,
            priority="medium",
            emergency=False
        )
        assert checkin.user_id == 1
        assert checkin.text == "Test check-in"
        assert checkin.mood == 0.5
        assert checkin.priority == "medium"
        assert checkin.emergency == False
    
    def test_memory_validation(self):
        """Test Memory model validation."""
        # Valid memory
        memory = Memory(
            user_id=1,
            type="checkin_summary",
            data='{"test": "data"}'
        )
        assert memory.user_id == 1
        assert memory.type == "checkin_summary"
        assert memory.data == '{"test": "data"}'
