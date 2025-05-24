"""
애플리케이션 구성 모듈

전역 상수와 구성 값을 정의합니다.
"""

import os
import logging
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    LOG_LEVEL = "INFO"
LOG_LEVEL = getattr(logging, LOG_LEVEL)

# 에이전트 모델 설정
DEFAULT_MODEL = "gemini-2.0-flash"
SUPERVISOR_MODEL = os.environ.get("SUPERVISOR_MODEL", DEFAULT_MODEL)
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", DEFAULT_MODEL)
PLANNING_MODEL = os.environ.get("PLANNING_MODEL", DEFAULT_MODEL)
VALIDATION_MODEL = os.environ.get("VALIDATION_MODEL", DEFAULT_MODEL)
RESPOND_MODEL = os.environ.get("RESPOND_MODEL", DEFAULT_MODEL)
WEATHER_AGENT_MODEL = os.environ.get("WEATHER_AGENT_MODEL", DEFAULT_MODEL)

# 에이전트 구성
MAX_PLANNING_STEPS = 5
MAX_ITERATIONS = 10
DEFAULT_TEMPERATURE = 0.2
PLANNING_TEMPERATURE = 0.3
CREATIVITY_TEMPERATURE = 0.7

# API 키 및 인증 정보
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID", "")

# 애플리케이션 설정
APP_PORT = int(os.environ.get("PORT", 8001))
DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() == "true"
ENABLE_LOGGING = os.environ.get("ENABLE_LOGGING", "True").lower() == "true"

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

# Application Settings
HOST = os.environ.get("HOST", "0.0.0.0") 