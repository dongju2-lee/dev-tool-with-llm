"""
State management enums for the GitHub Issue Assistant Bot.
"""
from enum import Enum

class SessionState(Enum):
    """Enum for session state keys in Streamlit."""
    MESSAGES = "messages"
    SESSION_ID = "session_id"

class Response(Enum):
    """Enum for response keys from the API."""
    RESPONSE = "response"
    SESSION_ID = "session_id"
    SUCCESS = "success"
    METADATA = "metadata" 