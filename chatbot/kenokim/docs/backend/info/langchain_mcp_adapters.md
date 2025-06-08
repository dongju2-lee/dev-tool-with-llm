langchain-mcp-adapters는 LangGraph 에이전트가 MCP(Model Context Protocol) 도구를 활용할 수 있도록 돕는 Python 라이브러리입니다. 이 라이브러리는 LangGraph와 MCP 간의 중요한 연결 고리 역할을 하여 AI 에이전트의 상호 운용성을 강화합니다.
다음은 langchain-mcp-adapters를 활용하여 LangGraph가 MCP 도구를 사용하는 구조에 대한 간단한 설명입니다.

--------------------------------------------------------------------------------
를 활용한 LangGraph와 MCP 도구 연동 구조
langchain-mcp-adapters 라이브러리는 AI 모델(특히 LLM 에이전트)이 외부 도구, 시스템 및 데이터 소스와 안전하고 표준화된 방식으로 컨텍스트를 통합하고 공유하도록 설계된 개방형 프로토콜인 MCP를 LangChain 및 LangGraph 환경과 호환되도록 만듭니다.
이 연동 구조는 다음과 같은 핵심 단계와 구성 요소를 포함합니다:
•
MCP 서버: 먼저, 사용하고자 하는 도구(예: 숫자 연산, 날씨 정보 조회 등)를 MCP 서버로 노출합니다. 이 서버는 mcp.server.fastmcp.FastMCP를 사용하여 도구를 정의하고 mcp.run()을 통해 실행됩니다. LangGraph 서버 자체도 MCP를 구현하여 LangGraph 에이전트를 MCP 도구로 노출할 수 있습니다.
•
어댑터를 통한 도구 변환: langchain-mcp-adapters 라이브러리의 load_mcp_tools 함수는 MCP 서버에서 노출된 도구들을 LangChain과 LangGraph가 이해하고 사용할 수 있는 형식으로 변환합니다. 이 과정에서 MCP 클라이언트 세션(mcp.client.stdio.stdio_client 또는 mcp.client.streamable_http.streamablehttp_client)을 통해 MCP 서버와 통신하여 도구 정의를 가져옵니다. 또한, langchain-mcp-adapters.tools.to_fastmcp를 사용하여 LangChain 도구를 FastMCP 서버에 추가할 수도 있습니다.
•
LangGraph 에이전트의 도구 활용: 변환된 MCP 도구들은 LangGraph 에이전트 내에서 표준 LangChain 도구처럼 사용됩니다.
◦
ReAct 에이전트: langgraph.prebuilt.create_react_agent와 같이 미리 빌드된 ReAct 에이전트를 생성할 때, 변환된 tools 목록을 인자로 전달하여 에이전트가 해당 도구들을 활용할 수 있도록 합니다.
◦
StateGraph: langgraph.graph.StateGraph를 사용하여 그래프를 정의할 때는, 모델에 tools를 model.bind_tools(tools) 형태로 바인딩하고, ToolNode(tools)를 통해 도구 실행 노드를 추가할 수 있습니다.
•
다중 MCP 서버 지원: langchain-mcp-adapters.client.MultiServerMCPClient를 사용하면 여러 MCP 서버에 동시에 연결하여 각 서버에서 노출하는 도구들을 통합하여 사용할 수 있습니다. 이는 복잡한 AI 에이전트가 다양한 기능을 제공하는 여러 외부 서비스와 상호작용해야 할 때 유용합니다.
이러한 구조는 LangGraph로 구축된 에이전트가 MCP 생태계 내의 다른 시스템이나 도구와 상호작용할 수 있도록 돕는 중요한 역할을 하며, AI 에이전트의 상호 운용성과 모듈성을 크게 향상시킵니다.
코드 레벨에서 설명해줘 python 으로

