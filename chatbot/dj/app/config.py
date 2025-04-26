"""
Configuration settings and constants for the GitHub Issue Assistant Bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Settings
CHATBOT_API_URL = os.environ.get("CHATBOT_API_URL", "http://agent:8000")
CHAT_ENDPOINT = "/chat"

# Error Messages
ERROR_SERVER_CONNECTION = "Error connecting to server: {}"
ERROR_JSON_DECODE = "Error decoding JSON response: {}"
ERROR_NO_RESPONSE = "Failed to get a valid response from the server"

# UI Messages
PROCESSING_MESSAGE = "Processing your request..."
CHAT_INPUT_PLACEHOLDER = "Enter your message here..."
APP_TITLE = "Github Issue Assistant Bot"

# Status Messages
STATUS_COMPLETE = "✅ Complete"
STATUS_ERROR = "❌ Error"

# Session Management Messages
SESSION_NEW = "New session created with ID: {}"
SESSION_UPDATED = "Session ID updated: {}"
SESSION_CURRENT = "Current Session ID: {}"
SESSION_NONE = "No active session"

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Application Settings
PORT = int(os.environ.get("PORT", "8501"))
HOST = os.environ.get("HOST", "0.0.0.0") 