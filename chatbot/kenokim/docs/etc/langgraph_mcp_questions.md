Q). MCP 서버는 (Python) 어떻게 띄우는지? 서브프로세스 / 도커 등등 설명, 또는 더 있는지?

A). Python에서 MCP 서버를 띄우는 방법은 다양합니다:

1. **FastMCP를 사용한 기본 서버 구현** (출처: [Python SDK, modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)):
   ```python
   from mcp.server.fastmcp import FastMCP
   import logging

   # 로깅 설정
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   # FastMCP 서버 생성
   mcp = FastMCP(
       "ServiceName",  # 서비스 이름 지정
       debug=True,     # 디버그 모드 (옵션)
   )

   # 도구 정의
   @mcp.tool()
   def sample_tool(param1: str, param2: int) -> str:
       """도구 설명
       
       Args:
           param1: 첫 번째 매개변수 설명
           param2: 두 번째 매개변수 설명
           
       Returns:
           반환값 설명
       """
       logger.info(f"도구 호출: {param1}, {param2}")
       return f"결과: {param1}, {param2}"

   if __name__ == "__main__":
       # stdio 모드로 서버 실행
       try:
           logger.info("MCP 서버 시작...")
           mcp.run(transport="stdio")
       except Exception as e:
           logger.error(f"서버 오류: {str(e)}")
   ```

2. **서브프로세스 방식** (출처: [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/docs/concepts/architecture)):
   - 가장 일반적인 방법으로, 클라이언트가 서버 스크립트를 서브프로세스로 실행합니다.
   - 클라이언트와 서버는 stdio(표준 입출력)를 통해 통신합니다.
   - 서버 스크립트 종료 시 서브프로세스도 자동으로 종료됩니다.
   - 예시:
     ```python
     # 클라이언트 측에서 서브프로세스로 MCP 서버 실행
     from mcp import ClientSession, StdioServerParameters
     from mcp.client.stdio import stdio_client
     
     async def start_server():
         server_params = StdioServerParameters(
             command="python",
             args=["server_script.py"],
         )
         read, write = await stdio_client(server_params)
         session = await ClientSession(read, write)
         await session.initialize()
         return session
     ```

