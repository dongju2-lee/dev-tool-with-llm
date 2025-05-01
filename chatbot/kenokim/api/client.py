"""Vertex AI Gemini API 클라이언트

이 모듈은 Google Vertex AI의 Gemini 모델을 활용하는 클라이언트를 제공합니다.
"""

import os
from typing import Dict, List, Any, Optional, Union
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from dotenv import load_dotenv

class VertexAIClient:
    """Vertex AI Gemini API 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None, 
                 project_id: Optional[str] = None,
                 location: Optional[str] = None,
                 model_name: str = "gemini-pro"):
        """Vertex AI 클라이언트 초기화
        
        Args:
            api_key: Vertex AI API 키 (없으면 환경변수에서 로드)
            project_id: Google Cloud 프로젝트 ID (없으면 환경변수에서 로드)
            location: Vertex AI 모델 위치 (없으면 환경변수에서 로드)
            model_name: 사용할 Gemini 모델명
        """
        # .env 파일 로드
        load_dotenv()
        
        # 환경변수에서 값 로드 (인자가 없는 경우)
        self.api_key = api_key or os.getenv("VERTEX_API_KEY")
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location or os.getenv("VERTEX_AI_LOCATION", "us-central1")
        
        # 필수 값 확인
        if not self.project_id:
            raise ValueError("project_id 또는 GCP_PROJECT_ID 환경변수가 필요합니다")
        
        # API 키 방식 또는 서비스 계정 키 방식 결정
        if self.api_key:
            # API 키 방식 초기화
            vertexai.init(project=self.project_id, location=self.location, api_key=self.api_key)
        else:
            # 서비스 계정 인증 방식 (환경변수 GOOGLE_APPLICATION_CREDENTIALS 필요)
            vertexai.init(project=self.project_id, location=self.location)
        
        # 모델 초기화
        self.model_name = model_name
        self.model = GenerativeModel(self.model_name)
    
    def generate_content(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Gemini 모델로 텍스트 생성
        
        Args:
            prompt: 입력 텍스트
            **kwargs: 추가 모델 매개변수
            
        Returns:
            응답 텍스트와 메타데이터를 포함한 딕셔너리
        """
        try:
            response = self.model.generate_content(prompt, **kwargs)
            return {
                "content": response.text,
                "status": "success",
                "model": self.model_name
            }
        except Exception as e:
            return {
                "content": f"오류 발생: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """대화 형식으로 메시지 전송
        
        Args:
            messages: 대화 이력 (역할과 내용을 포함한 메시지 리스트)
            **kwargs: 추가 모델 매개변수
            
        Returns:
            응답 텍스트와 메타데이터를 포함한 딕셔너리
        """
        try:
            # 메시지 포맷 구성
            prompt = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt += f"사용자: {content}\n"
                elif role == "assistant":
                    prompt += f"AI: {content}\n"
                else:
                    prompt += f"{role}: {content}\n"
            
            # 모델에 전송할 시스템 프롬프트 추가
            system_prompt = "당신은 도움이 되는 AI 슬라임 챗봇입니다. 친절하고 명확하게 답변해 주세요."
            full_prompt = f"{system_prompt}\n\n{prompt}AI: "
            
            # 응답 생성
            response = self.model.generate_content(full_prompt, **kwargs)
            
            return {
                "content": response.text,
                "status": "success",
                "model": self.model_name
            }
        except Exception as e:
            return {
                "content": f"오류 발생: {str(e)}",
                "status": "error",
                "error_message": str(e)
            }
    
    def check_status(self) -> Dict[str, Any]:
        """API 연결 상태 확인
        
        Returns:
            상태 정보를 포함한 딕셔너리
        """
        try:
            # 간단한 쿼리로 API 연결 테스트
            response = self.model.generate_content("Hello")
            return {
                "status": "online",
                "model": self.model_name,
                "version": "1.0.0"
            }
        except Exception as e:
            return {
                "status": "offline",
                "error": str(e)
            } 


class MCPClient:
    """MCP(Model Context Protocol) 인터페이스와 호환되는 클라이언트
    
    이 클래스는 기존 MCPClient와 호환성을 유지하면서 내부적으로 VertexAIClient를 사용합니다.
    """
    
    def __init__(self):
        """MCPClient 초기화"""
        # VertexAIClient 인스턴스 생성
        self.vertex_client = VertexAIClient()
        
    def process_query(self, query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """사용자 쿼리 처리
        
        Args:
            query: 사용자 입력 메시지
            history: 이전 대화 이력 (없으면 빈 리스트)
            
        Returns:
            처리 결과 (메시지, 응답 등)
        """
        # 대화 이력 준비
        messages = history or []
        messages.append({"role": "user", "content": query})
        
        # Vertex AI 클라이언트로 응답 생성
        response = self.vertex_client.chat(messages)
        
        # 응답을 기존 MCPClient 형식으로 변환
        if response["status"] == "success":
            # 응답 메시지 추가
            messages.append({"role": "assistant", "content": response["content"]})
            
            return {
                "response": response["content"],
                "messages": messages,
                "status": "success"
            }
        else:
            return {
                "response": "죄송합니다. 오류가 발생했습니다: " + response.get("error_message", "알 수 없는 오류"),
                "messages": messages,
                "status": "error"
            }
    
    def check_connection(self) -> Dict[str, Any]:
        """MCPClient 연결 상태 확인
        
        Returns:
            상태 정보를 포함한 딕셔너리
        """
        return self.vertex_client.check_status() 