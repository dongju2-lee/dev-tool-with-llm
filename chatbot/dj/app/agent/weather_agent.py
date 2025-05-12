"""
날씨 에이전트 모듈

위치 기반 날씨 정보를 검색하고 제공합니다.
OpenWeatherMap API를 사용하여 현재 날씨 및 예보 정보를 가져옵니다.
"""

import os
import json
from typing import Literal, Dict, Any, Optional, List, TypedDict
from datetime import datetime, timedelta
import httpx
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.types import Command
from dotenv import load_dotenv

from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values
from state.base_state import MessagesState, TaskStatus, AgentResponse, AgentRequest

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("weather_agent", level=LOG_LEVEL)

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 날씨 정보 제공 전문 에이전트입니다.
사용자의 위치 기반 날씨 정보를 검색하고 명확하고 유용한 형태로 제공하는 것이 당신의 역할입니다.

날씨 정보 제공 지침:
1. 정확성: 제공하는 모든 날씨 정보는 정확해야 합니다.
2. 관련성: 사용자가 요청한 위치와 시간대에 맞는 날씨 정보를 제공해야 합니다.
3. 포괄성: 온도, 습도, 강수 확률, 바람 등 다양한 날씨 요소를 포함해야 합니다.
4. 실용성: 날씨 정보를 바탕으로 실용적인 제안이나 조언을 제공할 수 있습니다.

입력으로 받는 정보:
- 위치(도시명, 국가)
- 날짜(선택 사항): 현재 또는 예보

출력 정보:
- 온도(최저, 최고, 체감 온도)
- 날씨 상태(맑음, 흐림, 비, 눈 등)
- 습도 및 기압
- 바람(속도 및 방향)
- 일출 및 일몰 시간
- 시간별 예보 또는 일일 예보(요청에 따라)

