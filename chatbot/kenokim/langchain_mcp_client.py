"""
Gemini 모델을 사용한 LangChain MCP Adapters 클라이언트

이 모듈은 langchain-mcp-adapters를 사용하여 MCP 서버와 LangGraph를 연동하고,
Gemini 모델을 사용하여 추론을 수행합니다.
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Tuple, Optional, Union
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, BaseMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint import InMemoryCheckpointer

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiMCPClient:
    """Gemini 모델과 LangChain MCP Adapters를 사용한 클라이언트"""
    
    def __init__(self, 
                 server_script_path: str = None, 
                 project_id: str = None,
                 model_name: str = "gemini-1.5-flash"):
        """클라이언트 초기화
        
        Args:
            server_script_path: MCP 서버 스크립트 경로
            project_id: GCP 프로젝트 ID (None이면 환경 변수에서 로드)
            model_name: 사용할 Gemini 모델 이름 (gemini-1.5-flash, gemini-1.5-pro, gemini-pro)
        """
        # 서버 스크립트 경로 설정
        if server_script_path is None:
            # 기본 경로는 현재 디렉토리의 mcp-server/math_server.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.server_script_path = os.path.join(current_dir, "mcp-server", "math_server.py")
        else:
            self.server_script_path = server_script_path
        
        # GCP 프로젝트 ID 설정
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        if not self.project_id:
            logger.warning("GCP_PROJECT_ID가 설정되지 않았습니다.")
        
        # API 키 확인
        self.api_key = os.getenv("VERTEX_API_KEY")
        if not self.api_key:
            logger.warning("VERTEX_API_KEY가 설정되지 않았습니다.")
        
        # 모델 이름 설정
        self.model_name = model_name
        logger.info(f"GeminiMCPClient 초기화 완료 (서버: {self.server_script_path}, 모델: {self.model_name})")
        
        # 클라이언트 컴포넌트
        self.session = None
        self.agent = None
        self.tools = []
        
        # 비동기 작업을 위한 이벤트 루프
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    async def _initialize_session(self) -> Tuple[ClientSession, List[Any]]:
        """MCP 세션을 초기화하고 도구를 로드합니다.
        
        Returns:
            (세션, 도구 리스트) 튜플
        """
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
        logger.info(f"도구 로드 완료: {len(tools)}개 ({', '.join([t.name for t in tools])})")
        
        return session, tools
    
    async def _setup_agent(self) -> Any:
        """ReAct 에이전트를 설정합니다.
        
        Returns:
            설정된 ReAct 에이전트
        """
        # 세션 및 도구 초기화
        self.session, self.tools = await self._initialize_session()
        
        # LLM 설정 (Gemini 모델)
        try:
            llm = ChatVertexAI(
                model_name=self.model_name,
                project=self.project_id,
                vertex_ai_api_key=self.api_key,
                max_output_tokens=1024,
                temperature=0.1,
                top_p=0.95,
                top_k=40,
                verbose=True
            )
        except Exception as e:
            logger.error(f"Gemini 모델 초기화 오류: {str(e)}")
            raise ValueError(f"Gemini 모델 초기화 실패: {str(e)}")
        
        # 시스템 메시지 설정
        system_message = f"""당신은 MCP 도구를 사용하는 AI 슬라임 챗봇입니다.
사용자의 요청에 따라 적절한 도구를 사용하여 문제를 해결해 주세요.
다음과 같은 도구를 사용할 수 있습니다:

{', '.join([tool.name for tool in self.tools])}

