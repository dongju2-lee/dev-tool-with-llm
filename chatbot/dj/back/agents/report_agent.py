import os
from typing import Dict, List, Any
import aiofiles

from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langfuse.callback import CallbackHandler

from utils.config import settings

# 환경 변수 로드
load_dotenv()

# 싱글톤 인스턴스
_llm_instance = None
_mcp_client = None
_mcp_tools_cache = None
_agent_instance = None

langfuse_handler = CallbackHandler(public_key="", secret_key="", host="")

# MCP 서버 URL 설정
MCP_SERVERS = {
    "github": {
        "url": os.environ.get(
            "REFRIGERATOR_MCP_URL", "http://localhost:10005/sse"
        ),
        "transport": "sse",
    }
}


# MCP 클라이언트 초기화 함수
async def init_mcp_client():
    """MCP 클라이언트를 초기화합니다."""
    global _mcp_client
    if _mcp_client is None:
        print("MCP 클라이언트 초기화 시작")
        try:
            client = MultiServerMCPClient(MCP_SERVERS)
            print("MCP 클라이언트 인스턴스 생성 완료")
            _mcp_client = client
            print("MCP 클라이언트 초기화 완료")
        except Exception as e:
            print(f"MCP 클라이언트 초기화 중 오류 발생: {str(e)}")
            raise
    return _mcp_client


# MCP 클라이언트 종료 함수 (필요시)
async def close_mcp_client():
    """MCP 클라이언트 연결을 안전하게 종료합니다."""
    global _mcp_client
    _mcp_client = None
    print("MCP 클라이언트 인스턴스 해제 완료")


# MCP 도구 가져오기 함수
async def get_mcp_tools() -> List:
    """MCP 도구를 가져오고 상세 정보를 출력합니다."""
    global _mcp_tools_cache
    if _mcp_tools_cache is not None:
        return _mcp_tools_cache
    try:
        client = await init_mcp_client()
        print("MCP 도구 가져오는 중...")
        tools = await client.get_tools()  # await 필수!
        print(f"총 {len(tools)}개의 MCP 도구를 가져왔습니다")
        _mcp_tools_cache = tools
        return tools
    except Exception as e:
        print(f"도구 가져오기 중 오류 발생: {str(e)}")
        return []


# MCP 도구 정보 변환 함수
async def convert_mcp_tools_to_info() -> List[Dict[str, Any]]:
    """MCP 도구를 사용자 친화적인 형식으로 변환합니다."""
    tools = await get_mcp_tools()
    tools_info = []
    for tool in tools:
        try:
            tool_info = {
                "name": getattr(tool, "name", "Unknown"),
                "description": getattr(tool, "description", "설명 없음"),
                "parameters": [],
            }
            if hasattr(tool, "args_schema") and tool.args_schema is not None:
                schema_props = getattr(tool.args_schema, "schema", {}).get(
                    "properties", {}
                )
                if schema_props:
                    tool_info["parameters"] = list(schema_props.keys())
            tools_info.append(tool_info)
        except Exception as e:
            print(f"도구 정보 변환 중 오류: {str(e)}")
    return tools_info


# LLM 모델 초기화 함수
async def get_llm():
    """LLM 모델을 초기화하고 반환합니다."""

    import vertexai

    vertexai.init(
        project=settings.gcp_project_id,
        location=settings.gcp_vertexai_location,
    )

    global _llm_instance
    if _llm_instance is None:
        model_name = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")
        print(f"LLM 모델 초기화: {model_name}")
        _llm_instance = ChatVertexAI(
            model=model_name, temperature=0.1, max_output_tokens=8190
        )
    return _llm_instance


# 프롬프트 생성 함수
async def generate_prompt() -> str:
    """사용자 요청에 따른 프롬프트를 생성합니다."""
    try:
        tools_info = await convert_mcp_tools_to_info()
        tools_text = "\n".join(
            [
                f"{i+1}. {tool['name']}: {tool['description']}"
                for i, tool in enumerate(tools_info)
            ]
        )
        if not tools_text:
            tools_text = (
                "현재 사용 가능한 도구가 없습니다. MCP 서버 연결을 확인하세요."
            )
    except Exception as e:
        print(f"도구 정보 가져오기 중 오류 발생: {str(e)}")
        tools_text = "도구 정보를 가져오는 중 오류가 발생했습니다. MCP 서버 연결을 확인하세요."
    
    prompt_path = os.path.join(
        os.path.dirname(__file__), "../prompts/report_agent.txt"
    )
    async with aiofiles.open(prompt_path, mode="r", encoding="utf-8") as f:
        prompt_template = await f.read()
    
    # 단순 문자열 대체 사용
    prompt = prompt_template.replace("{tools}", tools_text)
    
    return prompt