3. **도커 컨테이너** (출처: [MCP Servers 리포지토리](https://github.com/modelcontextprotocol/servers), 2025-01-03 업데이트):
   - 공식 MCP 서버 리포지토리는 도커화된 MCP 서버를 제공합니다.
   - 이점:
     - 의존성 관리 간소화
     - 환경 격리
     - 배포 용이성
   - 사용 방법:
     ```bash
     # 도커 이미지 빌드
     docker build -t my-mcp-server .
     
     # 도커 컨테이너 실행
     docker run -p 3000:3000 my-mcp-server
     ```
   - Dockerfile 예시:
     ```dockerfile
     FROM python:3.11-slim
     
     WORKDIR /app
     COPY requirements.txt .
     RUN pip install --no-cache-dir -r requirements.txt
     
     COPY . .
     
     CMD ["python", "math_server.py"]
     ```

4. **HTTP/WebSocket 서버 모드** (출처: [MCP 2025-03-26 명세](https://modelcontextprotocol.io/specification/2025-03-26/)):
   - stdio 외에도 HTTP/WebSocket을 통한 실행도 가능합니다:
     ```python
     if __name__ == "__main__":
         # HTTP/WebSocket 서버로 실행
         mcp.run(transport="http", port=3000)
     ```
   - 이 방식은 원격 서버 연결이나 클라우드 배포에 적합합니다.

5. **IDE 및 호스트 통합** (출처: [MCP 공식 문서](https://modelcontextprotocol.io/docs/concepts/architecture)):
   - Claude Desktop, VS Code 등 MCP를 지원하는 호스트 애플리케이션 내에서 직접 실행 가능
   - 호스트 애플리케이션이 서버를 자동으로 관리하고 실행합니다.

Q). MCP 클라이언트 <-> 서버는 어떻게 통신하는지? 통신 방식?

A). MCP 클라이언트와 서버 간 통신 방식에 대한 설명 (출처: [MCP 공식 문서](https://modelcontextprotocol.io/docs/concepts/architecture) 및 [2025-03-26 프로토콜 명세](https://modelcontextprotocol.io/specification/2025-03-26/)):

1. **기본 통신 프로토콜**:
   - MCP는 **JSON-RPC 2.0** 기반 프로토콜을 사용합니다.
   - 현재 프로토콜 버전: **2025-03-26** (출처: [MCP 버전 정보](https://modelcontextprotocol.io/specification/2025-03-26/))
   - 버전 형식: `YYYY-MM-DD` (마지막 하위 호환성을 깨는 변경이 이루어진 날짜)

2. **지원되는 통신 방식** (Transport Layer):
   - **stdio (표준 입출력)**: 가장 일반적인 방식, 서브프로세스를 통한 통신
   - **HTTP/WebSocket**: 네트워크를 통한 원격 통신
   - **IPC (프로세스 간 통신)**: 일부 SDK에서 지원

3. **통신 흐름** (출처: [MCP 공식 문서](https://modelcontextprotocol.io/tutorials/building-mcp-with-llms) 및 코드 예제):
   ```
   클라이언트 → 서버 연결 초기화 → 버전 협상 → 세션 설정 → 
   도구/리소스 목록 요청 → 도구 호출/리소스 요청 → 결과 반환 → 종료
   ```

4. **파이썬 구현 예시** (출처: [Python SDK](https://github.com/modelcontextprotocol/python-sdk)):
   ```python
   # 클라이언트 측 코드
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client
   import asyncio

   async def connect_to_server(server_script_path):
       # 서버 파라미터 설정
       server_params = StdioServerParameters(
           command="python",  # 실행 명령어
           args=[server_script_path],  # 서버 스크립트 경로
       )
       
       # stdio 클라이언트 생성
       read, write = await stdio_client(server_params)
       
       # 세션 생성 및 초기화
       session = await ClientSession(read, write)
       await session.initialize()
       
       # 도구 목록 조회
       tools = await session.list_tools()
       print(f"사용 가능한 도구: {[tool.name for tool in tools.tools]}")
       
       # 도구 호출
       result = await session.call_tool(
           name="add", 
           arguments={"a": 5, "b": 3}
       )
       print(f"도구 호출 결과: {result}")
       
       # 세션 종료
       await session.close()
   
   # 실행
   asyncio.run(connect_to_server("math_server.py"))
   ```

5. **메시지 형식 예시** (출처: [MCP 프로토콜 명세](https://modelcontextprotocol.io/specification/2025-03-26/)):
   - **초기화 요청 (클라이언트 → 서버)**:
     ```json
     {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "initialize",
       "params": {
         "clientInfo": {
           "name": "MCP Example Client",
           "version": "1.0.0"
         },
         "capabilities": {
           "protocol": {
             "versions": ["2025-03-26"]
           }
         }
       }
     }
     ```
   - **초기화 응답 (서버 → 클라이언트)**:
     ```json
     {
       "jsonrpc": "2.0",
       "id": 1,
       "result": {
         "serverInfo": {
           "name": "Math Server",
           "version": "1.0.0"
         },
         "capabilities": {
           "protocol": {
             "version": "2025-03-26"
           }
         }
       }
     }
     ```

6. **오류 처리** (출처: [MCP 프로토콜 명세](https://modelcontextprotocol.io/specification/2025-03-26/)):
   - 통신 오류는 JSON-RPC 오류 형식으로 반환됩니다.
   - 예시:
     ```json
     {
       "jsonrpc": "2.0",
       "id": 2,
       "error": {
         "code": -32602,
         "message": "Invalid params",
         "data": {
           "details": "Parameter 'b' cannot be zero for division operation"
         }
       }
     }
     ```

Q). LangGraph 에서 붙으려면 어떻게 하는지?

A). LangGraph와 MCP 서버 연동 방법 (출처: [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/) 및 [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)):

1. **필요한 패키지 설치**:
   ```bash
   pip install langgraph>=0.4.1 langchain-core>=0.1.28 langchain-mcp-adapters>=0.0.9 mcp>=1.6.0
   ```

2. **LangGraph와 MCP 통합 과정**:

   a. **MCP 세션 설정** (출처: [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)):
   ```python
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client
   
   async def initialize_session(server_script_path):
       server_params = StdioServerParameters(
           command="python",
           args=[server_script_path],
       )
       
       read, write = await stdio_client(server_params)
       session = await ClientSession(read, write)
       await session.initialize()
       
       return session
   ```

   b. **MCP 도구를 LangChain 도구로 변환** (출처: [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)):
   ```python
   from langchain_mcp_adapters.tools import load_mcp_tools
   
   async def load_tools(session):
       # MCP 서버의 도구를 LangChain 도구로 변환
       tools = await load_mcp_tools(session)
       return tools
   ```

   c. **LangGraph ReAct 에이전트 생성** (출처: [LangGraph 문서](https://langchain-ai.github.io/langgraph/)):
   ```python
   from langgraph.prebuilt import create_react_agent
   from langgraph.checkpoint import InMemoryCheckpointer
   from langchain_google_vertexai import ChatVertexAI
   
   async def setup_agent(tools, model_name="gemini-1.5-flash"):
       # LLM 설정
       llm = ChatVertexAI(
           model_name=model_name,
           max_output_tokens=1024,
           temperature=0.1,
       )
       
       # ReAct 에이전트 생성 (LangGraph 0.4.1 이상 버전 기준)
       agent = create_react_agent(
           llm=llm,
           tools=tools,
           system_message="당신은 MCP 도구를 사용하는 AI 에이전트입니다."
       )
       
       # 체크포인터 설정
       checkpointer = InMemoryCheckpointer()
       
       # 설정 적용
       return agent.with_config({"checkpointer": checkpointer})
   ```

3. **통합 클래스 구현** (LangGraph와 MCP 통합 예시):
   ```python
   import asyncio
   from typing import List, Dict, Any, Optional
   from langchain_core.messages import HumanMessage
   
   class MCPLangGraphClient:
       def __init__(self, server_script_path, model_name="gemini-1.5-flash"):
           self.server_script_path = server_script_path
           self.model_name = model_name
           self.session = None
           self.agent = None
           self.tools = []
           self.loop = asyncio.new_event_loop()
           asyncio.set_event_loop(self.loop)
           
       def initialize(self):
           """클라이언트 초기화"""
           self.loop.run_until_complete(self._initialize_async())
       
       async def _initialize_async(self):
           self.session = await initialize_session(self.server_script_path)
           self.tools = await load_tools(self.session)
           self.agent = await setup_agent(self.tools, self.model_name)
           
       def process_query(self, query: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
           """쿼리 처리"""
           return self.loop.run_until_complete(
               self._process_query_async(query, thread_id)
           )
       
       async def _process_query_async(self, query: str, thread_id: Optional[str] = None):
           messages = [HumanMessage(content=query)]
           
           # 에이전트 실행
           config = {}
           if thread_id:
               config["configurable"] = {"thread_id": thread_id}
               
           response = await self.agent.ainvoke(
               {"messages": messages}, 
               config=config
           )
           
           return response
           
       def close(self):
           """세션 종료"""
           if self.session:
               self.loop.run_until_complete(self.session.close())
   ```

4. **사용 예시** (LangGraph와 MCP 통합 사용 방법):
   ```python
   # 클라이언트 생성 및 초기화
   client = MCPLangGraphClient("math_server.py")
   client.initialize()
   
   try:
       # 쿼리 처리
       result = client.process_query("15와 27을 더하고 결과를 3으로 나누세요.")
       print(result)
   finally:
       # 세션 종료
       client.close()
   ```

5. **LangGraph 통합의 핵심 장점** (출처: [LangGraph 문서](https://langchain-ai.github.io/langgraph/)):
   - **상태 관리**: LangGraph는 대화 상태를 관리하는 기능 제공
   - **흐름 제어**: 복잡한 추론 흐름을 그래프로 모델링 가능
   - **도구 통합**: MCP 도구를 LangChain 에코시스템과 쉽게 통합

Q). ReAct 패턴이란? MCP 서버랑 무슨 연관?

A). ReAct 패턴과 MCP 서버의 연관성 (출처: [LangGraph 문서](https://langchain-ai.github.io/langgraph/) 및 [MCP 공식 문서](https://modelcontextprotocol.io/docs/concepts/architecture)):

1. **ReAct 패턴 설명** (출처: [LangGraph 문서](https://langchain-ai.github.io/langgraph/)):
   - ReAct = **Re**asoning + **Act**ion (추론 + 행동)
   - 이 패턴은 LLM의 사고 과정을 다음과 같은 단계로 구조화합니다:
     1. **사고(Thought)**: 문제 분석 및 해결 전략 수립
     2. **행동(Action)**: 적절한 도구 선택 및 호출
     3. **관찰(Observation)**: 도구 실행 결과 분석
     4. **반복**: 최종 해결책을 찾을 때까지 위 과정 반복
   - 이 접근 방식은 LLM이 복잡한 문제를 단계별로 해결하는 데 효과적입니다.

2. **ReAct와 MCP 서버의 연관성** (출처: [MCP 공식 문서](https://modelcontextprotocol.io/docs/concepts/architecture)):
   - **도구 제공자로서의 MCP 서버**: 
     - MCP 서버는 ReAct 패턴의 '행동(Action)' 단계에서 LLM이 호출할 수 있는 도구들을 제공합니다.
     - 각 도구는 명확한 입출력 스키마와 설명을 가지고 있어 LLM이 쉽게 이해하고 활용할 수 있습니다.
   
   - **표준화된 인터페이스**:
     - MCP는 도구 호출을 위한 일관된 인터페이스를 제공합니다.
     - 이를 통해 ReAct 에이전트는 서로 다른 MCP 서버가 제공하는 다양한 도구를 동일한 방식으로 호출할 수 있습니다.
   
   - **통합 흐름** (출처: [MCP 튜토리얼](https://modelcontextprotocol.io/tutorials/building-mcp-with-llms)):
     ```
     사용자 질문 → LLM 추론(Thought) → 
     도구 선택(Action) → MCP 서버에 도구 호출 → 
     결과 수신(Observation) → 최종 응답 생성
     ```

3. **LangGraph에서의 ReAct 구현** (출처: [LangGraph 문서](https://langchain-ai.github.io/langgraph/)):
   - LangGraph는 `create_react_agent()` 함수를 통해 ReAct 패턴을 구현합니다:
     ```python
     from langgraph.prebuilt import create_react_agent
     
     agent = create_react_agent(
         llm=llm,
         tools=tools,  # MCP 도구들
         system_message="지시사항..." 
     )
     ```
   - 이 에이전트는 다음과 같은 기능을 자동으로 처리합니다:
     - 도구 선택 로직
     - JSON 형식의 도구 호출 매개변수 생성
     - 도구 실행 결과 처리 및 분석
     - 다음 단계 결정

4. **실제 동작 예시** (출처: [LangGraph 문서](https://langchain-ai.github.io/langgraph/) 및 [MCP 예제](https://github.com/modelcontextprotocol/servers)):
   
   사용자 쿼리: "15와 27을 더한 후 3으로 나누세요."
   
   ```
   # 1단계: LLM 추론 (Thought)
   이 문제는 두 숫자를 더한 후 결과를 나누는 수학 연산입니다.
   먼저 15와 27을 더한 다음, 그 결과를 3으로 나누어야 합니다.
   MCP 서버의 도구를 사용해 이 연산을 수행하겠습니다.
   
   # 2단계: 도구 선택 (Action)
   도구 선택: "add"
   매개변수: {"a": 15, "b": 27}
   
   # 3단계: 도구 실행 결과 (Observation)
   결과: 42
   
   # 4단계: 다음 추론 (Thought)
   이제 42를 3으로 나눠야 합니다.
   
   # 5단계: 도구 선택 (Action)
   도구 선택: "divide"
   매개변수: {"a": 42, "b": 3}
   
   # 6단계: 도구 실행 결과 (Observation)
   결과: 14.0
   
   # 7단계: 최종 응답 생성
   15와 27을 더하면 42가 되고, 42를 3으로 나누면 답은 14입니다.
   ```

5. **MCP와 ReAct 통합의 이점** (출처: [MCP 공식 문서](https://modelcontextprotocol.io/docs/concepts/architecture)):
   - **확장성**: MCP 서버에 새로운 도구를 추가하면 ReAct 에이전트가 즉시 활용할 수 있습니다.
   - **모듈성**: MCP 서버와 LLM 로직이 분리되어 독립적으로 개발 및 개선 가능합니다.
   - **표준화**: 모든 도구가 일관된 인터페이스를 통해 호출되므로 에이전트 구현이 단순해집니다.
   - **재사용성**: 여러 LLM 애플리케이션에서 동일한 MCP 서버를 활용할 수 있습니다.

Q). 