langchain-mcp-adapters는 LangGraph로 구축된 AI 에이전트가 MCP(Model Context Protocol) 기반의 외부 도구와 상호작용할 수 있도록 돕는 Python 라이브러리입니다. 이는 AI 모델, 특히 LLM 에이전트가 외부 도구, 시스템, 데이터 소스와 컨텍스트를 안전하고 표준화된 방식으로 통합하고 공유하도록 설계된 MCP 프로토콜의 "AI 앱용 USB-C" 비유처럼, 에이전트의 상호 운용성을 크게 향상시킵니다.
이 연동은 크게 다음 단계로 이루어집니다:
1.
MCP 서버 구축: 사용할 도구를 MCP 프로토콜을 통해 노출하는 서버를 생성합니다.
2.
langchain-mcp-adapters를 통한 도구 로드: LangGraph 애플리케이션에서 MCP 서버에 연결하고 해당 도구들을 LangChain/LangGraph 호환 형식으로 변환합니다.
3.
LangGraph 에이전트에서 도구 활용: 로드된 도구를 LangGraph 에이전트(예: ReAct 에이전트, StateGraph)에 바인딩하여 사용합니다.

--------------------------------------------------------------------------------
1. MCP 서버 구축 (예: )
먼저, AI 에이전트가 사용할 기능을 MCP 도구로 노출하는 서버를 작성해야 합니다. 아래는 두 숫자를 더하거나 곱하는 간단한 수학 도구를 제공하는 MCP 서버의 예시입니다:
# math_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    mcp.run(transport="stdio") # 표준 입출력을 통해 서버를 실행 [1]
이 서버는 mcp.run(transport="stdio")를 통해 실행되며, 다른 프로세스가 표준 입출력을 통해 이 도구에 접근할 수 있게 합니다.
2. 를 통한 도구 로드
LangGraph 애플리케이션에서는 langchain_mcp_adapters.tools.load_mcp_tools 함수를 사용하여 MCP 서버에서 도구를 가져옵니다. 이때 mcp.client.stdio.stdio_client 또는 mcp.client.streamable_http.streamablehttp_client와 같은 MCP 클라이언트를 사용하여 서버와 연결합니다.
예시 1: 와 함께 사용
LangGraph의 미리 빌드된 ReAct 에이전트(create_react_agent)는 로드된 MCP 도구들을 바로 사용할 수 있습니다.
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

# MCP 서버 매개변수 정의
server_params = StdioServerParameters(
    command="python",
    args=["/path/to/math_server.py"], # math_server.py의 실제 경로로 변경
)

async def run_agent_with_mcp_tools():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # MCP 서버 연결 초기화
            await session.initialize()
            # MCP 도구 로드
            tools = await load_mcp_tools(session) # [1]
            
            # ReAct 에이전트 생성 및 도구 바인딩
            agent = create_react_agent("openai:gpt-4.1", tools) # [1]
            
            # 에이전트 실행
            agent_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"}) # [1]
            print(agent_response)

if __name__ == "__main__":
    asyncio.run(run_agent_with_mcp_tools())
여기서 **load_mcp_tools(session)**은 MCP 서버에서 노출된 add와 multiply 도구를 가져와 LangGraph 에이전트가 이해하고 사용할 수 있는 형식으로 변환합니다.
예시 2: 와 로 여러 서버 도구 활용
더 복잡한 시나리오에서는 langchain_mcp_adapters.client.MultiServerMCPClient를 사용하여 여러 MCP 서버에서 노출된 도구들을 한 번에 로드하고 StateGraph에 통합할 수 있습니다.
import asyncio
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient # [3]

# 모델 초기화
model = init_chat_model("openai:gpt-4.1") # [3]

# MultiServerMCPClient를 사용하여 여러 MCP 서버 정의 및 연결
client = MultiServerMCPClient({ # [3]
    "math": {
        "command": "python",
        "args": ["./examples/math_server.py"], # math_server.py의 실제 경로로 변경
        "transport": "stdio",
    },
    "weather": {
        "url": "http://localhost:8000/mcp", # 날씨 서버 URL (예시)
        "transport": "streamable_http",
    }
})

