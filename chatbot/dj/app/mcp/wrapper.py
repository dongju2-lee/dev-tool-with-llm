"""
MCP(Model Context Protocol) 서버 래퍼 모듈

이 모듈은 MCP 서버와의 상호작용을 위한 클래스와 함수를 제공합니다.
전략 패턴을 사용하여 다양한 작업(라우팅 정보 가져오기, 도구 가져오기, 도구 실행 등)을 추상화합니다.
"""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    # MCP 라이브러리 임포트 시도
    from mcp import stdio_client
    from mcp.server_info import ServerInfo
    HAS_MCP = True
except ImportError:
    logger.warning("MCP 라이브러리를 찾을 수 없습니다. 가상 구현을 사용합니다.")
    HAS_MCP = False


class MCPSessionFunction(ABC):
    """MCP 세션 함수를 위한 추상 기본 클래스"""
    
    @abstractmethod
    async def __call__(self, server_name: str, session: Any) -> Any:
        """
        MCP 세션에서 작업을 실행합니다.
        
        Args:
            server_name: MCP 서버 이름
            session: MCP 세션 객체
            
        Returns:
            다양한 작업 결과
        """
        pass


class RoutingDescription(MCPSessionFunction):
    """MCP 서버의 라우팅 정보를 가져오기 위한 함수"""
    
    async def __call__(self, server_name: str, session: Any) -> str:
        """
        도구, 프롬프트, 리소스를 기반으로 라우팅 정보를 가져옵니다.
        
        Args:
            server_name: MCP 서버 이름
            session: MCP 세션 객체
            
        Returns:
            str: 라우팅 정보 문자열
        """
        if not HAS_MCP:
            return f"가상 MCP 서버 '{server_name}'의 라우팅 정보"
        
        server_info = ServerInfo(session)
        tools = await server_info.tools()
        
        # 도구 설명 추출
        tools_description = []
        for tool in tools:
            tools_description.append(
                f"Tool Name: {tool.name}\n"
                f"Description: {tool.description}\n"
                f"Parameters: {json.dumps(tool.parameters)}"
            )
        
        tools_text = "\n\n".join(tools_description)
        return f"# MCP Server: {server_name}\n\n## Tools:\n\n{tools_text}"


class GetTools(MCPSessionFunction):
    """MCP 서버에서 도구 목록을 가져오는 함수"""
    
    async def __call__(self, server_name: str, session: Any) -> List[Dict[str, Any]]:
        """
        MCP 서버의 도구 목록을 가져와 LangGraph가 사용할 수 있는 형식으로 변환합니다.
        
        Args:
            server_name: MCP 서버 이름
            session: MCP 세션 객체
            
        Returns:
            List[Dict[str, Any]]: LangGraph 호환 도구 목록
        """
        if not HAS_MCP:
            # 가상 도구 반환
            return [
                {
                    "type": "function",
                    "function": {
                        "name": f"{server_name}_virtual_tool",
                        "description": f"{server_name} 서버의 가상 도구",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "도구에 전달할 쿼리"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]
        
        server_info = ServerInfo(session)
        tools = await server_info.tools()
        
        # MCP 도구를 LangGraph 호환 형식으로 변환
        langgraph_tools = []
        for tool in tools:
            langgraph_tools.append({
                "type": "function",
                "function": {
                    "name": f"{server_name}_{tool.name}",
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        
        return langgraph_tools


class RunTool(MCPSessionFunction):
    """MCP 서버에서 도구를 실행하는 함수"""
    
    def __init__(self, tool_name: str, tool_args: Dict[str, Any]):
        """
        Args:
            tool_name: 실행할 도구 이름
            tool_args: 도구에 전달할 인수
        """
        self.tool_name = tool_name
        self.tool_args = tool_args
    
    async def __call__(self, server_name: str, session: Any) -> Any:
        """
        MCP 서버에서 도구를 실행하고 결과를 반환합니다.
        
        Args:
            server_name: MCP 서버 이름
            session: MCP 세션 객체
            
        Returns:
            Any: 도구 실행 결과
        """
        if not HAS_MCP:
            return {
                "result": f"가상 도구 '{self.tool_name}' 실행 결과",
                "args": self.tool_args
            }
        
        # 실제 MCP 도구 호출
        try:
            result = await session.call(self.tool_name, self.tool_args)
            return result
        except Exception as e:
            logger.error(f"도구 실행 중 오류 발생: {e}")
            return {"error": str(e)}


async def apply(server_name: str, config: Dict[str, Any], fn: MCPSessionFunction) -> Any:
    """
    MCP 서버에 함수를 적용합니다.
    
    Args:
        server_name: MCP 서버 이름
        config: MCP 서버 구성
        fn: 적용할 MCPSessionFunction
        
    Returns:
        Any: 함수 실행 결과
    """
    if not HAS_MCP:
        # MCP 라이브러리 없이 가상 세션 사용
        return await fn(server_name, None)
    
    # 실제 MCP 세션 생성 및 함수 적용
    try:
        async with stdio_client(
            cmd=config.get("command"),
            args=config.get("args", []),
            transport=config.get("transport", "stdio")
        ) as session:
            return await fn(server_name, session)
    except Exception as e:
        logger.error(f"MCP 세션 생성 중 오류 발생: {e}")
        return {"error": str(e)}


class MCPTools:
    """MCP 도구 관리 클래스"""
    
    def __init__(self, config_path: str = "mcp_tools_config.json"):
        """
        Args:
            config_path: MCP 도구 구성 파일 경로
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """구성 파일에서 MCP 도구 설정을 로드합니다."""
        if not os.path.exists(self.config_path):
            return {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"MCP 도구 구성 로드 중 오류 발생: {e}")
            return {}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        MCP 도구 구성을 저장합니다.
        
        Args:
            config: 저장할 구성
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.config = config
            return True
        except Exception as e:
            logger.error(f"MCP 도구 구성 저장 중 오류 발생: {e}")
            return False
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        서버 이름으로 서버 구성을 가져옵니다.
        
        Args:
            server_name: MCP 서버 이름
            
        Returns:
            Optional[Dict[str, Any]]: 서버 구성 또는 None
        """
        return self.config.get(server_name)
    
    async def get_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """
        MCP 서버의 도구 목록을 가져옵니다.
        
        Args:
            server_name: MCP 서버 이름
            
        Returns:
            List[Dict[str, Any]]: 도구 목록
        """
        server_config = self.get_server_config(server_name)
        if not server_config:
            logger.error(f"서버 '{server_name}'에 대한 구성을 찾을 수 없습니다.")
            return []
        
        return await apply(server_name, server_config, GetTools())
    
    async def run_tool(self, server_name: str, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        MCP 서버에서 도구를 실행합니다.
        
        Args:
            server_name: MCP 서버 이름
            tool_name: 실행할 도구 이름
            tool_args: 도구에 전달할 인수
            
        Returns:
            Any: 도구 실행 결과
        """
        server_config = self.get_server_config(server_name)
        if not server_config:
            logger.error(f"서버 '{server_name}'에 대한 구성을 찾을 수 없습니다.")
            return {"error": f"서버 '{server_name}'에 대한 구성을 찾을 수 없습니다."}
        
        return await apply(server_name, server_config, RunTool(tool_name, tool_args)) 