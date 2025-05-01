"""Gemini API 클라이언트

이 모듈은 Google AI Studio의 Gemini API를 사용하여 텍스트 생성을 수행합니다.
"""

import os
from typing import Dict, List, Any, Optional
import requests
from dotenv import load_dotenv
import logging

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiClient:
    """Google AI Studio Gemini API 클라이언트"""
    
    # Google AI Studio 엔드포인트
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, api_key: Optional[str] = None,
                 model_name: str = "gemini-2.0-flash"):
        """Gemini 클라이언트 초기화
        
        Args:
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
            model_name: 사용할 Gemini 모델명
        """
        # 환경변수에서 값 로드 (인자가 없는 경우)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        # 필수 값 확인
        if not self.api_key:
            raise ValueError("API 키(GEMINI_API_KEY)가 설정되어 있지 않습니다. .env 파일이나 환경변수에 설정해주세요.")
        
        # 모델 초기화
        self.model_name = model_name
        logger.info(f"Gemini 클라이언트 초기화 완료 (모델: {self.model_name})")
    
    def generate_content(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Gemini 모델로 텍스트 생성
        
        Args:
            prompt: 입력 텍스트
            **kwargs: 추가 모델 매개변수
            
        Returns:
            응답 텍스트와 메타데이터를 포함한 딕셔너리
        """
        try:
            logger.info(f"콘텐츠 생성 요청: 길이={len(prompt)} (모델: {self.model_name})")
            
            # 요청 URL 구성
            # https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash
            url = f"{self.BASE_URL}/models/{self.model_name}:generateContent?key={self.api_key}"
            
            # 요청 본문 구성
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # 추가 파라미터 처리
            if "temperature" in kwargs:
                data["generationConfig"] = data.get("generationConfig", {})
                data["generationConfig"]["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs or "maxOutputTokens" in kwargs:
                data["generationConfig"] = data.get("generationConfig", {})
                data["generationConfig"]["maxOutputTokens"] = kwargs.get("max_tokens", kwargs.get("maxOutputTokens", 1024))
            
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
            
            logger.info("응답 수신 성공")
            return {
                "content": text,
                "status": "success",
                "model": self.model_name
            }
        except Exception as e:
            logger.error(f"콘텐츠 생성 오류: {str(e)}")
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
            logger.info(f"채팅 요청: 메시지 수={len(messages)} (모델: {self.model_name})")
            
            # 요청 URL 구성
            url = f"{self.BASE_URL}/models/{self.model_name}:generateContent?key={self.api_key}"
            
            # 대화 이력을 Gemini API 형식으로 변환
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
            
            # 나머지 대화 이력 추가
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                content = {
                    "role": role,
                    "parts": [
                        {
                            "text": msg.get("content", "")
                        }
                    ]
                }
                contents.append(content)
            
            # 요청 본문 구성
            data = {
                "contents": contents,
                "generationConfig": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "maxOutputTokens": kwargs.get("max_tokens", 1024),
                    "topP": kwargs.get("top_p", 0.9),
                    "topK": kwargs.get("top_k", 40)
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
            
            logger.info("채팅 응답 수신 성공")
            return {
                "content": text,
                "status": "success",
                "model": self.model_name
            }
        except Exception as e:
            logger.error(f"채팅 오류: {str(e)}")
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
            logger.info(f"API 상태 확인 (모델: {self.model_name})")
            
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
            
            logger.info("API 온라인 확인")
            return {
                "status": "online",
                "model": self.model_name,
                "available_models": available_models,
                "version": "1.0.0"
            }
        except Exception as e:
            logger.error(f"API 상태 확인 오류: {str(e)}")
            return {
                "status": "offline",
                "error": str(e)
            }


class MCPClient:
    """MCP(Model Context Protocol) 인터페이스와 호환되는 클라이언트
    
    이 클래스는 기존 MCPClient와 호환성을 유지하면서 내부적으로 GeminiClient를 사용합니다.
    """
    
    def __init__(self, model_name: str = "gemini-pro"):
        """MCPClient 초기화
        
        Args:
            model_name: 사용할 Gemini 모델명 (기본값: "gemini-pro")
        """
        # GeminiClient 인스턴스 생성
        try:
            self.gemini_client = GeminiClient(model_name=model_name)
            logger.info(f"MCPClient 초기화 성공 (모델: {model_name})")
        except Exception as e:
            logger.error(f"MCPClient 초기화 오류: {str(e)}")
            raise
        
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
        
        logger.info(f"쿼리 처리: '{query[:30]}...' (메시지 수: {len(messages)})")
        
        # Gemini 클라이언트로 응답 생성
        response = self.gemini_client.chat(messages)
        
        # 응답을 기존 MCPClient 형식으로 변환
        if response["status"] == "success":
            # 응답 메시지 추가
            messages.append({"role": "assistant", "content": response["content"]})
            
            logger.info("쿼리 처리 성공")
            return {
                "response": response["content"],
                "messages": messages,
                "status": "success",
                "model": self.gemini_client.model_name
            }
        else:
            logger.error(f"쿼리 처리 오류: {response.get('error_message', '알 수 없는 오류')}")
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
        return self.gemini_client.check_status() 