async def run_state_graph_with_mcp_tools():
    # 모든 MCP 도구 로드
    tools = await client.get_tools() # [3]
    
    # LangGraph의 모델 호출 노드 정의
    def call_model(state: MessagesState): # [3]
        # LLM에 로드된 도구 바인딩 (LLM이 어떤 도구를 사용할 수 있는지 알게 됨)
        response = model.bind_tools(tools).invoke(state["messages"]) # [3, 5]
        return {"messages": response}

    # StateGraph 빌더 생성
    builder = StateGraph(MessagesState) # [3]
    
    # 노드 추가
    builder.add_node("call_model", call_model) # 모델 호출 노드 [3]
    builder.add_node("tools", ToolNode(tools)) # 도구 실행 노드 [3, 6]
    
    # 엣지(흐름) 정의
    builder.add_edge(START, "call_model") # 시작 -> 모델 호출 [3]
    builder.add_conditional_edges(
        "call_model",
        tools_condition, # 모델이 도구 호출을 생성하면 "tools" 노드로 이동
        {"continue": "call_model", "tools": "tools"}, # [3] (여기서 END도 추가할 수 있음)
    )
    builder.add_edge("tools", "call_model") # 도구 실행 후 다시 모델 호출 (결과를 LLM에 전달) [3]
    
    # 그래프 컴파일 (Pregel 인스턴스 생성)
    graph = builder.compile() # [3, 7]
    
    # 그래프 실행 예시
    math_response = await graph.ainvoke({"messages": "what's (3 + 5) x 12?"}) # [3]
    print("Math Response:", math_response)
    
    weather_response = await graph.ainvoke({"messages": "what is the weather in nyc?"}) # [3]
    print("Weather Response:", weather_response)

if __name__ == "__main__":
    asyncio.run(run_state_graph_with_mcp_tools())
이 예시에서 각 코드 구성 요소의 역할은 다음과 같습니다:
•
MultiServerMCPClient: math_server (stdio)와 weather_server (HTTP) 두 개의 다른 MCP 서버에 대한 정보를 담고 있습니다. 이를 통해 두 서버의 도구를 동시에 로드할 수 있습니다.
•
model.bind_tools(tools): LLM(model)이 tools 변수에 포함된 모든 MCP 도구(add, multiply, 날씨 관련 도구 등)의 존재와 사용법을 인식하도록 합니다.
•
ToolNode(tools): LangGraph 그래프 내에서 LLM이 생성한 도구 호출을 실제로 실행하는 역할을 하는 노드입니다.
•
tools_condition: call_model 노드의 출력을 평가하여, LLM이 도구 호출을 요청했는지 여부에 따라 다음 노드를 결정하는 조건부 엣지입니다. 도구 호출이 있으면 tools 노드로, 그렇지 않으면 call_model 노드로 돌아가거나 END (최종 응답)로 이동합니다.
•
builder.compile(): 정의된 LangGraph 빌더(노드와 엣지)를 실행 가능한 Pregel 인스턴스로 변환하는 핵심 단계입니다. 이 컴파일된 그래프는 이제 상태를 유지하며 복잡한 워크플로우를 효율적으로 실행할 수 있습니다.

--------------------------------------------------------------------------------
3. LangGraph 에이전트에서 도구 활용
LangGraph는 LLM이 도구를 호출하고 그 결과를 워크플로우에 통합하는 방식을 유연하게 제어할 수 있도록 합니다. 이는 상태 저장(stateful) 다중 에이전트 앱을 **방향성 순환 그래프(DAG)**로 모델링하는 LangGraph의 강점을 활용합니다.
이 구조를 통해 LangGraph 에이전트는 다양한 외부 시스템 및 서비스에 원활하게 연결하고, 복잡한 작업을 자율적으로 수행하며, 그 과정에서 필요한 정보를 MCP 도구를 통해 동적으로 얻을 수 있습니다. 이는 AI 에이전트의 능력과 유용성을 크게 확장시키는 핵심 메커니즘입니다.