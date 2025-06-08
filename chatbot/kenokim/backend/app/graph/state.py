from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """에이전트 간에 공유되는 대화 상태를 정의합니다."""
    
    # 메시지 히스토리
    messages: List[BaseMessage]
    
    # 현재 처리할 사용자 입력
    current_input: str
    
    # 다음에 호출할 에이전트 (Supervisor가 결정)
    next: Optional[str]
    
    # 현재 활성화된 에이전트
    current_agent: Optional[str]
    
    # 작업 완료 여부
    is_finished: bool
    
    # 에이전트 간 컨텍스트 공유를 위한 메타데이터
    metadata: Dict[str, Any]
    
    # 스레드 ID (세션 관리용)
    thread_id: Optional[str] 