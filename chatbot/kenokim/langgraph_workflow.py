"""LangGraph 기반 챗봇 워크플로우

이 모듈은 LangGraph를 사용하여 상태 기반의 대화형 워크플로우를 구현합니다.
"""

import os
from typing import Dict, List, Any, TypedDict, Optional, Union, Callable
from langgraph.graph import StateGraph, END
from api.client import VertexAIClient
from PIL import Image
import io

# 상태 타입 정의
class ChatState(TypedDict):
    """챗봇 상태 타입 정의"""
    messages: List[Dict[str, Any]]  # 채팅 이력
    current_input: str              # 현재 사용자 입력
    response: str                   # 현재 응답
    dashboard_mode: bool            # 대시보드 모드 여부
    error: str                      # 오류 메시지
    images: List[Dict[str, Any]]    # 이미지 리스트

# 전역 변수 - API 클라이언트
client = VertexAIClient()

def create_initial_state() -> ChatState:
    """초기 상태 생성 함수"""
    return {
        "messages": [],
        "current_input": "",
        "response": "",
        "dashboard_mode": False,
        "error": "",
        "images": []
    }

# strangekino.png 이미지를 로드하는 함수
def load_strangekino_image() -> bytes:
    """strangekino.png 이미지를 로드합니다."""
    # 현재 스크립트의 디렉토리 위치 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 이미지 경로 지정
    image_path = os.path.join(current_dir, "strangekino.png")
    
    try:
        # 이미지 파일 열기
        with open(image_path, "rb") as f:
            return f.read()
    except Exception as e:
        print(f"이미지 로드 오류: {str(e)}")
        # 오류 발생 시 빈 이미지 반환
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        return img_bytes.getvalue()

# 워크플로우 노드 함수들
def process_input(state: ChatState) -> Dict:
    """사용자 입력 처리 및 모드 결정"""
    try:
        # 현재 입력에서 대시보드 키워드 감지
        is_dashboard_request = any(
            keyword in state["current_input"].lower() 
            for keyword in ["대시보드", "차트", "그래프", "보여줘"]
        )
        
        # 메시지 이력 업데이트
        messages = state["messages"].copy()
        messages.append({"role": "user", "content": state["current_input"]})
        
        return {
            "messages": messages,
            "dashboard_mode": is_dashboard_request
        }
    except Exception as e:
        return {"error": f"입력 처리 오류: {str(e)}"}

def generate_llm_response(state: ChatState) -> Dict:
    """Gemini 모델로 응답 생성"""
    try:
        # 모델 호출을 위한 메시지 준비
        messages = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in state["messages"] 
            if "role" in msg and "content" in msg
        ]
        
        # API 클라이언트를 통해 응답 생성
        response = client.chat(messages)
        
        if response["status"] == "success":
            return {"response": response["content"]}
        else:
            return {"error": response.get("error_message", "응답 생성 실패")}
            
    except Exception as e:
        return {"error": f"응답 생성 오류: {str(e)}"}

def update_messages(state: ChatState) -> Dict:
    """메시지 이력 업데이트"""
    messages = state["messages"].copy()
    messages.append({"role": "assistant", "content": state["response"]})
    return {"messages": messages}

def create_dashboard_response(state: ChatState) -> Dict:
    """대시보드 응답 생성"""
    
    # strangekino.png 이미지 로드
    image_data = load_strangekino_image()
    
    # 응답 메시지
    response = "여기 스트레인지 키노 이미지입니다! 🌟"
    
    # 메시지 업데이트
    messages = state["messages"].copy()
    messages.append({
        "role": "assistant", 
        "content": response,
        "is_dashboard": True
    })
    
    # 이미지 정보 저장
    images = state.get("images", []).copy()
    images.append({
        "data": image_data,
        "caption": "스트레인지 키노",
        "message_index": len(messages) - 1  # 연결된 메시지 인덱스
    })
    
    return {
        "messages": messages, 
        "response": response,
        "images": images
    }

def handle_error(state: ChatState) -> Dict:
    """오류 처리"""
    error_message = state.get("error", "알 수 없는 오류가 발생했습니다.")
    response = f"죄송합니다. 오류가 발생했습니다: {error_message}"
    
    # 메시지 업데이트
    messages = state["messages"].copy()
    messages.append({"role": "assistant", "content": response})
    
    return {"messages": messages, "response": response}

# 그래프 구성 함수
def create_chat_workflow() -> StateGraph:
    """챗봇 워크플로우 그래프 생성"""
    # 상태 그래프 생성
    workflow = StateGraph(ChatState)
    
    # 노드 추가
    workflow.add_node("process_input", process_input)
    workflow.add_node("generate_llm_response", generate_llm_response)
    workflow.add_node("update_messages", update_messages)
    workflow.add_node("create_dashboard", create_dashboard_response)
    workflow.add_node("handle_error", handle_error)
    
    # 에지 추가 (조건부 라우팅)
    
    # 프로세스 입력 후 대시보드 모드 또는 에러 발생 여부에 따라 라우팅
    workflow.add_conditional_edges(
        "process_input",
        lambda state: "handle_error" if state.get("error") else
                     "create_dashboard" if state.get("dashboard_mode") else
                     "generate_llm_response"
    )
    
    # LLM 응답 생성 후 에러 발생 여부에 따라 라우팅
    workflow.add_conditional_edges(
        "generate_llm_response",
        lambda state: "handle_error" if state.get("error") else "update_messages"
    )
    
    # 나머지 에지 연결
    workflow.add_edge("update_messages", END)
    workflow.add_edge("create_dashboard", END)
    workflow.add_edge("handle_error", END)
    
    # 시작점 설정
    workflow.set_entry_point("process_input")
    
    return workflow

# 워크플로우 인스턴스 생성 및 컴파일
chat_workflow = create_chat_workflow()
chat_chain = chat_workflow.compile()

# 워크플로우 실행 헬퍼 함수
def process_message(message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """메시지 처리 함수
    
    Args:
        message: 사용자 메시지
        history: 이전 대화 이력 (없으면 빈 리스트)
        
    Returns:
        처리 결과 (메시지, 응답, 이미지 등)
    """
    # 초기 상태 생성
    state = create_initial_state()
    
    # 이전 이력 설정
    state["messages"] = history or []
    
    # 현재 메시지 설정
    state["current_input"] = message
    
    # 워크플로우 실행
    result = chat_chain.invoke(state)
    
    return result 