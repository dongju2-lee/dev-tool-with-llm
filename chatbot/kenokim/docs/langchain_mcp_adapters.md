LangGraph와 MCP 연동 개요
MCP 서버는 외부 도구(예: 수학 계산, 날씨 조회 등)를 표준 프로토콜로 노출하는 경량 서버입니다.

LangChain-MCP-Adapters가 MCP 서버와 통신하여 MCP 도구들을 LangChain/LangGraph가 이해하는 도구(BaseTool)로 자동 변환해 줍니다.

LangGraph는 이렇게 변환된 도구를 ReAct 에이전트 등 워크플로우에 통합해 사용할 수 있습니다.

간단한 연동 예시
1) MCP 서버 (math_server.py)
python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    return a * b

if __name__ == "__main__":
    mcp.run(transport="stdio")
2) LangGraph 클라이언트 (client_app.py)
python
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

math_server_script_path = os.path.join(os.path.dirname(__file__), "math_server.py")

async def main():
    model = ChatOpenAI(model="gpt-4o")

    server_params = StdioServerParameters(
        command="python",
        args=[math_server_script_path],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(model, tools)

            inputs = {"messages": [("human", "what's (3 + 5) * 12?")]}
            async for event in agent.astream_events(inputs, version="v1"):
                print(event)

if __name__ == "__main__":
    asyncio.run(main())
주요 특징
MCP 서버와의 통신은 stdio(표준입출력) 또는 sse(서버 전송 이벤트) 방식 지원

여러 MCP 서버를 동시에 연결 가능 (MultiServerMCPClient 사용)

LangGraph API 서버 환경에서도 MCP 도구 사용 가능

MCP 도구를 UI에서 동적으로 추가/제거 및 관리하는 Streamlit 인터페이스 제공 프로젝트도 존재