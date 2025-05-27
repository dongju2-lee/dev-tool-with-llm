from enum import Enum


# API response keys
class Response(str, Enum):
    MESSAGE = "message"
    SESSION_ID = "session_id"
    RESPONSE = "response"


# Session state keys
class SessionState(str, Enum):
    SESSION_ID = "session_id"
    MESSAGES = "messages"


class Request(str, Enum):
    MESSAGE = "message"
    SESSION_ID = "session_id"
    AGENT_MODE = "agent_mode"