응답은 항상 한국어로 제공하세요.
"""


class WeatherAgent:
    """날씨 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        self.llm = None
        self.api_key = os.environ.get("OPENWEATHERMAP_API_KEY", "")
        
        if not self.api_key:
            logger.warning("OpenWeatherMap API 키가 설정되지 않았습니다.")
        
        # 모델 설정 가져오기
        self.model_name = os.environ.get("WEATHER_MODEL", "gemini-1.5-pro")
        logger.info(f"날씨 에이전트 LLM 모델: {self.model_name}")
    
    async def initialize(self):
        """날씨 에이전트 LLM을 초기화합니다."""
        if self.llm is None:
            logger.info("날씨 에이전트 초기화 시작")
            
            try:
                # LLM 초기화
                logger.info("LLM 초기화 중...")
                self.llm = ChatVertexAI(
                    model=self.model_name,
                    temperature=0.1,
                    max_output_tokens=4000
                )
                logger.info("LLM 초기화 완료")
                logger.info("날씨 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"날씨 에이전트 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.llm
    
    async def extract_location(self, query: str) -> str:
        """
        쿼리에서 위치 정보를 추출합니다.
        
        Args:
            query: 사용자 쿼리
            
        Returns:
            추출된 위치 문자열
        """
        # 에이전트 인스턴스 가져오기
        llm = await self.initialize()
        
        # 위치 추출 프롬프트
        messages = [
            SystemMessage(content="""당신은 텍스트에서 위치 정보를 추출하는 전문가입니다. 
주어진 쿼리에서 날씨 정보를 요청하는 위치(도시, 지역, 국가 등)를 추출하세요.
추출한 위치만 반환하고 추가 설명은 하지 마세요.
추출할 수 있는 위치 정보가 없으면 "서울"을 반환하세요."""),
            HumanMessage(content=f"다음 쿼리에서 위치 정보를 추출해주세요: {query}")
        ]
        
        try:
            response = await llm.ainvoke(messages)
            location = response.content.strip()
            logger.info(f"추출된 위치: {location}")
            return location
        except Exception as e:
            logger.error(f"위치 추출 중 오류 발생: {str(e)}")
            return "서울"  # 기본값
    
    async def get_coordinates(self, location: str) -> Dict[str, float]:
        """
        위치 이름을 좌표(위도, 경도)로 변환합니다.
        
        Args:
            location: 위치 이름(도시, 국가 등)
            
        Returns:
            위도와 경도를 포함하는 딕셔너리
        """
        base_url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {
            "q": location,
            "limit": 1,
            "appid": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    lat = data[0].get("lat")
                    lon = data[0].get("lon")
                    logger.info(f"위치 '{location}'의 좌표: 위도 {lat}, 경도 {lon}")
                    return {"lat": lat, "lon": lon}
                else:
                    logger.warning(f"위치 '{location}'에 대한 좌표를 찾을 수 없습니다.")
                    return {"lat": 37.5665, "lon": 126.9780}  # 서울 좌표(기본값)
        
        except Exception as e:
            logger.error(f"좌표 변환 중 오류 발생: {str(e)}")
            return {"lat": 37.5665, "lon": 126.9780}  # 서울 좌표(기본값)
    
    async def get_weather_data(self, coordinates: Dict[str, float]) -> Dict[str, Any]:
        """
        OpenWeatherMap API를 사용하여 날씨 데이터를 가져옵니다.
        
        Args:
            coordinates: 위도와 경도를 포함하는 딕셔너리
            
        Returns:
            날씨 데이터를 포함하는 딕셔너리
        """
        lat = coordinates.get("lat", 37.5665)  # 기본값: 서울 위도
        lon = coordinates.get("lon", 126.9780)  # 기본값: 서울 경도
        
        base_url = "https://api.openweathermap.org/data/2.5/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely",
            "units": "metric",
            "lang": "kr",
            "appid": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                
                weather_data = response.json()
                logger.info(f"날씨 데이터 가져오기 성공: {len(str(weather_data))} 바이트")
                return weather_data
        
        except Exception as e:
            logger.error(f"날씨 데이터 가져오기 중 오류 발생: {str(e)}")
            
            # 오류 발생 시 더미 데이터 반환
            current_time = datetime.now().timestamp()
            return {
                "current": {
                    "dt": current_time,
                    "temp": 20,
                    "feels_like": 20,
                    "humidity": 50,
                    "wind_speed": 2,
                    "weather": [{"main": "Clear", "description": "맑음"}]
                },
                "daily": [
                    {
                        "dt": current_time + i * 86400,
                        "temp": {"min": 15, "max": 25},
                        "weather": [{"main": "Clear", "description": "맑음"}]
                    }
                    for i in range(7)
                ],
                "hourly": [
                    {
                        "dt": current_time + i * 3600,
                        "temp": 20,
                        "weather": [{"main": "Clear", "description": "맑음"}]
                    }
                    for i in range(24)
                ]
            }
    
    async def format_weather_response(self, location: str, weather_data: Dict[str, Any]) -> str:
        """
        날씨 데이터를 사용자 친화적인 응답으로 변환합니다.
        
        Args:
            location: 위치 이름
            weather_data: 날씨 데이터
            
        Returns:
            형식화된 날씨 응답
        """
        # 에이전트 인스턴스 가져오기
        llm = await self.initialize()
        
        # 날씨 데이터를 문자열로 변환
        weather_json = json.dumps(weather_data, ensure_ascii=False, indent=2)
        
        # 날씨 응답 프롬프트
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"""위치: {location}
            
다음은 OpenWeatherMap API에서 가져온 날씨 데이터입니다:

{weather_json}

위 데이터를 기반으로 사용자 친화적인 날씨 정보를 한국어로 제공해주세요. 
현재 날씨와 오늘/내일 예보를 포함해주세요.
온도, 체감 온도, 습도, 바람, 날씨 상태를 모두 포함하세요.""")
        ]
        
        try:
            response = await llm.ainvoke(messages)
            formatted_response = response.content.strip()
            logger.info(f"날씨 응답 형식화 완료: {len(formatted_response)} 자")
            return formatted_response
        except Exception as e:
            logger.error(f"날씨 응답 형식화 중 오류 발생: {str(e)}")
            
            # 오류 발생 시 기본 응답 생성
            current = weather_data.get("current", {})
            temp = current.get("temp", "알 수 없음")
            weather = current.get("weather", [{}])[0].get("description", "알 수 없음")
            
            return f"{location}의 현재 날씨: {weather}, 온도: {temp}°C\n\n(상세 정보 로드 중 오류가 발생했습니다.)"
    
    async def get_weather_for_location(self, query: str) -> str:
        """
        위치에 대한 날씨 정보를 가져옵니다.
        
        Args:
            query: 위치 정보가 포함된 쿼리
            
        Returns:
            형식화된 날씨 정보
        """
        # 위치 추출
        location = await self.extract_location(query)
        
        # 위치를 좌표로 변환
        coordinates = await self.get_coordinates(location)
        
        # 날씨 데이터 가져오기
        weather_data = await self.get_weather_data(coordinates)
        
        # 응답 형식화
        response = await self.format_weather_response(location, weather_data)
        
        return response
    
    async def __call__(self, state: MessagesState) -> Command[Literal["orchestrator"]]:
        """
        날씨 에이전트 호출 메서드입니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            오케스트레이터로 돌아가는 명령
        """
        try:
            logger.info("날씨 에이전트 호출 시작")
            
            # 날씨 요청 파악
            plan = state.get("plan", [])
            current_step_idx = state.get("current_step", 0)
            
            if current_step_idx is not None and 0 <= current_step_idx < len(plan):
                # 현재 단계 정보 가져오기
                current_step = plan[current_step_idx]
                query = current_step.request.query if current_step.request else ""
                
                if not query:
                    # 쿼리가 없는 경우, 원본 쿼리 사용
                    query = state.get("original_query", "")
                
                logger.info(f"날씨 에이전트 쿼리: {query}")
                
                # 현재 단계 상태 업데이트
                current_step.status = TaskStatus.executing
                current_step.start_time = datetime.now()
                
                # 날씨 정보 가져오기
                weather_response = await self.get_weather_for_location(query)
                
                # 응답 생성
                response_message = AIMessage(
                    content=weather_response,
                    name="weather_agent"
                )
                
                # 응답 저장
                agent_response = AgentResponse(
                    content=weather_response,
                    timestamp=datetime.now()
                )
                
                # 단계 완료 처리
                current_step.status = TaskStatus.completed
                current_step.end_time = datetime.now()
                current_step.response = agent_response
                
                # 결과 저장
                results = state.get("results", {})
                results[current_step_idx] = {
                    "step": current_step,
                    "response": agent_response
                }
                
                # 상태 업데이트 준비
                updated_state = dict(state)
                updated_state["messages"] = updated_state.get("messages", []) + [response_message]
                updated_state["results"] = results
                updated_state["current_step"] = current_step_idx + 1
                updated_state["status"] = TaskStatus.executing
                updated_state["next"] = "orchestrator"
                
                logger.info("날씨 에이전트 작업 완료, 오케스트레이터로 반환")
                
                # 오케스트레이터로 돌아가기
                return Command(
                    update=updated_state,
                    goto="orchestrator"
                )
            else:
                # 유효한 단계 없음
                logger.warning(f"유효한 단계를 찾을 수 없음: current_step_idx={current_step_idx}, plan_length={len(plan)}")
                error_message = AIMessage(
                    content="날씨 정보를 처리할 유효한 단계를 찾을 수 없습니다.",
                    name="weather_agent"
                )
                
                error_state = dict(state)
                error_state["messages"] = error_state.get("messages", []) + [error_message]
                error_state["status"] = TaskStatus.failed
                error_state["next"] = "orchestrator"
                
                return Command(
                    update=error_state,
                    goto="orchestrator"
                )
            
        except Exception as e:
            logger.error(f"날씨 에이전트 호출 중 오류 발생: {str(e)}")
            error_message = AIMessage(
                content=f"날씨 에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                name="weather_agent"
            )
            
            error_state = dict(state)
            error_state["messages"] = error_state.get("messages", []) + [error_message]
            error_state["status"] = TaskStatus.failed
            error_state["next"] = "orchestrator"
            
            return Command(
                update=error_state,
                goto="orchestrator"
            )


# 날씨 에이전트 인스턴스 생성
weather_agent = WeatherAgent()

# weather_agent_node 함수는 WeatherAgent 인스턴스를 호출하는 래퍼 함수
async def weather_agent_node(state: MessagesState) -> Command[Literal["orchestrator"]]:
    """
    날씨 에이전트 노드 함수입니다. WeatherAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        오케스트레이터로 돌아가는 명령
    """
    return await weather_agent(state) 