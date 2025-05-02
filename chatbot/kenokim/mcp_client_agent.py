from contextlib import asynccontextmanager
import os
import logging
import traceback
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Gemini model
gemini_model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)

@asynccontextmanager
async def make_graph(
    client_name="mcp-server-test", 
    url="http://localhost:8000/sse", 
    transport="sse"
):
    """Creates a ReAct agent with the Gemini model and MCP tools if available
    
    Args:
        client_name: MCP 서버 클라이언트 이름
        url: MCP 서버 URL
        transport: MCP 서버 전송 방식 (sse, websocket 등)
    
    Yields:
        ReAct 에이전트
    """
    logger.info(f"Creating ReAct agent with Gemini model, connecting to {url}")
    try:
        async with MultiServerMCPClient(
            {
                client_name: {
                    "url": url,
                    "transport": transport
                }
            }
        ) as client:
            # Create agent with MCP tools
            agent = create_react_agent(gemini_model, client.get_tools())
            yield agent
    except Exception as e:
        logger.error(f"Error creating ReAct agent: {str(e)}")
        logger.error(traceback.format_exc())

# 간단한 사용 예시
async def simple_test():
    """Simple test function to verify the agent works"""
    async with make_graph() as agent:
        result = await agent.ainvoke({"messages": [HumanMessage(content="서버 상태 정보를 알려주세요.")]})
        print(f"결과: {result}")
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(simple_test())
    