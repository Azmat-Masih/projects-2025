# EVA-Lite: AI Health & Wellness Companion

A modern, AI-powered health and wellness companion built with FastAPI, Streamlit, and OpenAI/Gemini models. EVA-Lite analyzes user check-ins to provide wellness insights, emergency detection, and personalized suggestions.

## 🌟 Features

- **AI-Powered Analysis**: Uses OpenAI's GPT or Google Gemini models to analyze wellness check-ins
- **Emergency Detection**: Automatically detects emergency situations and provides immediate guidance
- **Personalized Suggestions**: Provides tailored wellness recommendations based on mood and context
- **Multi-Channel Notifications**: Supports SMS (Twilio) and email notifications
- **Follow-up Scheduling**: Automatically schedules wellness check-in reminders
- **Modern Web Interface**: Beautiful Streamlit-based frontend with responsive design
- **Comprehensive API**: RESTful API with proper validation and error handling
- **Database Persistence**: SQLite database with proper indexing and relationships
- **Comprehensive Testing**: Full test suite with mocking and integration tests

## 🏗️ Architecture

```
EVA-Lite/
├── app/                    # Backend API
│   ├── main.py            # FastAPI application
│   ├── agent.py           # AI wellness analysis agent
│   ├── db.py              # Database models and operations
│   ├── notifications.py   # SMS and email notifications
│   └── config.py          # Configuration management
├── ui/                    # Frontend
│   └── streamlit_app.py   # Streamlit web interface
├── tests/                 # Test suite
│   ├── test_agent.py      # Agent tests
│   ├── test_api.py        # API tests
│   ├── test_database.py   # Database tests
│   ├── test_notifications.py # Notification tests
│   └── conftest.py        # Test fixtures
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md             # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Either an OpenAI API key or a Google Gemini API key
- (Optional) Twilio account for SMS notifications
- (Optional) SMTP server for email notifications

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd EVA-lite-ai_health_and_wellness_companion
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   # Start the API server (OpenAI default)
   UVICORN_CMD="uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
   $UVICORN_CMD

   # Start the API with Gemini on port 9000 (example)
   # Set environment variables before starting
   export AI_PROVIDER=gemini
   export GEMINI_API_KEY=your_gemini_key
   export GEMINI_MODEL=gemini-1.5-flash
   uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload


  # In another terminal, start the frontend (Streamlit)
  # By default, Streamlit runs on port 8501. You can specify the port as shown below:
  export API_BASE=http://127.0.0.1:9000
  streamlit run ui/streamlit_app.py --server.port 8501
  # Access the frontend at http://localhost:8501
  ```

5. **Access the application**
   - API: http://127.0.0.1:8000 (or your selected port)
   - API Docs (enable by DEBUG=true): http://127.0.0.1:8000/docs
   - Frontend: http://localhost:8501


## ⚠️ Known Issues

- Twilio account and Gmail account are not configured correctly by default. You must update your `.env` file with valid Twilio and Gmail credentials for SMS and email notifications to work.
- If these credentials are missing or incorrect, notification features will fail silently or with errors.

## ⚙️ Configuration

### AI Provider and Keys

Pick one provider and set the corresponding variables:

```bash
# Provider selection
AI_PROVIDER=openai            # or gemini

# OpenAI (when AI_PROVIDER=openai)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Gemini (when AI_PROVIDER=gemini)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash

# Optional: local heuristic analysis if model/API fails
LOCAL_ANALYSIS_ENABLED=true
```

### Optional Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./eva_lite.db

# Twilio (for SMS)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_PHONE=+1234567890

# SMTP (for email)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password

# API Configuration
API_TITLE=EVA-Lite API
DEBUG=false
LOG_LEVEL=INFO
# Point the UI to the API (used by Streamlit UI)
API_BASE=http://127.0.0.1:8000

# Phone number formatting (API validation)
# contact_phone must match ^\+?1?\d{9,15}$ (no spaces). Example: +12345678901
```

See `env.example` for a complete list of configuration options.

## 📚 API Documentation

### Endpoints

#### POST `/api/checkin`
Submit a wellness check-in for analysis.

**Request Body:**
```json
{
  "user_id": 1,
  "text": "I'm feeling tired and stressed today",
  "contact_phone": "+1234567890",
  "contact_email": "user@example.com"
}
```

**Response:**
```json
{
  "mood": -0.3,
  "priority": "medium",
  "emergency": false,
  "suggestions": [
    "Try to get more sleep tonight",
    "Consider some light exercise or meditation"
  ],
  "follow_up_days": 3,
  "explanation": "You seem to be experiencing stress and fatigue. These are common issues that can be addressed with lifestyle changes."
}
```

#### GET `/api/users/{user_id}/checkins`
Get recent check-ins for a user.

**Query Parameters:**
- `limit` (optional): Maximum number of check-ins to return (default: 10)

#### GET `/health`
Health check endpoint.

### Response Codes

- `200 OK`: Successful request
- `201 Created`: Check-in successfully created
- `400 Bad Request`: Invalid input data
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_agent.py

# Run with verbose output
pytest -v
```

