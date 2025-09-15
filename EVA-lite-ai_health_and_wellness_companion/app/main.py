# app/main.py
import logging
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
from app.db import init_db, get_session, CheckIn, Memory, User, get_user_by_id
from app.agent import WellnessAgent, WellnessAnalysis
from app.notifications import send_sms, send_email
from app.config import get_settings, setup_logging, validate_configuration
from apscheduler.schedulers.background import BackgroundScheduler

# Get settings and configure logging
settings = get_settings()
setup_logging(settings)
validate_configuration(settings)

logger = logging.getLogger(__name__)

# Initialize database and agent
init_db()
agent = WellnessAgent()

# Create FastAPI app with configuration from settings
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Pydantic models with validation
class CheckInRequest(BaseModel):
    """Request model for user check-ins."""
    user_id: int = Field(..., gt=0, description="User ID")
    text: str = Field(..., min_length=1, max_length=1000, description="Check-in text")
    contact_phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$', description="Phone number for SMS")
    contact_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$', description="Email address")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Check-in text cannot be empty')
        return v.strip()

class AgentResponse(BaseModel):
    """Response model for agent analysis."""
    mood: float = Field(..., ge=-1.0, le=1.0, description="Mood score from -1.0 to 1.0")
    priority: str = Field(..., description="Priority level")
    emergency: bool = Field(..., description="Whether this is an emergency")
    suggestions: list[str] = Field(..., description="List of wellness suggestions")
    follow_up_days: int = Field(..., ge=0, le=30, description="Days until next follow-up")
    explanation: str = Field(..., description="Human-friendly explanation")

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

def schedule_followup(user_id: int, days: int, contact_phone: Optional[str], contact_email: Optional[str]) -> None:
    """
    Schedule a follow-up reminder for a user.
    
    Args:
        user_id: User ID
        days: Number of days until follow-up
        contact_phone: Optional phone number for SMS
        contact_email: Optional email address
    """
    if days <= 0:
        logger.warning(f"Invalid follow-up days: {days}")
        return
        
    run_date = datetime.utcnow() + timedelta(days=days)
    
    def job():
        """Background job to send follow-up messages."""
        body = "Hi — it's a check-in reminder from EVA-Lite. How are you today?"
        logger.info(f"Sending follow-up to user {user_id}")
        
        if contact_phone:
            success = send_sms(contact_phone, body)
            if success:
                logger.info(f"SMS sent to {contact_phone}")
            else:
                logger.error(f"Failed to send SMS to {contact_phone}")
                
        if contact_email:
            success = send_email(contact_email, "EVA-Lite follow-up", body)
            if success:
                logger.info(f"Email sent to {contact_email}")
            else:
                logger.error(f"Failed to send email to {contact_email}")
    
    try:
        scheduler.add_job(job, 'date', run_date=run_date, id=f"followup_{user_id}_{run_date.timestamp()}")
        logger.info(f"Scheduled follow-up for user {user_id} in {days} days")
    except Exception as e:
        logger.error(f"Failed to schedule follow-up: {e}")

# Dependency to get database session
def get_db_session():
    """Dependency to get database session."""
    with get_session() as session:
        yield session

@app.post("/api/checkin", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def post_checkin(
    req: CheckInRequest, 
    background_tasks: BackgroundTasks,
    db_session = Depends(get_db_session)
) -> AgentResponse:
    """
    Process a user check-in and return wellness analysis.
    
    This endpoint analyzes the user's check-in text using AI and provides
    wellness insights, suggestions, and emergency detection.
    """
    logger.info(f"Processing check-in for user {req.user_id}")
    
    try:
        # Validate user exists (create simple user if missing)
        user = get_user_by_id(db_session, req.user_id)
        if not user:
            logger.info(f"Creating new user {req.user_id}")
            user = User(
                id=req.user_id, 
                name=f"user-{req.user_id}", 
                phone=req.contact_phone,
                email=req.contact_email
            )
            db_session.add(user)
            db_session.commit()
        
        # Analyze check-in
        logger.info(f"Analyzing check-in text: {req.text[:50]}...")
        analysis = agent.analyze_checkin(req.text)
        
        # Save check-in and memory
        checkin = CheckIn(
            user_id=req.user_id,
            text=req.text,
            mood=analysis.mood,
            priority=analysis.priority,
            emergency=analysis.emergency,
            meta=analysis.explanation
        )
        db_session.add(checkin)
        
        memory = Memory(
            user_id=req.user_id,
            type="checkin_summary",
            data=analysis.model_dump_json()
        )
        db_session.add(memory)
        db_session.commit()
        
        logger.info(f"Check-in saved with mood: {analysis.mood}, priority: {analysis.priority}")
        
        # Handle emergency situations
        if analysis.emergency:
            logger.warning(f"Emergency detected for user {req.user_id}")
            emergency_msg = f"EMERGENCY: {analysis.explanation}"
            
            if req.contact_phone:
                background_tasks.add_task(send_sms, req.contact_phone, emergency_msg)
            if req.contact_email:
                background_tasks.add_task(send_email, req.contact_email, "EVA-Lite Emergency", emergency_msg)
            
            return AgentResponse(
                mood=analysis.mood,
                priority=analysis.priority,
                emergency=analysis.emergency,
                suggestions=analysis.suggestions,
                follow_up_days=analysis.follow_up_days,
                explanation=analysis.explanation
            )
        
        # Schedule follow-up if requested
        if analysis.follow_up_days > 0:
            schedule_followup(req.user_id, analysis.follow_up_days, req.contact_phone, req.contact_email)
        
        # Send suggestions
        if analysis.suggestions:
            suggestions_text = "EVA-Lite suggestions:\n" + "\n".join(f"- {sugg}" for sugg in analysis.suggestions)
            if req.contact_phone:
                background_tasks.add_task(send_sms, req.contact_phone, suggestions_text)
            if req.contact_email:
                background_tasks.add_task(send_email, req.contact_email, "EVA-Lite suggestions", suggestions_text)
        
        return AgentResponse(
            mood=analysis.mood,
            priority=analysis.priority,
            emergency=analysis.emergency,
            suggestions=analysis.suggestions,
            follow_up_days=analysis.follow_up_days,
            explanation=analysis.explanation
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error processing check-in: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing check-in"
        )

@app.get("/health", response_model=dict)
def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns the current status of the API and its dependencies.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "EVA-Lite API"
    }

@app.get("/api/users/{user_id}/checkins", response_model=list[dict])
def get_user_checkins(user_id: int, limit: int = 10, db_session = Depends(get_db_session)) -> list[dict]:
    """
    Get recent check-ins for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of check-ins to return (default: 10)
        
    Returns:
        List of check-in records
    """
    from app.db import get_user_checkins
    
    try:
        checkins = get_user_checkins(db_session, user_id, limit)
        def to_iso(val):
            return val.isoformat() if hasattr(val, "isoformat") else str(val)
        return [
            {
                "id": c.id,
                "text": c.text,
                "mood": c.mood,
                "priority": c.priority,
                "emergency": c.emergency,
                "created_at": to_iso(c.created_at)
            }
            for c in checkins
        ]
    except Exception as e:
        logger.error(f"Error fetching check-ins for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch check-ins"
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
