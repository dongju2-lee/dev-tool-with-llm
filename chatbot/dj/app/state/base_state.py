"""
기본 상태 클래스 정의
"""

from typing import TypedDict, List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    """태스크 상태를 나타내는 열거형"""
    planning = "planning"
    executing = "executing"
    validating = "validating"
    responding = "responding"
    completed = "completed"
    failed = "failed"

class AgentRequest(BaseModel):
    """에이전트에 대한 요청을 나타내는 모델"""
    query: str
    context: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    """에이전트의 응답을 나타내는 모델"""
    content: str
    raw_data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None

class TaskStep(BaseModel):
    """태스크 단계를 나타내는 모델"""
    description: str
    agent: str
    status: TaskStatus = TaskStatus.planning
    request: Optional[AgentRequest] = None
    response: Optional[AgentResponse] = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    dependencies: List[int] = Field(default_factory=list)

class ValidationResult(BaseModel):
    """검증 결과를 나타내는 모델"""
    is_complete: bool
    feedback: str
    missing_information: Optional[List[str]] = None
    suggested_agents: Optional[List[str]] = None

class MessagesState(TypedDict):
    """메시지 상태와 작업 관련 정보를 포함하는 상태 클래스"""
    messages: List[Dict]
    original_query: str
    parsed_intent: Optional[Dict[str, Any]]
    plan: Optional[List[TaskStep]]
    current_step: Optional[int]
    results: Dict[str, Any]
    validation_result: Optional[ValidationResult]
    final_response: Optional[str]
    conversation_context: Dict[str, Any]
    status: TaskStatus
    next: Optional[str]  # 라우팅을 위한 다음 노드 정보

class EnhancedState(MessagesState):
    """확장된 상태 클래스, 메시지 상태와 작업 관련 정보를 모두 포함"""
    pass 