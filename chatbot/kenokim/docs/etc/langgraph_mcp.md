# LangGraph와 MCP(Model Context Protocol) 연동 가이드

이 문서는 LangGraph와 MCP(Model Context Protocol)를 연동하는 방법을 Python 기준으로 설명합니다.

## 1. 필요한 라이브러리

다음 라이브러리들이 필요합니다:

```bash
pip install mcp==0.1.6                   # MCP 코어 라이브러리 (2025년 최신 버전: 1.6.0)
pip install langchain-core>=0.1.28       # LangChain 코어
pip install langgraph>=0.2.0             # LangGraph (2025년 최신 버전: 0.4.1)
pip install langchain-mcp-adapters>=0.0.5 # LangChain MCP 어댑터 (2025년 최신 버전: 0.0.9)
```

### 라이브러리 출처 및 업데이트 상태

| 라이브러리 | 출처 | 2025년 상태 | 최신 버전 |
|------------|------|-------------|------------|
| mcp | [GitHub - modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | 활발히 유지보수 중 | 1.6.0 (2025년 3월 27일) |
| langgraph | [LangChain - LangGraph](https://langchain-ai.github.io/langgraph/) | 활발히 유지보수 중 | 0.4.1 (2025년 4월 30일) |
| langchain-mcp-adapters | [GitHub - langchain-ai/langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) | 활발히 유지보수 중 | 0.0.9 (2025년 4월 16일) |

LLM 제공자에 따라 추가 패키지가 필요합니다:

```bash
# OpenAI를 사용하는 경우
pip install langchain-openai

# Vertex AI (Gemini)를 사용하는 경우
pip install langchain-google-vertexai
pip install google-cloud-aiplatform
```

## 2. MCP 서버 구현 (Python)

### 2.1 기본 MCP 서버 구조

MCP 서버는 FastMCP를 사용하여 쉽게 구현할 수 있습니다:

```python
"""
간단한 MCP 서버 예제

이 모듈은 FastMCP를 사용한 간단한 수학 연산 도구를 제공하는 MCP 서버입니다.
"""

from mcp.server.fastmcp import FastMCP
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastMCP 서버 생성
mcp = FastMCP("MathTools")

@mcp.tool()
def add(a: int, b: int) -> int:
    """두 숫자를 더합니다.
    
    Args:
        a: 첫 번째 숫자
        b: 두 번째 숫자
        
    Returns:
        두 숫자의 합
    """
    logger.info(f"add 도구 호출: {a} + {b}")
    return a + b

# 더 많은 도구 추가...

if __name__ == "__main__":
    # stdio 모드로 서버 실행
    try:
        logger.info("MCP 서버 시작...")
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("서버가 중지되었습니다.")
    except Exception as e:
        logger.error(f"서버 오류: {str(e)}")
```

### 2.2 도구 데코레이터 활용

MCP 서버의 도구는 `@mcp.tool()` 데코레이터를 사용하여 정의합니다:

```python
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """두 숫자를 곱합니다.
    
    Args:
        a: 첫 번째 숫자
        b: 두 번째 숫자
        
    Returns:
        두 숫자의 곱
    """
    logger.info(f"multiply 도구 호출: {a} * {b}")
    return a * b

@mcp.tool()
def divide(a: int, b: int) -> float:
    """첫 번째 숫자를 두 번째 숫자로 나눕니다.
    
    Args:
        a: 첫 번째 숫자 (나누어질 수)
        b: 두 번째 숫자 (나누는 수)
        
    Returns:
        나눗셈 결과
    """
    if b == 0:
        raise ValueError("0으로 나눌 수 없습니다.")
    logger.info(f"divide 도구 호출: {a} / {b}")
    return a / b
```

### 2.3 MCP 서버 실행 방법

MCP 서버는 stdio 통신을 통해 클라이언트와 통신합니다. 다음과 같이 실행합니다:

```bash
python math_server.py
```

일반적으로 MCP 서버는 직접 실행하지 않고, MCP 클라이언트에 의해 subprocess로 실행됩니다.

## 3. LangGraph와 MCP 연동

### 3.1 LangGraph용 MCP 클라이언트 구현

LangGraph와 MCP를 연동하는 클라이언트를 구현합니다:

```python
import os
import logging
import asyncio
from typing import List, Dict, Any, Tuple, Optional
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_google_vertexai import ChatVertexAI  # 또는 다른 LLM 제공자
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint import InMemoryCheckpointer

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPLangGraphClient:
    """LangGraph와 MCP를 연동하는 클라이언트"""
    
    def __init__(self, 
                 server_script_path: str,
                 model_name: str = "gemini-1.5-flash"):
        """클라이언트 초기화
        
        Args:
            server_script_path: MCP 서버 스크립트 경로
            model_name: 사용할 LLM 모델 이름
        """
        self.server_script_path = server_script_path
        self.model_name = model_name
        
        # 클라이언트 컴포넌트
        self.session = None
        self.agent = None
        self.tools = []
        
        # 비동기 작업을 위한 이벤트 루프
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    async def _initialize_session(self) -> Tuple[ClientSession, List[Any]]:
        """MCP 세션을 초기화하고 도구를 로드합니다."""
        logger.info(f"MCP 서버 연결 중: {self.server_script_path}")
        
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path],
        )
        
        # stdio 클라이언트 생성
        read, write = await stdio_client(server_params)
        session = await ClientSession(read, write)
        await session.initialize()
        
        # MCP 도구 로드
        tools = await load_mcp_tools(session)
        logger.info(f"도구 로드 완료: {len(tools)}개")
        
        return session, tools
    
    async def _setup_agent(self) -> Any:
        """ReAct 에이전트를 설정합니다."""
        # 세션 및 도구 초기화
        self.session, self.tools = await self._initialize_session()
        
        # LLM 설정
        llm = ChatVertexAI(
            model_name=self.model_name,
            max_output_tokens=1024,
            temperature=0.1,
        )
        
        # ReAct 에이전트 생성
        agent = create_react_agent(
            llm=llm,
            tools=self.tools,
            system_message="당신은 MCP 도구를 사용하는 AI 에이전트입니다."
        )
        
        # 체크포인터 설정
        checkpointer = InMemoryCheckpointer()
        
        # 체크포인트 설정 추가
        return agent.with_config({"checkpointer": checkpointer})
    
    def initialize(self):
        """클라이언트를 초기화합니다."""
        self.agent = self.loop.run_until_complete(self._setup_agent())
        logger.info("에이전트 초기화 완료")
    
    def close(self):
        """세션을 닫습니다."""
        if self.session:
            self.loop.run_until_complete(self.session.close())
            self.session = None
            logger.info("세션 종료됨")
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """쿼리를 처리합니다."""
        async def _process():
            if not self.agent:
                logger.warning("에이전트가 초기화되지 않았습니다.")
                self.agent = await self._setup_agent()
            
            # 쿼리 처리
            messages = [HumanMessage(content=query)]
            
            # 에이전트 실행
            response_messages = []
            async for event in self.agent.astream({"messages": messages}):
                if "messages" in event:
                    response_messages = event["messages"]
            
            # 결과 추출
            final_response = ""
            tool_outputs = []
            
            for msg in response_messages:
                if isinstance(msg, AIMessage) and msg not in messages:
                    final_response = msg.content
                elif isinstance(msg, ToolMessage) and msg not in messages:
                    tool_outputs.append({"tool": msg.name, "result": msg.content})
            
            return {
                "response": final_response,
                "tool_outputs": tool_outputs
            }
        
        return self.loop.run_until_complete(_process())
```

### 3.2 LangGraph와 MCP 연동 예제

아래는 MCP 서버를 LangGraph ReAct 에이전트와 연동하는 예제입니다:

```python
# 서버 경로 설정
server_script_path = "math_server.py"

# 클라이언트 생성 및 초기화
client = MCPLangGraphClient(server_script_path, model_name="gemini-1.5-flash")
client.initialize()

try:
    # 쿼리 처리
    result = client.process_query("15와 27을 더하면 얼마인가요?")
    
    # 응답 출력
    print(f"응답: {result['response']}")
    
    # 도구 출력 표시
    for tool_output in result.get("tool_outputs", []):
        print(f"도구: {tool_output.get('tool', '알 수 없음')}")
        print(f"결과: {tool_output.get('result', '')}")
finally:
    # 세션 종료
    client.close()
```

## 4. MCP와 LangGraph ReAct 에이전트 통합

### 4.1 ReAct 에이전트 패턴

LangGraph의 ReAct 에이전트 패턴은 다음과 같은 흐름으로 작동합니다:

1. 사용자가 쿼리를 입력합니다.
2. LLM이 쿼리를 분석하고 도구 실행 여부를 결정합니다.
3. 도구가 필요한 경우, 해당 도구를 호출합니다.
4. 도구 실행 결과를 LLM에 전달합니다.
5. LLM이 최종 응답을 생성합니다.

### 4.2 주요 구성 요소

MCP와 LangGraph 통합의 주요 구성 요소:

1. **ClientSession**: MCP 서버와의 통신을 관리합니다.
2. **load_mcp_tools**: MCP 서버의 도구를 LangChain 도구로 변환합니다.
3. **create_react_agent**: ReAct 에이전트를 생성합니다.
4. **InMemoryCheckpointer**: 에이전트의 상태를 저장합니다.

### 4.3 데이터 흐름

MCP와 LangGraph 통합의 데이터 흐름:

```
사용자 쿼리 -> LangGraph 에이전트 -> LLM 추론 -> MCP 도구 호출 -> 
도구 실행 결과 -> LLM 추론 -> 최종 응답 -> 사용자
```

## 5. 실전 예제: Streamlit 앱에서 LangGraph MCP 활용

Streamlit 앱에서 LangGraph MCP를 활용하는 예제:

```python
import streamlit as st
import os
from mcp_langgraph_client import MCPLangGraphClient

# 페이지 설정
st.set_page_config(
    page_title="LangGraph MCP 데모",
    page_icon="🤖",
    layout="centered"
)

# 세션 상태 초기화
if "client" not in st.session_state:
    st.session_state.client = None

# 서버 스크립트 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
server_script_path = os.path.join(current_dir, "math_server.py")

# 사이드바 설정
with st.sidebar:
    st.header("설정")
    
    # 모델 선택
    model_name = st.selectbox(
        "모델 선택",
        ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    )
    
    # 클라이언트 초기화 버튼
    if st.button("클라이언트 초기화"):
        with st.spinner("MCP 클라이언트 초기화 중..."):
            try:
                # 기존 클라이언트 종료
                if st.session_state.client:
                    st.session_state.client.close()
                
                # 새 클라이언트 생성 및 초기화
                st.session_state.client = MCPLangGraphClient(
                    server_script_path=server_script_path,
                    model_name=model_name
                )
                st.session_state.client.initialize()
                st.success("클라이언트 초기화 성공")
            except Exception as e:
                st.error(f"초기화 오류: {str(e)}")
                st.session_state.client = None

# 메인 인터페이스
st.title("LangGraph MCP 데모")

# 데모 설명
st.markdown("""
이 데모는 LangGraph와 MCP를 연동하여 수학 연산을 수행하는 예제입니다.
사이드바에서 클라이언트를 초기화한 후, 아래에 질문을 입력해 보세요.

예시 질문:
- "15와 27을 더하면 얼마인가요?"
- "42에서 17을 빼면 얼마가 되나요?"
- "8과 9를 곱하면 얼마인가요?"
""")

# 사용자 입력
query = st.text_input("질문 입력:")

if query and st.session_state.client:
    with st.spinner("처리 중..."):
        try:
            # 쿼리 처리
            result = st.session_state.client.process_query(query)
            
            # 응답 표시
            st.markdown("### 응답")
            st.write(result["response"])
            
            # 도구 정보 표시
            st.markdown("### 사용된 도구")
            for tool_output in result.get("tool_outputs", []):
                st.info(f"도구: {tool_output.get('tool', '알 수 없음')}")
                st.code(tool_output.get("result", ""))
        except Exception as e:
            st.error(f"처리 오류: {str(e)}")
elif query:
    st.warning("클라이언트가 초기화되지 않았습니다. 사이드바에서 '클라이언트 초기화' 버튼을 클릭하세요.")
```

## 6. 추가 팁과 모범 사례

### 6.1 환경 변수 관리

MCP 서버와 LLM API 키와 같은 민감한 정보는 환경 변수로 관리하는 것이 좋습니다:

```python
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수 사용
api_key = os.getenv("VERTEX_API_KEY")
project_id = os.getenv("GCP_PROJECT_ID")
```

### 6.2 예외 처리

MCP 서버와의 통신에서 발생할 수 있는 예외를 적절히 처리해야 합니다:

```python
try:
    # MCP 도구 호출
    result = await self.session.call_tool(name=tool_name, arguments=tool_args)
    return result
except Exception as e:
    logger.error(f"도구 호출 오류: {str(e)}")
    return {"error": str(e)}
```

### 6.3 로깅

디버깅을 위해 자세한 로깅을 구현하는 것이 좋습니다:

```python
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

### 6.4 비동기 처리

MCP 통신은 비동기적으로 처리하는 것이 효율적입니다:

```python
async def process_query_async(self, query: str):
    # 비동기 처리 코드
    pass

def process_query(self, query: str):
    # 동기 래퍼
    return self.loop.run_until_complete(self.process_query_async(query))
```

## 요약

LangGraph와 MCP를 연동하면 다양한 외부 도구를 LLM 에이전트에 연결할 수 있습니다. 주요 단계는:

1. MCP 서버 구현: FastMCP를 사용하여 도구를 정의하고 stdio 모드로 실행
2. LangGraph 클라이언트 구현: MCP 도구를 로드하고 ReAct 에이전트와 통합
3. 사용자 쿼리 처리: 에이전트가 쿼리를 분석하고 적절한 도구를 호출
4. 결과 반환: 도구 실행 결과와 함께 최종 응답 제공

이러한 접근 방식을 통해 강력하고 유연한 AI 에이전트를 구축할 수 있습니다.
