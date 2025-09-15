# app/agent.py
import json
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from openai import OpenAI, OpenAIError
try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None
from pydantic import BaseModel, Field, validator
from app.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize provider clients
client = None
if settings.ai_provider == 'openai' and settings.openai_api_key:
    client = OpenAI(api_key=settings.openai_api_key)
elif settings.ai_provider == 'gemini' and settings.gemini_api_key and genai is not None:
    genai.configure(api_key=settings.gemini_api_key)

# Pydantic models for better validation
class WellnessAnalysis(BaseModel):
    mood: float = Field(..., ge=-1.0, le=1.0, description="Mood score from -1.0 (very negative) to 1.0 (very positive)")
    priority: str = Field(..., pattern="^(low|medium|high)$", description="Priority level")
    emergency: bool = Field(default=False, description="Whether this is an emergency situation")
    suggestions: list[str] = Field(default_factory=list, max_items=5, description="List of wellness suggestions")
    follow_up_days: int = Field(default=0, ge=0, le=30, description="Days until next follow-up")
    explanation: str = Field(default="", max_length=500, description="Human-friendly explanation")
    
    @validator('suggestions')
    def validate_suggestions(cls, v):
        return [s.strip() for s in v if s.strip()]

SYSTEM_PROMPT = """You are EVA-Lite, an empathetic, non-diagnostic health & wellness assistant.
You analyze short user check-ins and return a JSON object with this schema:
{
  "mood": float,           # -1.0 (very negative) .. 0 neutral .. +1.0 (very positive)
  "priority": "low|medium|high",
  "emergency": bool,
  "suggestions": [ "string" ],
  "follow_up_days": integer, # recommended days until next followup or 0
  "explanation": "short human-friendly explanation"
}
Rules:
- If the user describes severe chest pain, difficulty breathing, loss of consciousness, suicidal thoughts, or other red-flag emergency symptoms, set emergency=true and priority=high and include immediate action instructions like: 'If you are in immediate danger, call emergency services now (call 911 or your local emergency number).'
- Do NOT offer medical diagnosis. Offer lifestyle tips only and encourage seeing a medical professional when needed.
- Keep suggestions concise (1-3 short bullets).
Return only valid JSON in the response. If you include text, wrap it in JSON fields only.
"""

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract JSON from text response, handling various formats.
    
    Args:
        text: Raw text response from OpenAI
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If no valid JSON can be extracted
    """
    logger.debug(f"Extracting JSON from text: {text[:100]}...")
    
    # Try to locate JSON substring
    idx = text.find("{")
    if idx == -1:
        # Fallback: attempt to find triple-backtick JSON
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if m:
            raw = m.group(1)
        else:
            raise ValueError("No JSON found in model response")
    else:
        # Find matching braces (simple heuristic)
        raw = text[idx:]
        # Trim trailing text that is not part of JSON
        # Try incremental parsing until success
        for end in range(len(raw), 0, -1):
            try:
                candidate = raw[:end]
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise ValueError("Couldn't parse JSON from text")
    
    return json.loads(raw)

class WellnessAgent:
    """
    AI-powered wellness analysis agent using OpenAI's GPT models.
    
    This class handles the analysis of user check-ins and provides
    wellness insights, suggestions, and emergency detection.
    """
    
    def __init__(self, model: str = None):
        """
        Initialize the wellness agent.
        
        Args:
            model: OpenAI model to use for analysis (defaults to settings)
        """
        self.model = model or (settings.openai_model if settings.ai_provider == 'openai' else settings.gemini_model)
        logger.info(f"Initialized WellnessAgent with model: {self.model}")

    def analyze_checkin(self, text: str, user_profile: Optional[Dict[str, Any]] = None) -> WellnessAnalysis:
        """
        Analyze a user's wellness check-in text.
        
        Args:
            text: User's check-in text
            user_profile: Optional user profile data for context
            
        Returns:
            WellnessAnalysis object with analysis results
            
        Raises:
            ValueError: If text is empty or invalid
        """
        if not text or not text.strip():
            raise ValueError("Check-in text cannot be empty")
            
        logger.info(f"Analyzing check-in: {text[:50]}...")

        # Local analysis mode (no OpenAI call)
        if settings.local_analysis_enabled:
            return self._local_analyze(text)
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"User check-in: \"{text.strip()}\""}
        ]
        
        try:
            # Provider-specific call
            if settings.ai_provider == 'openai':
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=settings.openai_max_tokens,
                    temperature=settings.openai_temperature,
                    timeout=settings.openai_timeout
                )
                content = response.choices[0].message.content
                logger.debug(f"OpenAI response: {content[:100]}...")
            else:
                # Gemini
                model = genai.GenerativeModel(self.model)
                # Convert OpenAI messages to a single prompt for Gemini
                prompt = "\n".join([m["content"] for m in messages])
                resp = model.generate_content(prompt)
                content = resp.text or "{}"
                logger.debug(f"Gemini response: {content[:100]}...")
            
            # Extract and validate JSON
            try:
                parsed_data = extract_json_from_text(content)
                analysis = WellnessAnalysis(**parsed_data)
                logger.info(f"Analysis complete - Mood: {analysis.mood}, Priority: {analysis.priority}, Emergency: {analysis.emergency}")
                return analysis
                
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"JSON extraction failed, retrying: {e}")
                # Fallback: ask model to return shorter JSON
                messages.extend([
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": "Please respond ONLY with the JSON object described earlier; no extra text."}
                ])
                
                if settings.ai_provider == 'openai':
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=settings.openai_max_tokens // 2,
                        temperature=0,
                        timeout=settings.openai_timeout
                    )
                    parsed_data = extract_json_from_text(response.choices[0].message.content)
                else:
                    prompt = "\n".join([m["content"] for m in messages])
                    resp = model.generate_content(prompt)
                    parsed_data = extract_json_from_text(resp.text or "{}")
                analysis = WellnessAnalysis(**parsed_data)
                logger.info(f"Analysis complete (retry) - Mood: {analysis.mood}, Priority: {analysis.priority}")
                return analysis
                
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            if settings.local_analysis_enabled:
                return self._local_analyze(text)
            return self._create_fallback_analysis("OpenAI API error occurred")
        except Exception as e:
            # Gemini or generic error
            logger.error(f"Model API error: {e}")
            if settings.local_analysis_enabled:
                return self._local_analyze(text)
            return self._create_fallback_analysis("Model API error occurred")
    
    def _create_fallback_analysis(self, reason: str) -> WellnessAnalysis:
        """
        Create a fallback analysis when the main analysis fails.
        
        Args:
            reason: Reason for the fallback
            
        Returns:
            Safe fallback WellnessAnalysis
        """
        logger.warning(f"Using fallback analysis: {reason}")
        return WellnessAnalysis(
            mood=0.0,
            priority="low",
            emergency=False,
            suggestions=["Sorry — I couldn't analyze that. Try rephrasing your message."],
            follow_up_days=0,
            explanation=f"Analysis temporarily unavailable: {reason}"
        )

    def _local_analyze(self, text: str) -> WellnessAnalysis:
        """
        Simple local heuristic analysis used when OpenAI is unavailable or disabled.
        """
        t = text.lower()

        emergency_keywords = [
            "chest pain", "difficulty breathing", "can't breathe", "suicidal",
            "suicide", "kill myself", "overdose", "fainted", "loss of consciousness",
            "severe bleeding", "stroke", "emergency"
        ]

        negative_markers = [
            "tired", "sad", "depressed", "anxious", "anxiety", "stressed",
            "pain", "hurt", "insomnia", "can't sleep", "no sleep", "sick",
            "headache", "migraine", "fatigue", "lonely", "alone"
        ]
        positive_markers = ["good", "great", "happy", "better", "fine", "okay", "ok", "energized"]

        emergency = any(k in t for k in emergency_keywords)

        sentiment = 0
        sentiment += sum(t.count(w) for w in positive_markers)
        sentiment -= sum(t.count(w) for w in negative_markers)
        mood = max(-1.0, min(1.0, sentiment / 5.0))

        if emergency:
            priority = "high"
        else:
            if mood <= -0.3:
                priority = "high"
            elif mood <= 0.2:
                priority = "medium"
            else:
                priority = "low"

        # Symptom-specific suggestions
        suggestions: list[str] = []
        if emergency:
            suggestions.append("If you are in immediate danger, call emergency services now.")

        if any(w in t for w in ["sleep", "insomnia", "can't sleep", "no sleep", "tired", "fatigue"]):
            suggestions.append("Set a wind‑down: dim lights, no screens 60 min before bed.")
            suggestions.append("Try a 10‑minute relaxation (box breathing 4‑4‑4‑4).")

        if any(w in t for w in ["anxiety", "anxious", "panic", "overwhelmed", "stress", "stressed"]):
            suggestions.append("Do 5 slow breaths (inhale 4s, exhale 6s) to calm the body.")
            suggestions.append("Jot down top 3 worries and one tiny next step for each.")

        if any(w in t for w in ["headache", "migraine"]):
            suggestions.append("Hydrate now and rest your eyes 5 minutes away from screens.")

        if any(w in t for w in ["pain", "hurt", "sore"]):
            suggestions.append("Try gentle stretching and avoid heavy activity for the day.")

        if any(w in t for w in ["sad", "depressed", "lonely", "alone"]):
            suggestions.append("Send a short check‑in message to someone you trust today.")

        if any(w in t for w in ["diet", "junk", "sugar", "ate too much", "overeat"]):
            suggestions.append("Plan your next meal: protein + fiber + water before eating.")

        if any(w in t for w in ["thirsty", "dehydrated", "dry mouth"]):
            suggestions.append("Drink a full glass of water now; keep a bottle nearby.")

        if not suggestions:
            suggestions.append("Take a micro‑break: hydrate, stretch, and 3 deep breaths.")

        # De‑duplicate while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)

        follow_up_days = 0
        if priority == "high":
            follow_up_days = 1
        elif priority == "medium":
            follow_up_days = 3

        explanation = (
            "Local analysis based on keywords and sentiment markers. "
            + ("Emergency indicators detected. " if emergency else "")
            + f"Estimated mood {mood:.1f}, priority {priority}."
        )

        return WellnessAnalysis(
            mood=mood,
            priority=priority,
            emergency=emergency,
            suggestions=unique_suggestions[:3],
            follow_up_days=follow_up_days,
            explanation=explanation,
        )
