"""
MCP 도구 구현을 위한 기본 클래스
"""
from typing import Dict, Any, Callable, TypeVar, Generic, Type, Optional, get_type_hints
from pydantic import BaseModel, create_model, Field
import inspect
import json
import logging
from ..server import MCPTool

logger = logging.getLogger("mcp-tools")

T = TypeVar('T', bound=BaseModel)
R = TypeVar('R')

class Tool(Generic[T, R]):
    """MCP 도구 구현을 위한 기본 클래스."""
    
    def __init__(self, name: str, description: str, param_model: Type[T], handler: Callable[[Dict[str, Any]], R]):
        self.name = name
        self.description = description
        self.param_model = param_model
        self.handler = handler
        
    def to_mcp_tool(self) -> MCPTool:
        """MCP 도구 정의로 변환합니다."""
        # pydantic 모델에서 JSON 스키마 생성
        schema = self.param_model.model_json_schema()
        
        # MCP 도구 형식으로 변환
        return MCPTool(
            name=self.name,
            description=self.description,
            input_schema=schema
        )
        
    def handle(self, args: Dict[str, Any]) -> R:
        """매개변수로 도구 호출을 처리합니다."""
        try:
            # pydantic을 사용하여 매개변수 파싱
            parsed_params = self.param_model(**args)
            
            # 핸들러 호출
            return self.handler(parsed_params.model_dump())
        except Exception as e:
            logger.exception(f"Error handling tool {self.name}")
            raise

def create_tool(name: str, description: str, handler: Callable) -> Tool:
    """
    함수로부터 도구를 생성합니다.
    
    Args:
        name: 도구 이름
        description: 도구 설명
        handler: 핸들러 함수
        
    Returns:
        생성된 도구
    """
    # 함수 시그니처 검사
    sig = inspect.signature(handler)
    if len(sig.parameters) != 1:
        raise ValueError(f"Handler function {handler.__name__} must have exactly one parameter")
    
    # 함수의 첫 번째 매개변수 타입
    param_name = list(sig.parameters.keys())[0]
    
    # 함수 주석에서 매개변수 모델 정보 추출
    type_hints = get_type_hints(handler)
    if param_name not in type_hints:
        raise ValueError(f"Handler function {handler.__name__} must have type annotations")
    
    param_type = type_hints[param_name]
    
    # pydantic 모델인지 확인
    if not hasattr(param_type, 'model_json_schema'):
        raise ValueError(f"Parameter type for {handler.__name__} must be a Pydantic model")
    
    # 도구 생성
    return Tool(
        name=name,
        description=description,
        param_model=param_type,
        handler=handler
    ) 