# 리포트 에이전트 생성 함수
async def get_report_agent():
    """리포트 에이전트를 생성하고 반환합니다."""
    global _agent_instance
    if _agent_instance is None:
        prompt = await generate_prompt()
        print("프롬프트 생성 완료")
        system_prompt = ChatPromptTemplate.from_messages(
            [("system", prompt), MessagesPlaceholder(variable_name="messages")]
        )
        llm = await get_llm()
        tools = await get_mcp_tools()
        _agent_instance = create_react_agent(
            llm, tools, prompt=system_prompt, debug=True  # 디버그 모드 활성화
        )
        print("리포트 에이전트 생성 완료")
    return _agent_instance


# 리포트 생성 함수
async def generate_report(user_query: str) -> str:
    """사용자 쿼리를 받아 리포트를 생성합니다."""
    try:
        print(f"리포트 생성 시작: {user_query}")
        agent = await get_report_agent()
        
        # 에이전트 실행
        result = await agent.ainvoke(
            {"messages": [("user", user_query)]},
            config={"callbacks": [langfuse_handler]}
        )
        
        # 결과에서 최종 답변 추출
        if "messages" in result and result["messages"]:
            final_message = result["messages"][-1]
            if hasattr(final_message, "content"):
                return final_message.content
            else:
                return str(final_message)
        else:
            return "리포트 생성 중 오류가 발생했습니다."
            
    except Exception as e:
        print(f"리포트 생성 중 오류 발생: {str(e)}")
        return f"리포트 생성 중 오류가 발생했습니다: {str(e)}"


# 장애 분석 리포트 생성 함수
async def analyze_incident(incident_description: str, time_range: str = "1h") -> str:
    """장애 상황을 분석하고 상세한 리포트를 생성합니다."""
    analysis_query = f"""
    다음 장애 상황을 분석해주세요:
    
    장애 설명: {incident_description}
    분석 시간 범위: {time_range}
    
    다음 단계로 분석을 진행해주세요:
    1. 관련 메트릭 데이터 수집 및 분석
    2. 로그 패턴 분석
    3. 트레이스 데이터 확인
    4. 최근 배포 및 변경사항 확인
    5. 근본 원인 분석
    6. 해결 방안 및 예방 전략 제시
    
    증거 기반의 상세한 분석 리포트를 작성해주세요.
    """
    
    return await generate_report(analysis_query)


# 성능 분석 리포트 생성 함수
async def analyze_performance(service_name: str, metric_type: str = "response_time") -> str:
    """특정 서비스의 성능을 분석하고 리포트를 생성합니다."""
    performance_query = f"""
    다음 서비스의 성능을 분석해주세요:
    
    서비스명: {service_name}
    분석 메트릭: {metric_type}
    
    다음 항목들을 포함하여 분석해주세요:
    1. 현재 성능 지표 현황
    2. 과거 대비 성능 변화 추이
    3. 성능 병목 지점 식별
    4. 리소스 사용량 분석
    5. 성능 개선 방안 제시
    
    데이터 기반의 상세한 성능 분석 리포트를 작성해주세요.
    """
    
    return await generate_report(performance_query)


# 시스템 상태 리포트 생성 함수
async def generate_system_health_report() -> str:
    """전체 시스템의 상태를 점검하고 리포트를 생성합니다."""
    health_query = """
    전체 시스템의 상태를 점검하고 종합적인 헬스 리포트를 작성해주세요.
    
    다음 항목들을 포함해주세요:
    1. 주요 서비스별 상태 점검
    2. 인프라 리소스 사용량 현황
    3. 최근 발생한 이슈 및 알림 분석
    4. 성능 지표 트렌드 분석
    5. 잠재적 위험 요소 식별
    6. 권장 조치사항
    
    현재 시스템의 전반적인 건강 상태와 개선이 필요한 영역을 명확히 제시해주세요.
    """
    
    return await generate_report(health_query)


# 에이전트 정리 함수
async def cleanup_agent():
    """에이전트 리소스를 정리합니다."""
    global _agent_instance, _mcp_client, _mcp_tools_cache, _llm_instance
    
    _agent_instance = None
    _mcp_tools_cache = None
    _llm_instance = None
    
    if _mcp_client:
        await close_mcp_client()
    
    print("리포트 에이전트 리소스 정리 완료")