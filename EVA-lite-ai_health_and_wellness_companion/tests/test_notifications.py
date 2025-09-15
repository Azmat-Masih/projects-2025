# tests/test_notifications.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.notifications import send_sms, send_email, send_notification, _retry_with_backoff

class TestSMSNotifications:
    """Test cases for SMS notification functionality."""
    
    @patch('app.notifications.TW_ACCOUNT', 'test_account')
    @patch('app.notifications.TW_TOKEN', 'test_token')
    @patch('app.notifications.TW_FROM', '+1234567890')
    @patch('app.notifications.Client')
    def test_send_sms_success(self, mock_client_class):
        """Test successful SMS sending."""
        # Mock Twilio client
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = "test_sid"
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client
        
        result = send_sms("+1987654321", "Test message")
        
        assert result == True
        mock_client.messages.create.assert_called_once_with(
            body="Test message",
            from_="+1234567890",
            to="+1987654321"
        )
    
    @patch('app.notifications.TW_ACCOUNT', None)
    def test_send_sms_not_configured(self):
        """Test SMS sending when Twilio is not configured."""
        result = send_sms("+1987654321", "Test message")
        assert result == False
    
    def test_send_sms_invalid_parameters(self):
        """Test SMS sending with invalid parameters."""
        # Empty phone number
        result = send_sms("", "Test message")
        assert result == False
        
        # Empty message
        result = send_sms("+1987654321", "")
        assert result == False
        
        # None phone number
        result = send_sms(None, "Test message")
        assert result == False
    
    @patch('app.notifications.TW_ACCOUNT', 'test_account')
    @patch('app.notifications.TW_TOKEN', 'test_token')
    @patch('app.notifications.TW_FROM', '+1234567890')
    @patch('app.notifications.Client')
    def test_send_sms_twilio_error(self, mock_client_class):
        """Test SMS sending with Twilio error."""
        from twilio.base.exceptions import TwilioException
        
        mock_client = Mock()
        mock_client.messages.create.side_effect = TwilioException("API Error")
        mock_client_class.return_value = mock_client
        
        result = send_sms("+1987654321", "Test message")
        assert result == False

class TestEmailNotifications:
    """Test cases for email notification functionality."""
    
    @patch('app.notifications.SMTP_HOST', 'smtp.example.com')
    @patch('app.notifications.SMTP_USER', 'test@example.com')
    @patch('app.notifications.SMTP_PASS', 'password')
    @patch('app.notifications.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp_class):
        """Test successful email sending."""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        
        result = send_email("recipient@example.com", "Test Subject", "Test body")
        
        assert result == True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.send_message.assert_called_once()
    
    @patch('app.notifications.SMTP_HOST', None)
    def test_send_email_not_configured(self):
        """Test email sending when SMTP is not configured."""
        result = send_email("recipient@example.com", "Test Subject", "Test body")
        assert result == False
    
    def test_send_email_invalid_parameters(self):
        """Test email sending with invalid parameters."""
        # Empty email
        result = send_email("", "Test Subject", "Test body")
        assert result == False
        
        # Empty subject
        result = send_email("recipient@example.com", "", "Test body")
        assert result == False
        
        # Empty body
        result = send_email("recipient@example.com", "Test Subject", "")
        assert result == False
    
    @patch('app.notifications.SMTP_HOST', 'smtp.example.com')
    @patch('app.notifications.SMTP_USER', 'test@example.com')
    @patch('app.notifications.SMTP_PASS', 'password')
    @patch('app.notifications.smtplib.SMTP')
    def test_send_email_smtp_error(self, mock_smtp_class):
        """Test email sending with SMTP error."""
        import smtplib
        
        mock_smtp_class.side_effect = smtplib.SMTPException("SMTP Error")
        
        result = send_email("recipient@example.com", "Test Subject", "Test body")
        assert result == False

class TestRetryMechanism:
    """Test cases for retry mechanism."""
    
    def test_retry_with_backoff_success_first_attempt(self):
        """Test retry mechanism when function succeeds on first attempt."""
        mock_func = Mock(return_value="success")
        
        result = _retry_with_backoff(mock_func, "arg1", "arg2", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    
    def test_retry_with_backoff_success_after_retries(self):
        """Test retry mechanism when function succeeds after retries."""
        mock_func = Mock(side_effect=[Exception("Error 1"), Exception("Error 2"), "success"])
        
        result = _retry_with_backoff(mock_func, "arg1")
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_with_backoff_all_attempts_fail(self):
        """Test retry mechanism when all attempts fail."""
        mock_func = Mock(side_effect=Exception("Persistent error"))
        
        result = _retry_with_backoff(mock_func, "arg1")
        
        assert result is None
        assert mock_func.call_count == 3  # MAX_RETRIES

class TestNotificationIntegration:
    """Test cases for integrated notification functionality."""
    
    @patch('app.notifications.send_sms')
    @patch('app.notifications.send_email')
    def test_send_notification_both_channels(self, mock_send_email, mock_send_sms):
        """Test sending notification via both SMS and email."""
        mock_send_sms.return_value = True
        mock_send_email.return_value = True
        
        result = send_notification(
            to_phone="+1234567890",
            to_email="test@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        assert result["sms_sent"] == True
        assert result["email_sent"] == True
        assert result["sms_error"] is None
        assert result["email_error"] is None
        
        mock_send_sms.assert_called_once_with("+1234567890", "Test body")
        mock_send_email.assert_called_once_with("test@example.com", "Test Subject", "Test body")
    
    @patch('app.notifications.send_sms')
    @patch('app.notifications.send_email')
    def test_send_notification_sms_only(self, mock_send_email, mock_send_sms):
        """Test sending notification via SMS only."""
        mock_send_sms.return_value = True
        
        result = send_notification(
            to_phone="+1234567890",
            to_email=None,
            subject="Test Subject",
            body="Test body"
        )
        
        assert result["sms_sent"] == True
        assert result["email_sent"] == False
        assert result["sms_error"] is None
        assert result["email_error"] is None
        
        mock_send_sms.assert_called_once_with("+1234567890", "Test body")
        mock_send_email.assert_not_called()
    
    @patch('app.notifications.send_sms')
    @patch('app.notifications.send_email')
    def test_send_notification_email_only(self, mock_send_email, mock_send_sms):
        """Test sending notification via email only."""
        mock_send_email.return_value = True
        
        result = send_notification(
            to_phone=None,
            to_email="test@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        assert result["sms_sent"] == False
        assert result["email_sent"] == True
        assert result["sms_error"] is None
        assert result["email_error"] is None
        
        mock_send_email.assert_called_once_with("test@example.com", "Test Subject", "Test body")
        mock_send_sms.assert_not_called()
    
    @patch('app.notifications.send_sms')
    @patch('app.notifications.send_email')
    def test_send_notification_with_errors(self, mock_send_email, mock_send_sms):
        """Test sending notification with errors in both channels."""
        mock_send_sms.side_effect = Exception("SMS Error")
        mock_send_email.side_effect = Exception("Email Error")
        
        result = send_notification(
            to_phone="+1234567890",
            to_email="test@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        assert result["sms_sent"] == False
        assert result["email_sent"] == False
        assert "SMS Error" in result["sms_error"]
        assert "Email Error" in result["email_error"]
