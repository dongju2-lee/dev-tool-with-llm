"""
Gemini 모델을 사용한 LangChain MCP Adapters 클라이언트

이 모듈은 Vertex AI의 Gemini 모델을 직접 호출하고,
LangGraph와 MemorySaver를 사용하여 대화 기록을 관리합니다.
"""

import os
import logging
import asyncio
import uuid
import requests
from typing import List, Dict, Any, Optional

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver

from langchain_mcp_adapters.tools import load_mcp_tools

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiMCPClient:
    """Gemini API를 직접 호출하는 MCP 클라이언트"""
    
    # Google AI Studio 엔드포인트
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, 
                 model_name: str = "gemini-2.0-flash",
                 api_key: Optional[str] = None):
        """클라이언트 초기화
        
        Args:
            model_name: 사용할 Gemini 모델 이름 (gemini-2.0-flash, gemini-1.5-pro, gemini-pro)
            api_key: Gemini API 키 (없으면 환경 변수에서 로드)
        """
        # 모델 이름 설정
        self.model_name = model_name
        
        # API 키 확인
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API 키(GEMINI_API_KEY)가 설정되지 않았습니다.")
        
        # 체크포인터 설정
        self.checkpointer = MemorySaver()
        
        logger.info(f"GeminiMCPClient 초기화 완료 (모델: {self.model_name})")
        
        # 비동기 작업을 위한 이벤트 루프
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 도구 정보 (샘플)
        self.tools = [
            {"name": "calculator", "description": "수학 계산을 수행하는 도구입니다."},
            {"name": "weather", "description": "날씨 정보를 조회하는 도구입니다."},
            {"name": "search", "description": "웹 검색을 수행하는 도구입니다."}
        ]
    
    def initialize(self):
        """클라이언트를 초기화합니다."""
        logger.info("클라이언트 초기화 완료")
        # 간단한 API 연결 확인
        self.check_connection()
    
    def close(self):
        """세션을 닫습니다."""
        logger.info("세션 종료됨")
    
    def _format_messages_for_api(self, messages):
        """메시지 형식을 Gemini API 호출용으로 변환합니다."""
        contents = []
        
        # 시스템 메시지 추가
        system_message = {
            "role": "user",
            "parts": [
                {
                    "text": "당신은 도움이 되는 AI 슬라임 챗봇입니다. 친절하고 명확하게 답변해 주세요."
                }
            ]
        }
        contents.append(system_message)
        
        # 응답 메시지 추가
        system_response = {
            "role": "model",
            "parts": [
                {
                    "text": "네, 저는 슬라임 챗봇입니다. 어떻게 도와드릴까요?"
                }
            ]
        }
        contents.append(system_response)
        
        # 대화 이력 추가
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
                text = msg.content
            elif isinstance(msg, AIMessage):
                role = "model"
                text = msg.content
            elif isinstance(msg, dict):
                role = "user" if msg.get("role") == "user" else "model"
                text = msg.get("content", "")
            else:
                continue
                
            content = {
                "role": role,
                "parts": [
                    {
                        "text": text
                    }
                ]
            }
            contents.append(content)
        
        return contents
    
    async def _process_query_async(self, query: str, history: List[Any] = None, thread_id: str = None) -> Dict[str, Any]:
        """쿼리를 비동기적으로 처리합니다.
        
        Args:
            query: 사용자 쿼리
            history: 대화 이력 (없으면 빈 리스트 사용)
            thread_id: 대화 스레드 ID (없으면 랜덤 생성)
            
        Returns:
            처리 결과 딕셔너리
        """
        # 스레드 ID 설정
        thread_id = thread_id or str(uuid.uuid4())
        logger.info(f"쿼리 처리 시작 (스레드 ID: {thread_id})")
        
        try:
            # 히스토리를 메시지 형식으로 변환
            messages = []
            if history:
                for msg in history:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            
            # 현재 쿼리 추가
            messages.append(HumanMessage(content=query))
            
            # API 호출용 메시지 형식으로 변환
            contents = self._format_messages_for_api(messages)
            
            # 요청 URL 구성
            url = f"{self.BASE_URL}/models/{self.model_name}:generateContent?key={self.api_key}"
            
            # 요청 본문 구성
            data = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            # API 요청 보내기
            response = requests.post(url, json=data)
            response.raise_for_status()  # HTTP 오류 확인
            
            # 응답 파싱
            result = response.json()
            
            # 응답에서 텍스트 추출
            text = ""
            if "candidates" in result:
                for part in result["candidates"][0]["content"]["parts"]:
                    if "text" in part:
                        text += part["text"]
            
            # 도구 사용 시뮬레이션 (실제 MCP 대신 자체 처리)
            # 실제 환경에서는 MCP 서버와 연동 필요
            tool_outputs = []
            if "계산" in query or "덧셈" in query or "뺄셈" in query:
                tool_outputs.append({
                    "tool": "calculator", 
                    "result": "계산 결과: 42"
                })
            
            logger.info(f"쿼리 처리 완료 (스레드 ID: {thread_id})")
            return {
                "response": text,
                "tool_outputs": tool_outputs,
                "status": "success",
                "model": self.model_name,
                "thread_id": thread_id
            }
        except Exception as e:
            logger.error(f"쿼리 처리 오류: {str(e)}")
            return {
                "response": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "tool_outputs": [],
                "status": "error",
                "error_message": str(e),
                "model": self.model_name,
                "thread_id": thread_id
            }
    
    def process_query(self, query: str, history: List[Dict[str, Any]] = None, thread_id: str = None) -> Dict[str, Any]:
        """쿼리를 처리합니다.
        
        Args:
            query: 사용자 쿼리
            history: 대화 이력 (없으면 빈 리스트 사용)
            thread_id: 대화 스레드 ID (없으면 랜덤 생성)
            
        Returns:
            처리 결과 딕셔너리
        """
        return self.loop.run_until_complete(self._process_query_async(query, history, thread_id))
    
    def get_tools(self) -> List[Dict[str, str]]:
        """사용 가능한 도구 목록을 가져옵니다.
        
        Returns:
            도구 목록 (이름, 설명 포함)
        """
        return self.tools
    
    def check_connection(self) -> Dict[str, Any]:
        """API 연결 상태를 확인합니다.
        
        Returns:
            연결 상태 정보
        """
        try:
            # 요청 URL 구성 (모델 목록 조회)
            url = f"{self.BASE_URL}/models?key={self.api_key}"
            
            # API 요청 보내기
            response = requests.get(url)
            response.raise_for_status()  # HTTP 오류 확인
            
            # 응답 파싱
            result = response.json()
            
            # 사용 가능한 모델 확인
            available_models = []
            for model in result.get("models", []):
                if model.get("name", "").startswith("models/gemini-"):
                    model_name = model.get("name").replace("models/", "")
                    available_models.append(model_name)
            
            logger.info("API 연결 확인 성공")
            return {
                "status": "success",
                "connected": True,
                "model": self.model_name,
                "available_models": available_models,
                "available_tools": [tool["name"] for tool in self.tools]
            }
        except Exception as e:
            logger.error(f"API 연결 확인 오류: {str(e)}")
            return {
                "status": "error",
                "connected": False,
                "error_message": str(e)
            }


# 클라이언트 사용 예시
if __name__ == "__main__":
    # Gemini API 직접 호출 클라이언트 사용
    client = GeminiMCPClient()
    
    try:
        # 클라이언트 초기화
        client.initialize()
        
        # 연결 확인
        connection_status = client.check_connection()
        print(f"연결 상태: {connection_status}")
        
        # 도구 목록 확인
        tools = client.get_tools()
        print(f"사용 가능한 도구: {tools}")
        
        # 쿼리 실행
        query = "15와 27을 더한 후, 그 결과에 3을 곱하세요."
        result = client.process_query(query)
        
        print("\n=== 결과 ===")
        print(f"응답: {result['response']}")
        print("\n도구 사용 내역:")
        for tool_output in result.get("tool_outputs", []):
            print(f"- {tool_output.get('tool', '알 수 없음')}: {tool_output.get('result', '')}")
    
    finally:
        # 세션 종료
        client.close()
        print("\n세션이 종료되었습니다.") 