도구를 사용할 때는 사용자의 요청을 정확히 이해하고 적절한 도구를 선택하여 작업을 수행하세요.
도구를 호출한 후에는 그 결과를 사용자에게 친절하게 설명해 주세요.
"""
        
        # ReAct 에이전트 생성
        agent = create_react_agent(
            llm=llm,
            tools=self.tools,
            system_message=system_message
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
    
    async def _process_query_async(self, query: str, history: List[Dict[str, Any]] = None, thread_id: str = None) -> Dict[str, Any]:
        """쿼리를 비동기적으로 처리합니다.
        
        Args:
            query: 사용자 쿼리
            history: 대화 이력 (없으면 빈 리스트 사용)
            thread_id: 대화 스레드 ID (없으면 랜덤 생성)
            
        Returns:
            처리 결과 딕셔너리
        """
        if not self.agent:
            logger.warning("에이전트가 초기화되지 않았습니다. initialize() 메서드를 먼저 호출하세요.")
            self.agent = await self._setup_agent()
        
        # 스레드 ID 설정
        thread_id = thread_id or str(uuid.uuid4())
        logger.info(f"쿼리 처리 시작 (스레드 ID: {thread_id})")
        
        try:
            # 히스토리를 메시지 형식으로 변환
            messages = []
            if history:
                for msg in history:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            
            # 현재 쿼리 추가
            messages.append(HumanMessage(content=query))
            
            # 에이전트 실행
            response_messages = []
            async for event in self.agent.astream(
                {"messages": messages},
                {"configurable": {"thread_id": thread_id}}
            ):
                if "messages" in event:
                    response_messages = event["messages"]
            
            # 최종 응답 추출
            final_response = ""
            tool_outputs = []
            
            # 메시지 필터링 (에이전트 응답 메시지만 추출)
            for msg in response_messages:
                if isinstance(msg, AIMessage) and msg not in messages:
                    final_response = msg.content
                elif isinstance(msg, ToolMessage) and msg not in messages:
                    tool_outputs.append({"tool": msg.name, "result": msg.content})
            
            logger.info(f"쿼리 처리 완료 (스레드 ID: {thread_id})")
            return {
                "response": final_response,
                "tool_outputs": tool_outputs,
                "status": "success",
                "model": self.model_name,
                "thread_id": thread_id
            }
        except Exception as e:
            logger.error(f"쿼리 처리 오류: {str(e)}")
            return {
                "response": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "tool_outputs": [],
                "status": "error",
                "error_message": str(e),
                "model": self.model_name,
                "thread_id": thread_id
            }
    
    def process_query(self, query: str, history: List[Dict[str, Any]] = None, thread_id: str = None) -> Dict[str, Any]:
        """쿼리를 처리합니다.
        
        Args:
            query: 사용자 쿼리
            history: 대화 이력 (없으면 빈 리스트 사용)
            thread_id: 대화 스레드 ID (없으면 랜덤 생성)
            
        Returns:
            처리 결과 딕셔너리
        """
        return self.loop.run_until_complete(self._process_query_async(query, history, thread_id))
    
    async def _get_tools_async(self) -> List[Dict[str, str]]:
        """사용 가능한 도구 목록을 비동기적으로 가져옵니다.
        
        Returns:
            도구 정보 딕셔너리 리스트
        """
        if not self.session:
            _, self.tools = await self._initialize_session()
        
        return [{"name": tool.name, "description": tool.description} for tool in self.tools]
    
    def get_tools(self) -> List[Dict[str, str]]:
        """사용 가능한 도구 목록을 가져옵니다.
        
        Returns:
            도구 정보 딕셔너리 리스트
        """
        return self.loop.run_until_complete(self._get_tools_async())
    
    async def _check_connection_async(self) -> Dict[str, Any]:
        """서버 연결 상태를 비동기적으로 확인합니다.
        
        Returns:
            서버 상태 정보 딕셔너리
        """
        try:
            if not self.session:
                self.session, self.tools = await self._initialize_session()
            
            # 간단한 도구 목록 조회로 연결 상태 확인
            tools = await self.session.list_tools()
            
            return {
                "status": "online",
                "model": self.model_name,
                "project_id": self.project_id,
                "available_tools": [tool.name for tool in self.tools],
                "tool_count": len(self.tools)
            }
        except Exception as e:
            logger.error(f"연결 확인 오류: {str(e)}")
            return {
                "status": "offline",
                "error": str(e),
                "model": self.model_name
            }
    
    def check_connection(self) -> Dict[str, Any]:
        """서버 연결 상태를 확인합니다.
        
        Returns:
            서버 상태 정보 딕셔너리
        """
        return self.loop.run_until_complete(self._check_connection_async())

# CLI 테스트 코드
if __name__ == "__main__":
    import sys
    
    # 서버 스크립트 경로 확인
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_script_path = os.path.join(current_dir, "mcp-server", "math_server.py")
    
    # 파일 존재 확인
    if not os.path.exists(server_script_path):
        print(f"오류: MCP 서버 스크립트를 찾을 수 없습니다: {server_script_path}")
        print("math_server.py 파일이 mcp-server 디렉토리에 있는지 확인하세요.")
        sys.exit(1)
    
    # 환경 변수 확인
    project_id = os.getenv("GCP_PROJECT_ID")
    api_key = os.getenv("VERTEX_API_KEY")
    
    if not project_id:
        print("경고: GCP_PROJECT_ID 환경 변수가 설정되지 않았습니다.")
        project_id = input("GCP 프로젝트 ID를 입력하세요: ")
        os.environ["GCP_PROJECT_ID"] = project_id
    
    if not api_key:
        print("경고: VERTEX_API_KEY 환경 변수가 설정되지 않았습니다.")
        api_key = input("Vertex API 키를 입력하세요: ")
        os.environ["VERTEX_API_KEY"] = api_key
    
    # 모델 선택
    model_options = {
        "1": "gemini-1.5-flash",
        "2": "gemini-1.5-pro",
        "3": "gemini-pro"
    }
    
    print("\n==== Gemini 모델 선택 ====")
    for key, value in model_options.items():
        print(f"{key}. {value}")
    
    model_choice = input("사용할 모델 번호를 선택하세요 (1-3, 기본값: 1): ")
    model_name = model_options.get(model_choice, "gemini-1.5-flash")
    
    # 클라이언트 생성
    try:
        print(f"\n==== Gemini MCP 클라이언트 초기화 중... (모델: {model_name}) ====")
        client = GeminiMCPClient(
            server_script_path=server_script_path,
            project_id=project_id,
            model_name=model_name
        )
        client.initialize()
        
        # 서버 상태 확인
        print("\n==== MCP 서버 상태 확인 ====")
        status = client.check_connection()
        print(f"서버 상태: {status['status']}")
        print(f"모델: {status.get('model', 'N/A')}")
        print(f"프로젝트 ID: {status.get('project_id', 'N/A')}")
        
        if status['status'] == 'online':
            print(f"사용 가능한 도구: {', '.join(status.get('available_tools', []))}")
        
        # CLI 모드 실행
        print("\n==== Gemini MCP 에이전트로 도구 호출하기 ====")
        print("종료하려면 'exit' 또는 '종료'를 입력하세요.\n")
        
        # 초기 메시지
        print("AI: 안녕하세요! 무엇을 도와드릴까요? MCP 수학 도구를 사용해 문제를 해결해 드리겠습니다.")
        
        # 대화 이력 초기화
        history = []
        thread_id = "cli-demo"
        
        while True:
            # 사용자 입력 받기
            user_input = input("\n사용자: ")
            
            if user_input.lower() in ["exit", "종료"]:
                print("대화를 종료합니다.")
                break
            
            # 대화 이력에 사용자 메시지 추가
            history.append({"role": "user", "content": user_input})
            
            # 에이전트 실행
            print("\n처리 중...")
            result = client.process_query(user_input, history, thread_id)
            
            # 응답 출력
            print(f"\nAI: {result['response']}")
            
            # 도구 출력 표시
            for tool_output in result.get("tool_outputs", []):
                print(f"\n[도구: {tool_output.get('tool', '알 수 없음')}] {tool_output.get('result', '')}")
            
            # 대화 이력에 AI 응답 추가
            history.append({"role": "assistant", "content": result['response']})
    
    except Exception as e:
        print(f"오류: {str(e)}")
    
    finally:
        # 세션 종료
        if 'client' in locals():
            client.close()
            print("\n세션이 종료되었습니다.") 