### Test Structure

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **API Tests**: Test HTTP endpoints
- **Mocking**: External services are mocked for reliable testing

## 🐳 Docker Deployment

### Build and run with Docker

```bash
# Build the image
docker build -t eva-lite .

# Run the container
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key eva-lite
```

### Docker Compose (recommended)

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AI_PROVIDER=${AI_PROVIDER}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GEMINI_MODEL=${GEMINI_MODEL}
      - LOCAL_ANALYSIS_ENABLED=${LOCAL_ANALYSIS_ENABLED}
      - DATABASE_URL=sqlite:///./eva_lite.db
    volumes:
      - ./data:/app/data
```

## 🧩 Troubleshooting

- Health endpoint hangs in browser
  - Verify server is running and port/host match. Try: `curl -v http://127.0.0.1:8000/health`
  - Change port if occupied: `--port 9000`
  - Ensure `.env` is loaded or env vars are set in the same terminal.

- Always seeing fallback suggestion or priority low
  - Check logs in `eva_lite.log` for provider errors (quota/auth/model).
  - For OpenAI 429/insufficient_quota: add billing or use a different key.
  - For Gemini errors: ensure `AI_PROVIDER=gemini`, a supported `GEMINI_MODEL`, and a valid `GEMINI_API_KEY`.
  - As a temporary measure, set `LOCAL_ANALYSIS_ENABLED=true`.

- 422 on `contact_phone`
  - Remove spaces/dashes. Use digits only with optional leading + and optional 1: `+12345678901`.

- Twilio errors 21659 / 63038
  - Use a valid SMS-enabled Twilio number for your region and stay within account limits.

## 🔧 Development

### Code Quality

The project follows modern Python best practices:

- **Type Hints**: Full type annotation coverage
- **Pydantic Models**: Data validation and serialization
- **Error Handling**: Comprehensive error handling with proper HTTP status codes
- **Logging**: Structured logging throughout the application
- **Testing**: High test coverage with mocking
- **Documentation**: Comprehensive docstrings and API documentation

### Project Structure

- **Separation of Concerns**: Clear separation between API, business logic, and data layers
- **Dependency Injection**: Proper dependency management
- **Configuration Management**: Centralized configuration with environment variable support
- **Database Design**: Proper relationships, indexes, and constraints

### Adding New Features

1. **Database Changes**: Update models in `app/db.py`
2. **API Endpoints**: Add routes in `app/main.py`
3. **Business Logic**: Implement in appropriate modules
4. **Tests**: Add corresponding tests in `tests/`
5. **Documentation**: Update README and docstrings

## 🛡️ Security Considerations

- **Input Validation**: All inputs are validated using Pydantic
- **SQL Injection Prevention**: Using SQLModel ORM with parameterized queries
- **API Key Management**: Environment variable configuration
- **Error Handling**: No sensitive information in error messages
- **CORS Configuration**: Configurable CORS settings

## 📊 Monitoring and Logging

- **Structured Logging**: JSON-formatted logs with timestamps
- **Log Levels**: Configurable logging levels (DEBUG, INFO, WARNING, ERROR)
- **Health Checks**: Built-in health check endpoint
- **Error Tracking**: Comprehensive error logging and handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black isort

# Run code formatting
black app/ tests/
isort app/ tests/

# Run linting
flake8 app/ tests/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

**This application is for educational and demonstration purposes only. It is not intended for medical diagnosis, treatment, or advice. Always consult with qualified healthcare professionals for medical concerns.**

## 🆘 Support

For support, questions, or contributions:

1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information
4. Contact the development team

## 🔮 Future Enhancements

- [ ] User authentication and authorization
- [ ] Advanced analytics and reporting
- [ ] Integration with health tracking devices
- [ ] Mobile application
- [ ] Multi-language support
- [ ] Advanced AI model fine-tuning
- [ ] Real-time notifications
- [ ] Data export functionality
- [ ] Admin dashboard
- [ ] API rate limiting

---

**Built with ❤️ for better health and wellness**
