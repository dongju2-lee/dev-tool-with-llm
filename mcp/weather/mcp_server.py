from mcp.server.fastmcp import FastMCP
import os
import random
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("weather_mcp_server")

# FastMCP 인스턴스 생성
mcp = FastMCP(
    "weather_service",  # MCP 서버 이름
    instructions="날씨 정보를 제공하는 도구입니다. 가장 더운 나라 검색, 특정 나라의 평균 온도 조회, 여러 도시의 강수량 조회 기능을 제공합니다.",
    host="0.0.0.0",  # 모든 IP에서 접속 허용
    port=8011,  # 포트 번호
)

# 전세계에서 가장 더운 나라 검색 도구
@mcp.tool()
async def get_hottest_country() -> Dict:
    """
    전세계에서 가장 더운 나라를 검색합니다.
    서울, 도쿄, 뉴욕, 파리, 런던, 카이로, 베이징 중에서 랜덤하게 하나의 도시를 반환합니다.
    
    Returns:
        Dict: 가장 더운 나라 정보가 포함된 딕셔너리
    """
    logger.info("가장 더운 나라 검색 요청 수신")
    
    # 도시 목록
    cities = ["서울", "도쿄", "뉴욕", "파리", "런던", "카이로", "베이징"]
    
    # 랜덤하게 도시 선택
    hottest_city = random.choice(cities)
    
    # 온도 랜덤 생성 (35~45도)
    temperature = random.uniform(35, 45)
    
    result = {
        "hottest_city": hottest_city,
        "temperature": round(temperature, 1),
        "unit": "celsius",
        "timestamp": "현재 시간 기준"
    }
    
    logger.info(f"가장 더운 나라 검색 결과: {result}")
    return result

# 특정 나라의 평균 온도 조회 도구
@mcp.tool()
async def get_country_temperature(country: str) -> Dict:
    """
    특정 나라의 평균 온도를 조회합니다.
    15~40도 사이의 랜덤한 온도를 반환합니다.
    
    Args:
        country (str): 온도를 조회할 나라 이름
        
    Returns:
        Dict: 해당 나라의 평균 온도 정보가 포함된 딕셔너리
    """
    logger.info(f"평균 온도 조회 요청 수신: {country}")
    
    # 온도 랜덤 생성 (15~40도)
    temperature = random.uniform(15, 40)
    
    # 날씨 상태 랜덤 선택
    weather_conditions = ["맑음", "흐림", "비", "폭염", "안개", "구름 조금"]
    weather = random.choice(weather_conditions)
    
    result = {
        "country": country,
        "average_temperature": round(temperature, 1),
        "weather_condition": weather,
        "unit": "celsius",
        "timestamp": "현재 시간 기준"
    }
    
    logger.info(f"평균 온도 조회 결과: {result}")
    return result

# 여러 도시의 강수량 조회 도구
@mcp.tool()
async def get_rainfall_amount(cities: List[str]) -> Dict:
    """
    여러 도시의 강수량을 조회합니다.
    각 도시마다 0~10 사이의 랜덤한 강수량을 반환합니다.
    
    Args:
        cities (List[str]): 강수량을 조회할 도시 목록 (최대 3개 권장)
        
    Returns:
        Dict: 각 도시의 강수량 정보가 포함된 딕셔너리
    """
    logger.info(f"강수량 조회 요청 수신: {cities}")
    
    # 최대 3개 도시만 처리
    if len(cities) > 3:
        cities = cities[:3]
        logger.warning(f"도시 수가 3개를 초과하여 앞의 3개만 처리합니다: {cities}")
    
    # 각 도시별 강수량 랜덤 생성
    rainfall_data = {}
    rainfall_descriptions = ["없음", "매우 적음", "적음", "보통", "많음", "매우 많음", "폭우"]
    
    for city in cities:
        # 0~10 사이 강수량 랜덤 생성
        amount = random.uniform(0, 10)
        
        # 강수량에 따른 설명 선택
        description_index = min(int(amount * len(rainfall_descriptions) / 10), len(rainfall_descriptions) - 1)
        description = rainfall_descriptions[description_index]
        
        rainfall_data[city] = {
            "amount": round(amount, 1),
            "unit": "mm/시간",
            "description": description
        }
    
    result = {
        "rainfall_data": rainfall_data,
        "cities_count": len(cities),
        "timestamp": "현재 시간 기준"
    }
    
    logger.info(f"강수량 조회 결과: {result}")
    return result

if __name__ == "__main__":
    # 서버 시작 메시지 출력
    print("날씨 검색 MCP 서버가 실행 중입니다...")
    print("포트 8010에서 수신 대기 중...")
    
    # SSE 트랜스포트를 사용하여 MCP 서버 시작
    mcp.run(transport="sse") 