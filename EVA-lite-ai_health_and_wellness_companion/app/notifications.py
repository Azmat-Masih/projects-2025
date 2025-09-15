# app/notifications.py
import logging
import time
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Expose simple constants for tests to patch
TW_ACCOUNT = settings.twilio_account_sid
TW_TOKEN = settings.twilio_auth_token
TW_FROM = settings.twilio_from_phone
SMTP_HOST = settings.smtp_host
SMTP_USER = settings.smtp_user
SMTP_PASS = settings.smtp_password

def _retry_with_backoff(func, *args, **kwargs):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or None if all retries failed
    """
    for attempt in range(settings.notification_retry_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            func_name = getattr(func, "__name__", repr(func))
            if attempt == settings.notification_retry_attempts - 1:
                logger.error(f"All retries failed for {func_name}: {e}")
                return None
            
            delay = settings.notification_retry_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed for {func_name}: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    
    return None

def send_sms(to_phone: str, body: str) -> bool:
    """
    Send SMS message using Twilio with retry logic.
    
    Args:
        to_phone: Recipient phone number
        body: Message body
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not (TW_ACCOUNT and TW_TOKEN and TW_FROM):
        logger.warning("Twilio not configured; skipping SMS.")
        return False
    
    if not to_phone or not body:
        logger.error("Invalid SMS parameters: phone or body is empty")
        return False
    
    def _send_sms():
        client = Client(TW_ACCOUNT, TW_TOKEN)
        message = client.messages.create(
            body=body,
            from_=TW_FROM,
            to=to_phone
        )
        logger.info(f"SMS sent successfully to {to_phone}. SID: {message.sid}")
        return True
    
    try:
        result = _retry_with_backoff(_send_sms)
        if result:
            logger.info(f"SMS sent to {to_phone}")
            return True
        else:
            logger.error(f"Failed to send SMS to {to_phone} after {settings.notification_retry_attempts} attempts")
            return False
    except TwilioException as e:
        logger.error(f"Twilio error sending SMS to {to_phone}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending SMS to {to_phone}: {e}")
        return False

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send email using SMTP with retry logic.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        logger.warning("SMTP not configured; skipping email.")
        return False
    
    if not to_email or not subject or not body:
        logger.error("Invalid email parameters: email, subject, or body is empty")
        return False
    
    def _send_email():
        # Create message
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Add body
        msg.attach(MIMEText(body, "plain"))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    
    try:
        result = _retry_with_backoff(_send_email)
        if result:
            logger.info(f"Email sent to {to_email}")
            return True
        else:
            logger.error(f"Failed to send email to {to_email} after {settings.notification_retry_attempts} attempts")
            return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        return False

def send_notification(to_phone: Optional[str], to_email: Optional[str], subject: str, body: str) -> dict:
    """
    Send notification via both SMS and email if configured.
    
    Args:
        to_phone: Optional phone number for SMS
        to_email: Optional email address
        subject: Notification subject
        body: Notification body
        
    Returns:
        Dictionary with success status for each channel
    """
    results = {
        "sms_sent": False,
        "email_sent": False,
        "sms_error": None,
        "email_error": None
    }
    
    # Send SMS if phone number provided
    if to_phone:
        try:
            results["sms_sent"] = send_sms(to_phone, body)
        except Exception as e:
            results["sms_error"] = str(e)
            logger.error(f"Error sending SMS: {e}")
    
    # Send email if email address provided
    if to_email:
        try:
            results["email_sent"] = send_email(to_email, subject, body)
        except Exception as e:
            results["email_error"] = str(e)
            logger.error(f"Error sending email: {e}")
    
    return results
