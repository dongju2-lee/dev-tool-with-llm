import requests
import os
from typing import Dict, List, Any, Optional

class MCPClient:
    def __init__(self, base_url: Optional[str] = None):
        """MCP 클라이언트 초기화"""
        self.base_url = base_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8000")
        self.headers = {"Content-Type": "application/json"}
    
    def check_status(self) -> Dict[str, Any]:
        """서버 상태 확인"""
        response = requests.get(f"{self.base_url}/status", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def send_message(
        self, 
        message: str, 
        thread_id: Optional[str] = None,
        context: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """메시지 전송"""
        payload = {
            "message": message,
            "thread_id": thread_id,
            "context": context or [],
            "stream": stream
        }
        
        response = requests.post(
            f"{self.base_url}/chat", 
            json=payload, 
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_threads(self) -> Dict[str, Any]:
        """모든 스레드 목록 조회"""
        response = requests.get(f"{self.base_url}/threads", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def create_thread(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """새 스레드 생성"""
        payload = {"metadata": metadata or {}}
        response = requests.post(
            f"{self.base_url}/threads", 
            json=payload, 
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_thread_messages(self, thread_id: str) -> Dict[str, Any]:
        """특정 스레드의 메시지 조회"""
        response = requests.get(
            f"{self.base_url}/threads/{thread_id}/messages", 
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """도구 실행"""
        payload = {
            "tool_name": tool_name,
            "parameters": parameters,
            "thread_id": thread_id
        }
        response = requests.post(
            f"{self.base_url}/tools/execute", 
            json=payload, 
            headers=self.headers
        )
        response.raise_for_status()
        return response.json() 