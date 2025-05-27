import os
from typing import Dict, List, Any
import aiofiles

from langchain_google_vertexai import ChatVertexAI
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langfuse.callback import CallbackHandler
import logging

logger = logging.getLogger("general_agent")
logging.basicConfig(level=logging.INFO)
from utils.config import settings

# 환경 변수 로드
load_dotenv()

# 싱글톤 인스턴스
_llm_instance = None
_mcp_client = None
_mcp_tools_cache = None

langfuse_handler = CallbackHandler(public_key="", secret_key="", host="")

# MCP 서버 URL 설정
MCP_SERVERS = {
    # "github": {
    #     "url": os.environ.get(
    #         "REFRIGERATOR_MCP_URL", "http://localhost:10005/sse"
    #     ),
    #     "transport": "sse",
    # },
    # "milvus": {
    #     "url": os.environ.get(
    #         "REFRIGERATOR_MCP_URL", "http://localhost:10004/sse"
    #     ),
    #     "transport": "sse",
    # },
    # "k6": {
    #     "url": os.environ.get(
    #         "REFRIGERATOR_MCP_URL", "http://localhost:10003/sse"
    #     ),
    #     "transport": "sse",
    # },
    "loki-tempo": {
        "url": os.environ.get(
            "LOKI_TEMPO_MCP_URL", "http://localhost:10002/sse"
        ),
        "transport": "sse",
    }
}


# MCP 클라이언트 초기화 함수
async def init_mcp_client():
    """MCP 클라이언트를 초기화합니다."""
    global _mcp_client
    if _mcp_client is None:
        logger.info("MCP 클라이언트 초기화 시작")
        try:
            client = MultiServerMCPClient(MCP_SERVERS)
            logger.info("MCP 클라이언트 인스턴스 생성 완료")
            _mcp_client = client
            logger.info("MCP 클라이언트 초기화 완료")
        except Exception as e:
            logger.info(f"MCP 클라이언트 초기화 중 오류 발생: {str(e)}")
            raise
    return _mcp_client


# MCP 클라이언트 종료 함수 (필요시)
async def close_mcp_client():
    """MCP 클라이언트 연결을 안전하게 종료합니다."""
    global _mcp_client
    _mcp_client = None
    logger.info("MCP 클라이언트 인스턴스 해제 완료")


# MCP 도구 가져오기 함수
async def get_mcp_tools() -> List:
    """MCP 도구를 가져오고 상세 정보를 출력합니다."""
    global _mcp_tools_cache
    if _mcp_tools_cache is not None:
        return _mcp_tools_cache
    try:
        client = await init_mcp_client()
        logger.info("MCP 도구 가져오는 중...")
        tools = await client.get_tools()  # await 필수!
        logger.info(f"총 {len(tools)}개의 MCP 도구를 가져왔습니다")
        _mcp_tools_cache = tools
        return tools
    except Exception as e:
        logger.info(f"도구 가져오기 중 오류 발생: {str(e)}")
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
            logger.info(f"도구 정보 변환 중 오류: {str(e)}")
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
        logger.info(f"LLM 모델 초기화: {model_name}")
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
        logger.info(f"도구 정보 가져오기 중 오류 발생: {str(e)}")
        tools_text = "도구 정보를 가져오는 중 오류가 발생했습니다. MCP 서버 연결을 확인하세요."
    
    prompt_path = os.path.join(
        os.path.dirname(__file__), "../prompts/general_agent.txt"
    )
    async with aiofiles.open(prompt_path, mode="r", encoding="utf-8") as f:
        prompt_template = await f.read()
    
    # {tools} 변수만 실제 변수로 처리하고 나머지는 일반 텍스트로 처리하기 위한 방법
    
    # 1. {tools} 변수를 임시 토큰으로 대체
    tools_token = "__TOOLS_PLACEHOLDER__"
    prompt_template = prompt_template.replace("{tools}", tools_token)
    
    # 2. 따옴표를 이스케이프 처리 (LangChain이 변수로 해석할 수 있는 패턴 처리)
    # `"source"`와 같은 패턴이 변수로 해석되는 것을 방지
    prompt_template = prompt_template.replace('"', '\\"')
    
    # 3. 중괄호를 이스케이프 처리 (모든 { 를 {{ 로, } 를 }} 로 변경)
    prompt_template = prompt_template.replace("{", "{{").replace("}", "}}")
    
    # 4. 임시 토큰을 다시 {tools} 변수로 복원
    prompt_template = prompt_template.replace(f"{{{{{tools_token}}}}}", "{tools}")
    
    # 5. 도구 목록 삽입
    prompt = prompt_template.replace("{tools}", tools_text)
    
    logger.info("프롬프트 템플릿 처리 완료")
    return prompt


# 계획 생성 함수
async def get_general_agent() -> str:
    """사용자 요청에 대한 계획을 생성합니다."""
    global _agent_instance
    prompt = await generate_prompt()
    logger.info("프롬프트 생성 완료")
    system_prompt = ChatPromptTemplate.from_messages(
        [("system", prompt), MessagesPlaceholder(variable_name="messages")]
    )
    llm = await get_llm()
    tools = await get_mcp_tools()
    _agent_instance = create_react_agent(
        llm, tools, prompt=system_prompt, debug=True  # 디버그 모드 활성화
    )
    logger.info("에이전트 생성 완료")
    return _agent_instance