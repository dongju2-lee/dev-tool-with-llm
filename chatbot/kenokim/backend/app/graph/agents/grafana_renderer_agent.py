from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from ..mcp.grafana_renderer_client import get_grafana_renderer_mcp_client
from ...core.config import settings


def create_grafana_renderer_agent():
    """Grafana Renderer MCP 클라이언트를 사용하는 에이전트를 생성합니다."""
    
    # MCP 클라이언트 가져오기
    mcp_client = get_grafana_renderer_mcp_client()
    tools = mcp_client.get_tools()
    
    # Gemini 모델 설정
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1
    )
    
    # Grafana Renderer 전문 시스템 프롬프트
    system_prompt = """당신은 Grafana 대시보드 시각화 및 렌더링 전문 AI 어시스턴트입니다.
    
주요 역할:
1. **대시보드 렌더링**: Grafana 대시보드를 이미지로 렌더링하여 시각적 리포트를 생성합니다.
2. **차트 및 그래프 생성**: 특정 패널이나 차트를 고품질 이미지로 변환합니다.
3. **시각화 최적화**: 렌더링 설정, 해상도, 테마 등을 최적화합니다.
4. **리포트 자동화**: 정기적인 모니터링 리포트 생성을 지원합니다.

항상 고품질의 시각화 결과물을 제공하며, 사용자의 모니터링 및 리포팅 요구사항을 만족시킵니다."""
    
    # create_react_agent로 에이전트 생성
    agent = create_react_agent(
        model=model, 
        tools=tools,
        prompt=system_prompt
    )
    
    return agent 