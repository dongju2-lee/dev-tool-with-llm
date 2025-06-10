from typing import Annotated, Optional, Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(Enum):
    ROUTER = "router"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    VISUALIZATION = "visualization"
    SYNTHESIZER = "synthesizer"


class TaskContext(TypedDict):
    """개별 작업의 컨텍스트"""
    task_id: str
    agent_type: AgentType
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int


class AgentMemory(TypedDict):
    """에이전트별 메모리"""
    agent_id: str
    conversations: List[BaseMessage]
    tools_used: List[str]
    performance_metrics: Dict[str, Any]
    learned_patterns: List[Dict[str, Any]]


# Enhanced Graph State for Multi-Agent System
class EnhancedGraphState(TypedDict):
    """LangGraph Enhanced State schema for Multi-Agent workflows"""
    
    # Core message flow
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Request metadata
    user_query: str
    intent_classification: Optional[str]
    urgency_level: int  # 1-5 scale
    
    # Routing information
    current_agent: Optional[AgentType]
    next_agent: Optional[AgentType]
    agent_routing_history: Annotated[List[str], lambda x, y: x + [y] if y not in x[-3:] else x]
    
    # Task management
    active_tasks: Annotated[List[TaskContext], lambda x, y: x + [y]]
    completed_tasks: List[TaskContext]
    
    # Data flow between agents
    shared_context: Dict[str, Any]
    intermediate_results: Dict[str, Any]
    final_results: Dict[str, Any]
    
    # Error handling and recovery
    errors: List[Dict[str, Any]]
    retry_stack: List[str]
    fallback_options: List[str]
    
    # Performance and monitoring
    execution_timeline: List[Dict[str, Any]]
    resource_usage: Dict[str, Any]
    
    # Agent-specific memory (subgraph states)
    agent_memories: Dict[str, AgentMemory]
    
    # Response enhancement
    response_quality_score: Optional[float]
    confidence_level: Optional[float]
    image_data: Optional[str]
    
    # Session management
    session_id: Optional[str]
    user_preferences: Dict[str, Any]


# Subgraph States for specialized agents
class MonitoringTeamState(TypedDict):
    """모니터링 팀 전용 state"""
    messages: Annotated[List[BaseMessage], add_messages]
    metrics_data: Dict[str, Any]
    alert_level: int
    time_range: Dict[str, str]
    dashboards_checked: List[str]


class AnalysisTeamState(TypedDict):
    """분석 팀 전용 state"""
    messages: Annotated[List[BaseMessage], add_messages]
    analysis_type: str  # "performance", "trend", "anomaly"
    data_sources: List[str]
    analysis_results: Dict[str, Any]
    recommendations: List[str]


class VisualizationTeamState(TypedDict):
    """시각화 팀 전용 state"""
    messages: Annotated[List[BaseMessage], add_messages]
    chart_type: str
    dashboard_uid: Optional[str]
    render_config: Dict[str, Any]
    output_format: str  # "image", "json", "html"
    generated_assets: List[Dict[str, Any]]


# 이전 호환성을 위한 별칭
GraphState = EnhancedGraphState
AgentState = EnhancedGraphState


# Utility functions for state management
def create_task_context(
    task_id: str,
    agent_type: AgentType,
    input_data: Dict[str, Any]
) -> TaskContext:
    """새로운 작업 컨텍스트 생성"""
    return TaskContext(
        task_id=task_id,
        agent_type=agent_type,
        status=TaskStatus.PENDING,
        created_at=datetime.now(),
        completed_at=None,
        input_data=input_data,
        output_data=None,
        error_message=None,
        retry_count=0
    )


def update_task_status(
    state: EnhancedGraphState,
    task_id: str,
    status: TaskStatus,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> EnhancedGraphState:
    """작업 상태 업데이트"""
    for task in state["active_tasks"]:
        if task["task_id"] == task_id:
            task["status"] = status
            if output_data:
                task["output_data"] = output_data
            if error_message:
                task["error_message"] = error_message
            if status == TaskStatus.COMPLETED:
                task["completed_at"] = datetime.now()
                state["completed_tasks"].append(task)
                state["active_tasks"] = [t for t in state["active_tasks"] if t["task_id"] != task_id]
            break
    return state 