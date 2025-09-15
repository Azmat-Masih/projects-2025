# ui/streamlit_app.py
import streamlit as st
import requests
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Configure page
st.set_page_config(
    page_title="EVA-Lite Health Companion",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .emergency-alert {
        background-color: #ffebee;
        border: 2px solid #f44336;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e8f5e8;
        border: 2px solid #4caf50;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .suggestion-card {
        background-color: #f0f8ff;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .mood-indicator {
        font-size: 1.5rem;
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .mood-positive { background-color: #e8f5e8; color: #2e7d32; }
    .mood-neutral { background-color: #fff3e0; color: #f57c00; }
    .mood-negative { background-color: #ffebee; color: #c62828; }
</style>
""", unsafe_allow_html=True)

def display_mood_indicator(mood: float) -> None:
    """Display mood with appropriate styling."""
    if mood > 0.3:
        mood_class = "mood-positive"
        mood_emoji = "😊"
        mood_text = "Positive"
    elif mood < -0.3:
        mood_class = "mood-negative"
        mood_emoji = "😔"
        mood_text = "Negative"
    else:
        mood_class = "mood-neutral"
        mood_emoji = "😐"
        mood_text = "Neutral"
    
    st.markdown(f"""
    <div class="mood-indicator {mood_class}">
        <h3>{mood_emoji} Mood: {mood_text} ({mood:.2f})</h3>
    </div>
    """, unsafe_allow_html=True)

def display_emergency_alert(explanation: str) -> None:
    """Display emergency alert with prominent styling."""
    st.markdown(f"""
    <div class="emergency-alert">
        <h3>🚨 EMERGENCY DETECTED</h3>
        <p><strong>Please seek immediate medical attention or call emergency services.</strong></p>
        <p>{explanation}</p>
    </div>
    """, unsafe_allow_html=True)

def display_suggestions(suggestions: list[str]) -> None:
    """Display wellness suggestions in cards."""
    if suggestions:
        st.subheader("💡 Wellness Suggestions")
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"""
            <div class="suggestion-card">
                <strong>{i}.</strong> {suggestion}
            </div>
            """, unsafe_allow_html=True)

def send_checkin(user_id: int, text: str, phone: Optional[str], email: Optional[str]) -> Optional[Dict[str, Any]]:
    """Send check-in to API with proper error handling."""
    payload = {
        "user_id": user_id,
        "text": text,
        "contact_phone": phone if phone else None,
        "contact_email": email if email else None
    }
    
    try:
        with st.spinner("Analyzing your check-in..."):
            response = requests.post(
                f"{API_BASE}/api/checkin",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Could not connect to the server. Please check if the API is running.")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            st.error("❌ Invalid input. Please check your data and try again.")
        elif e.response.status_code == 500:
            st.error("🔧 Server error. Please try again later.")
        else:
            st.error(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return None

def get_user_history(user_id: int) -> Optional[list[Dict[str, Any]]]:
    """Get user's check-in history."""
    try:
        response = requests.get(f"{API_BASE}/api/users/{user_id}/checkins", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load history: {e}")
        return None

# Main UI
st.markdown('<h1 class="main-header">💚 EVA-Lite Health & Wellness Companion</h1>', unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Settings")
    api_base = st.text_input("API Base URL", value=API_BASE, help="Change if running on different host/port")
    
    st.header("📊 Statistics")
    if st.button("🔄 Refresh Stats"):
        st.rerun()

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Daily Check-in")
    
    # User input form
    with st.form("checkin_form"):
        user_id = st.number_input(
            "👤 Your User ID", 
            min_value=1, 
            value=1,
            help="Enter a unique number to identify yourself"
        )
        
        phone = st.text_input(
            "📱 Phone Number (Optional)", 
            placeholder="+1234567890",
            help="For SMS notifications and reminders"
        )
        
        email = st.text_input(
            "📧 Email Address (Optional)", 
            placeholder="your.email@example.com",
            help="For email notifications and reminders"
        )
        
        st.markdown("---")
        
        text = st.text_area(
            "💭 How are you feeling today?", 
            height=150,
            placeholder="Example: I'm feeling tired and haven't slept well. I have a mild headache and feel stressed about work.",
            help="Describe your current physical and emotional state"
        )
        
        submitted = st.form_submit_button("🚀 Send Check-in", use_container_width=True)

    # Process form submission
    if submitted:
        if not text.strip():
            st.error("❌ Please enter your check-in text.")
        else:
            result = send_checkin(user_id, text, phone, email)
            
            if result:
                st.markdown('<div class="success-box"><h3>✅ Analysis Complete!</h3></div>', unsafe_allow_html=True)
                
                # Display mood
                display_mood_indicator(result["mood"])
                
                # Display emergency alert if needed
                if result["emergency"]:
                    display_emergency_alert(result["explanation"])
                else:
                    # Display priority and explanation
                    priority_colors = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                    st.info(f"**Priority Level:** {priority_colors.get(result['priority'], '⚪')} {result['priority'].title()}")
                    
                    if result["explanation"]:
                        st.info(f"**Analysis:** {result['explanation']}")
                
                # Display suggestions
                display_suggestions(result["suggestions"])
                
                # Display follow-up info
                if result["follow_up_days"] > 0:
                    st.success(f"📅 Follow-up reminder scheduled for {result['follow_up_days']} days from now.")
                
                # Display raw data in expander
                with st.expander("🔍 View Raw Analysis Data"):
                    st.json(result)

with col2:
    st.header("📈 Your History")
    
    if st.button("📋 Load Check-in History", use_container_width=True):
        history = get_user_history(user_id)
        
        if history:
            st.success(f"Found {len(history)} recent check-ins")
            
            for i, checkin in enumerate(history[:5]):  # Show last 5
                with st.expander(f"Check-in #{checkin['id']} - {checkin['created_at'][:10]}"):
                    st.write(f"**Text:** {checkin['text']}")
                    if checkin['mood'] is not None:
                        st.write(f"**Mood:** {checkin['mood']:.2f}")
                    if checkin['priority']:
                        st.write(f"**Priority:** {checkin['priority']}")
                    if checkin['emergency']:
                        st.warning("🚨 Emergency detected")
        else:
            st.info("No check-in history found for this user.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>💚 EVA-Lite - Your AI Health & Wellness Companion</p>
    <p><small>This is a demo application. Always consult healthcare professionals for medical advice.</small></p>
</div>
""", unsafe_allow_html=True)
