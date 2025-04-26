"""
MCP 서버 구현
"""
import json
import sys
import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional, Union, Tuple
import uuid

# FastAPI를 사용한 SSE 지원을 위해
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

class MCPTool:
    """MCP 도구 정의"""
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema

class GrafanaMCPServer:
    """MCP 서버 구현"""
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.tools: Dict[str, Tuple[MCPTool, Callable]] = {}
        self.app = FastAPI(title=f"{name} MCP Server")
        self._setup_sse_routes()
        
    def add_tool(self, tool: MCPTool, handler: Callable):
        """도구와 해당 핸들러 함수를 등록합니다."""
        self.tools[tool.name] = (tool, handler)
        logger.info(f"Tool registered: {tool.name}")
        
    def get_tools(self) -> List[MCPTool]:
        """등록된 모든 도구를 반환합니다."""
        return [tool for tool, _ in self.tools.values()]
    
    def _setup_sse_routes(self):
        """SSE 전송을 위한 라우트 설정"""
        @self.app.post("/v1/initialize")
        async def initialize(request: Request):
            data = await request.json()
            return self._handle_initialize(data)
        
        @self.app.post("/v1/list_tools")
        async def list_tools(request: Request):
            data = await request.json()
            return self._handle_list_tools(data)
        
        @self.app.post("/v1/call_tool")
        async def call_tool(request: Request):
            data = await request.json()
            return await self._handle_call_tool(data)
    
    def _handle_initialize(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """초기화 요청 처리"""
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "result": {
                "server_info": {
                    "name": self.name,
                    "version": self.version
                }
            }
        }
    
    def _handle_list_tools(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """도구 목록 요청 처리"""
        tools_data = []
        for tool_name, (tool, _) in self.tools.items():
            tools_data.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "result": {
                "tools": tools_data
            }
        }
    
    async def _handle_call_tool(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """도구 호출 요청 처리"""
        params = request_data.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }
        
        try:
            _, handler = self.tools[tool_name]
            # 비동기 또는 동기 핸들러 지원
            if asyncio.iscoroutinefunction(handler):
                result = await handler(arguments)
            else:
                result = handler(arguments)
                
            # 결과가 문자열이 아니면 JSON으로 직렬화
            if not isinstance(result, str):
                result = json.dumps(result)
                
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": {
                    "content": result
                }
            }
        except Exception as e:
            logger.exception(f"Error calling tool {tool_name}")
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "error": {
                    "code": -32000,
                    "message": f"Error calling tool: {str(e)}"
                }
            }
    
    async def _handle_stdin_stdout(self):
        """STDIO 전송을 사용한 요청/응답 처리"""
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                    
                request_data = json.loads(line)
                method = request_data.get("method")
                
                if method == "initialize":
                    response = self._handle_initialize(request_data)
                elif method == "list_tools":
                    response = self._handle_list_tools(request_data)
                elif method == "call_tool":
                    response = await self._handle_call_tool(request_data)
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_data.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                # 응답 전송
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON input")
            except Exception as e:
                logger.exception("Error processing request")
    
    async def start_stdio(self):
        """STDIO 전송을 사용하여 서버를 시작합니다."""
        logger.info("Starting MCP server with STDIO transport")
        await self._handle_stdin_stdout()
    
    def start_sse(self, host: str = "localhost", port: int = 8000):
        """SSE 전송을 사용하여 서버를 시작합니다."""
        logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port) 