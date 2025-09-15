# app/config.py
import os
import logging
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""
    
    # API Configuration
    api_title: str = Field(default="EVA-Lite API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(default="AI-powered health and wellness companion API", description="API description")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./eva_lite.db", description="Database URL")
    
    # AI Provider Configuration
    ai_provider: str = Field(default="openai", description="AI provider to use: openai or gemini")
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    # Gemini Configuration
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model to use")
    openai_max_tokens: int = Field(default=500, description="Maximum tokens for OpenAI responses")
    openai_temperature: float = Field(default=0.5, ge=0.0, le=2.0, description="OpenAI temperature")
    openai_timeout: int = Field(default=30, description="OpenAI request timeout in seconds")
    local_analysis_enabled: bool = Field(default=False, description="Use local analysis if OpenAI is unavailable or disabled")
    
    # Twilio Configuration
    twilio_account_sid: Optional[str] = Field(default=None, description="Twilio Account SID")
    twilio_auth_token: Optional[str] = Field(default=None, description="Twilio Auth Token")
    twilio_from_phone: Optional[str] = Field(default=None, description="Twilio from phone number")
    
    # SMTP Configuration
    smtp_host: Optional[str] = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")
    
    # Notification Configuration
    notification_retry_attempts: int = Field(default=3, ge=1, le=10, description="Number of retry attempts for notifications")
    notification_retry_delay: int = Field(default=1, ge=1, le=60, description="Base delay between retries in seconds")
    
    # Scheduler Configuration
    scheduler_timezone: str = Field(default="UTC", description="Scheduler timezone")
    
    # CORS Configuration
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")
    cors_allow_methods: list[str] = Field(default=["*"], description="CORS allowed methods")
    cors_allow_headers: list[str] = Field(default=["*"], description="CORS allowed headers")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    
    # Frontend Configuration
    frontend_api_base: str = Field(default="http://localhost:8000", description="Frontend API base URL")
    
    @validator('ai_provider')
    def validate_ai_provider(cls, v):
        providers = ['openai', 'gemini']
        if v not in providers:
            raise ValueError(f"ai_provider must be one of: {providers}")
        return v

    @validator('openai_api_key', always=True)
    def validate_openai_key(cls, v, values):
        if values.get('ai_provider', 'openai') == 'openai' and not v:
            raise ValueError("OPENAI_API_KEY is required when ai_provider=openai")
        return v

    @validator('gemini_api_key', always=True)
    def validate_gemini_key(cls, v, values):
        if values.get('ai_provider') == 'gemini' and not v:
            raise ValueError("GEMINI_API_KEY is required when ai_provider=gemini")
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator('openai_temperature')
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v
    
    @validator('smtp_port')
    def validate_smtp_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535")
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()

def setup_logging(settings: Settings) -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("eva_lite.log")
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlmodel").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

def validate_configuration(settings: Settings) -> None:
    """Validate configuration and log warnings for missing optional settings."""
    logger = logging.getLogger(__name__)
    
    # Check optional configurations
    if not settings.twilio_account_sid:
        logger.warning("Twilio not configured - SMS notifications will be disabled")
    
    if not settings.smtp_host:
        logger.warning("SMTP not configured - Email notifications will be disabled")
    
    if settings.debug:
        logger.warning("Debug mode is enabled - this should not be used in production")
    
    # Log configuration summary
    logger.info(f"API Title: {settings.api_title}")
    logger.info(f"API Version: {settings.api_version}")
    logger.info(f"Database URL: {settings.database_url}")
    logger.info(f"OpenAI Model: {settings.openai_model}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info(f"Debug Mode: {settings.debug}")

# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development-specific settings."""
    debug: bool = True
    log_level: str = "DEBUG"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]

class ProductionSettings(Settings):
    """Production-specific settings."""
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = []  # Should be configured per deployment

class TestingSettings(Settings):
    """Testing-specific settings."""
    debug: bool = True
    log_level: str = "DEBUG"
    database_url: str = "sqlite:///:memory:"
    openai_api_key: str = "test-key"
    cors_origins: list[str] = ["*"]

def get_settings_for_environment(env: str = None) -> Settings:
    """Get settings for specific environment."""
    if env is None:
        env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
