import os
import asyncio
import json
from typing import Literal, List, Dict, Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import MessagesState
from langgraph.types import Command
from langchain_google_vertexai import ChatVertexAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = setup_logger("mcp_agent", level=LOG_LEVEL)


class MCPClient:
    """MCP 클라이언트 클래스"""
    
    def __init__(self):
        """클라이언트 초기화"""
        self.client = None
        self.config = {
            "weather_service": {
                "url": "http://0.0.0.0:8011/sse",
                "transport": "sse"
            }
        }
        logger.info(f"MCP 클라이언트 설정: {json.dumps(self.config, indent=2)}")
    
    async def initialize(self) -> MultiServerMCPClient:
        """MCP 클라이언트를 초기화하고 연결합니다."""
        if self.client is None:
            logger.info("MCP 클라이언트 초기화 시작")
            
            try:
                # MCP 클라이언트 생성
                logger.info("MCP 클라이언트 생성 중...")
                self.client = MultiServerMCPClient(self.config)
                logger.info("MCP 클라이언트 인스턴스 생성 완료")
                
                # MCP 클라이언트 연결
                logger.info("MCP 서버에 연결 시도 중...")
                await self.client.__aenter__()
                logger.info("MCP 서버 연결 성공")
                
                logger.info("MCP 클라이언트 초기화 완료")
            except Exception as e:
                logger.error(f"MCP 클라이언트 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.client
    
    async def get_tools(self) -> List:
        """MCP 도구를 가져오고 상세 정보를 로깅합니다."""
        # 클라이언트 초기화
        client = await self.initialize()
        
        logger.info("MCP 도구 가져오는 중...")
        tools = client.get_tools()
        
        # 도구 정보 로깅
        logger.info(f"총 {len(tools)}개의 MCP 도구를 가져왔습니다")
        for i, tool in enumerate(tools, 1):
            try:
                tool_name = getattr(tool, "name", f"Tool-{i}")
                tool_desc = getattr(tool, "description", "설명 없음")
                logger.info(f"  도구 {i}: {tool_name} - {tool_desc}")
            except Exception as e:
                logger.warning(f"  도구 {i}의 정보를 가져오는 중 오류: {str(e)}")
        
        return tools
    
    async def close(self):
        """MCP 클라이언트 연결을 닫습니다."""
        if self.client is not None:
            try:
                await self.client.__aexit__(None, None, None)
                logger.info("MCP 클라이언트 연결 종료")
                self.client = None
            except Exception as e:
                logger.error(f"MCP 클라이언트 연결 종료 중 오류 발생: {str(e)}")


class MCPAgent:
    """MCP 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        self.agent = None
        self.mcp_client = MCPClient()
        
        # 모델 설정 가져오기
        self.model_name = os.environ.get("MCP_AGENT_MODEL", "gemini-2.0-flash")
        logger.info(f"MCP 에이전트 LLM 모델: {self.model_name}")
    
    async def initialize(self):
        """MCP 에이전트를 초기화합니다."""
        if self.agent is None:
            logger.info("MCP 에이전트 초기화 시작")
            
            try:
                # LLM 초기화
                logger.info("LLM 초기화 중...")
                llm = ChatVertexAI(
                    model=self.model_name,
                    temperature=0.1,
                    max_output_tokens=8000
                )
                logger.info("LLM 초기화 완료")
                
                # MCP 클라이언트 및 도구 가져오기
                logger.info("MCP 도구 로딩 중...")
                tools = await self.mcp_client.get_tools()
                logger.info("MCP 도구 로딩 완료")
                
                # 시스템 프롬프트 설정
                logger.info("시스템 프롬프트 구성 중...")
                system_prompt = ChatPromptTemplate.from_messages([
                    ("system", """당신은 MCP 에이전트입니다. 
다양한 MCP 도구를 사용하여 사용자의 요청을 처리할 수 있습니다.

응답은 항상 한국어로 제공하세요. 제공된 MCP 도구를 사용하여 사용자 질문에 대한 정보를 검색하고 답변하세요."""),
                    MessagesPlaceholder(variable_name="messages")
                ])
                
                logger.info("시스템 프롬프트 설정 완료")
                
                # ReAct 에이전트 생성
                logger.info("ReAct 에이전트 생성 중...")
                self.agent = create_react_agent(
                    llm, 
                    tools, 
                    prompt=system_prompt
                )
                logger.info("ReAct 에이전트 생성 완료")
                
                logger.info("MCP 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"MCP 에이전트 초기화 중 오류 발생: {str(e)}")
                raise
        
        return self.agent
    
    async def __call__(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        """
        MCP 에이전트 호출 메서드입니다.
        
        Args:
            state: 현재 메시지와 상태 정보
            
        Returns:
            슈퍼바이저로 돌아가는 명령
        """
        try:
            # 에이전트 인스턴스 가져오기
            logger.info("MCP 에이전트 호출 시작")
            agent = await self.initialize()
            
            # 입력 메시지 로깅
            if "messages" in state and state["messages"]:
                last_user_msg = state["messages"][-1].content
                logger.info(f"MCP 에이전트에 전달된 메시지: '{last_user_msg[:1000]}...'")
            
            # 에이전트 호출
            logger.info("MCP 에이전트 추론 시작")
            result = await agent.ainvoke(state)
            logger.info("MCP 에이전트 추론 완료")
            
            # 결과 메시지 생성
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                mcp_agent_message = HumanMessage(content=last_message.content, name="mcp_agent")
                logger.info(f"MCP 에이전트 응답: '{last_message.content[:1000]}...'")
            else:
                logger.warning("MCP 에이전트가 응답을 생성하지 않음")
                mcp_agent_message = HumanMessage(content="응답을 생성할 수 없습니다.", name="mcp_agent")
            
            logger.info("MCP 에이전트 작업 완료, 슈퍼바이저로 반환")
            
            # 슈퍼바이저로 돌아가기
            return Command(
                update={"messages": [mcp_agent_message]},
                goto="supervisor"
            )
        except Exception as e:
            logger.error(f"MCP 에이전트 호출 중 오류 발생: {str(e)}")
            error_message = HumanMessage(
                content=f"MCP 에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                name="mcp_agent"
            )
            return Command(
                update={"messages": [error_message]},
                goto="supervisor"
            )


# MCP 에이전트 인스턴스 생성
mcp_agent = MCPAgent()

# mcp_agent_node 함수는 MCPAgent 인스턴스를 호출하는 래퍼 함수
async def mcp_agent_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    """
    MCP 에이전트 노드 함수입니다. MCPAgent 인스턴스를 호출합니다.
    
    Args:
        state: 현재 메시지와 상태 정보
        
    Returns:
        슈퍼바이저로 돌아가는 명령
    """
    return await mcp_agent(state) 