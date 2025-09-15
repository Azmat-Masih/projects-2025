# app/db.py
import logging
from contextlib import contextmanager
from sqlmodel import SQLModel, Field, create_engine, Session, select, Index
from typing import Optional, Generator
from datetime import datetime
from app.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create engine with better configuration
engine = create_engine(
    settings.database_url, 
    connect_args={"check_same_thread": False},
    echo=settings.debug,  # Enable SQL debugging in debug mode
    pool_pre_ping=True  # Verify connections before use
)

class User(SQLModel, table=True):
    """User model for storing user information."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="User's display name")
    phone: Optional[str] = Field(default=None, max_length=20, description="User's phone number")
    email: Optional[str] = Field(default=None, max_length=255, description="User's email address")
    timezone: Optional[str] = Field(default="UTC", max_length=50, description="User's timezone")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Indexes for better query performance
    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_phone", "phone"),
    )

class CheckIn(SQLModel, table=True):
    """Check-in model for storing user wellness check-ins."""
    __tablename__ = "checkins"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", description="Reference to user")
    text: str = Field(description="User's check-in text")
    mood: Optional[float] = Field(default=None, ge=-1.0, le=1.0, description="Analyzed mood score")
    priority: Optional[str] = Field(default=None, description="Priority level (low/medium/high)")
    emergency: bool = Field(default=False, description="Whether this is an emergency")
    meta: Optional[str] = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Check-in timestamp")
    
    # Indexes for better query performance
    __table_args__ = (
        Index("idx_checkin_user_id", "user_id"),
        Index("idx_checkin_created_at", "created_at"),
        Index("idx_checkin_emergency", "emergency"),
        Index("idx_checkin_priority", "priority"),
    )

class Memory(SQLModel, table=True):
    """Memory model for storing agent memories and context."""
    __tablename__ = "memories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", description="Reference to user")
    type: str = Field(max_length=50, description="Type of memory (checkin_summary, etc.)")
    data: str = Field(description="Memory data as JSON string")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Memory creation timestamp")
    
    # Indexes for better query performance
    __table_args__ = (
        Index("idx_memory_user_id", "user_id"),
        Index("idx_memory_type", "type"),
        Index("idx_memory_created_at", "created_at"),
    )

def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function creates all tables defined in the SQLModel metadata.
    It's safe to call multiple times.
    """
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get a database session with proper context management.
    
    This context manager ensures that the session is properly closed
    and any transactions are committed or rolled back as needed.
    
    Yields:
        SQLModel Session object
        
    Example:
        with get_session() as session:
            user = session.get(User, 1)
            # Session is automatically closed after this block
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """
    Get a user by their ID.
    
    Args:
        session: Database session
        user_id: User ID to look up
        
    Returns:
        User object if found, None otherwise
    """
    return session.get(User, user_id)

def get_user_checkins(session: Session, user_id: int, limit: int = 10) -> list[CheckIn]:
    """
    Get recent check-ins for a user.
    
    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of check-ins to return
        
    Returns:
        List of CheckIn objects, ordered by creation date (newest first)
    """
    statement = (
        select(CheckIn)
        .where(CheckIn.user_id == user_id)
        .order_by(CheckIn.created_at.desc())
        .limit(limit)
    )
    return list(session.exec(statement))

def get_user_memories(session: Session, user_id: int, memory_type: Optional[str] = None) -> list[Memory]:
    """
    Get memories for a user, optionally filtered by type.
    
    Args:
        session: Database session
        user_id: User ID
        memory_type: Optional memory type filter
        
    Returns:
        List of Memory objects, ordered by creation date (newest first)
    """
    statement = select(Memory).where(Memory.user_id == user_id)
    
    if memory_type:
        statement = statement.where(Memory.type == memory_type)
    
    statement = statement.order_by(Memory.created_at.desc())
    
    return list(session.exec(statement))
