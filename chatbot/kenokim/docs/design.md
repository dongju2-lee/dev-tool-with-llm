# Streamlit 챗봇 UI 설계 문서

## 시스템 개요
이 시스템은 Python Streamlit을 사용하여 MCP(Model Control Panel) 서버 API와 상호작용하는 챗봇 UI를 구현합니다. 사용자는 웹 인터페이스를 통해 챗봇과 대화하고, 백엔드에서는 MCP 서버 API를 호출하여 응답을 생성합니다.

## 아키텍처

```
+-------------+      +------------------+      +---------------+
|  Streamlit  | <--> |  Python Backend  | <--> |   MCP 서버   |
|   챗봇 UI   |      |   (API 클라이언트)  |      |     API      |
+-------------+      +------------------+      +---------------+
```

## LangGraph + Streamlit + MCP 연동 아키텍처

```
+-------------+      +-------------------+      +-----------------+
|  Streamlit  | <--> |     LangGraph     | <--> |    MCP 서버    |
|   챗봇 UI   |      |  워크플로우 엔진   |      |      API       |
+-------------+      +-------------------+      +-----------------+
       ^                      ^                         ^
       |                      |                         |
       v                      v                         v
+------------------------------------------------------------------+
|                           상태 관리 계층                           |
|------------------------------------------------------------------|
| - StreamlitChatMessageHistory: 대화 기록 관리                     |
| - LangGraph 영속성 저장소: 워크플로우 상태 및 컨텍스트 유지          |
| - 세션 관리: 사용자별 세션 및 스레드 ID 관리                        |
+------------------------------------------------------------------+
```

## LangGraph + MCP 연동 구성 요소

### 1. Streamlit 프론트엔드
- 사용자 메시지 입력 필드
- 대화 이력 표시 영역
- 설정 사이드바 (모델 선택 등)
- 세션 관리 (대화 컨텍스트 유지)
- StreamlitCallbackHandler를 통한 LLM 사고 과정 표시

### 2. LangGraph 워크플로우 엔진
- StateGraph를 통한 대화 흐름 관리
- 에이전트 워크플로우 정의 및 실행
- 메모리 시스템 (단기/장기 메모리)
- 인간 개입(Human-in-the-loop) 기능 지원
- 이벤트 스트리밍 처리

### 3. MCP 서버 통합
- 요청/응답 처리
- 비동기 통신
- 스트리밍 응답 처리

## MCP 서버 API 명세

### MCP 서버가 노출해야 할 엔드포인트

1. **채팅 메시지 처리 엔드포인트**
   - **경로**: `/chat`
   - **메소드**: POST
   - **기능**: 사용자 메시지 처리 및 AI 응답 생성
   - **요청 파라미터**:
     ```json
     {
       "message": "사용자 입력 메시지",
       "thread_id": "대화 스레드 ID (선택사항)",
       "context": [이전 대화 히스토리 (선택사항)],
       "stream": true/false (스트리밍 응답 여부)
     }
     ```
   - **응답 형식**:
     - 일반 응답:
       ```json
       {
         "content": "AI 응답 메시지",
         "thread_id": "대화 스레드 ID"
       }
       ```
     - 스트리밍 응답: 서버-전송 이벤트(SSE) 또는 청크 응답

2. **스레드 관리 엔드포인트**
   - **경로**: `/threads`
   - **메소드**: 
     - GET: 모든 스레드 목록 조회
     - POST: 새 스레드 생성
   - **요청 파라미터** (POST):
     ```json
     {
       "metadata": {
         "title": "대화 제목 (선택사항)",
         "tags": ["태그1", "태그2"] (선택사항)
       }
     }
     ```
   - **응답 형식**:
     ```json
     {
       "thread_id": "생성된 스레드 ID",
       "created_at": "생성 시간",
       "metadata": { /* 메타데이터 */ }
     }
     ```

3. **대화 기록 조회 엔드포인트**
   - **경로**: `/threads/{thread_id}/messages`
   - **메소드**: GET
   - **응답 형식**:
     ```json
     {
       "messages": [
         {
           "id": "메시지 ID",
           "role": "user/assistant",
           "content": "메시지 내용",
           "created_at": "생성 시간"
         },
         // ...
       ]
     }
     ```

4. **도구 호출 엔드포인트**
   - **경로**: `/tools/execute`
   - **메소드**: POST
   - **기능**: 에이전트가 사용 가능한 도구 실행
   - **요청 파라미터**:
     ```json
     {
       "tool_name": "도구 이름",
       "parameters": {
         "param1": "값1",
         "param2": "값2"
       },
       "thread_id": "관련 스레드 ID (선택사항)"
     }
     ```
   - **응답 형식**:
     ```json
     {
       "result": "도구 실행 결과",
       "status": "success/error",
       "error": "오류 메시지 (있는 경우)"
     }
     ```

5. **상태 확인 엔드포인트**
   - **경로**: `/status`
   - **메소드**: GET
   - **기능**: MCP 서버 상태 확인
   - **응답 형식**:
     ```json
     {
       "status": "online/offline",
       "version": "서버 버전",
       "uptime": "가동 시간(초)"
     }
     ```

## 데이터 흐름

### 1. 사용자 메시지 처리 흐름
```
사용자 → Streamlit UI → StreamlitChatMessageHistory → LangGraph 워크플로우 
→ MCP API 클라이언트 → MCP 서버 → 응답 → 스트리밍 표시 → 사용자
```

### 2. 상태 관리 흐름
```
LangGraph 워크플로우 → 스레드별 메모리 → 체크포인터 → 영속성 저장소 
→ 세션 복원 → LangGraph 워크플로우
```

## LangGraph + MCP 연동 기술 구현

### 1. LangGraph 워크플로우 설정
```python
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

# 상태 정의
class ChatState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]
    thread_id: str

# 워크플로우 정의
def build_graph():
    # 체크포인터 설정 (상태 저장)
    checkpointer = MemorySaver()
    
    # 그래프 생성
    builder = StateGraph(ChatState)
    
    # MCP 통신 노드 정의
    def call_mcp_api(state):
        messages = state["messages"]
        thread_id = state["thread_id"]
        
        # MCP API 호출
        response = mcp_client.send_message(
            messages[-1].content, 
            thread_id=thread_id,
            context=messages[:-1]
        )
        
        # 응답 추가
        state["messages"].append(AIMessage(content=response["content"]))
        return state
        
    # 노드 추가
    builder.add_node("mcp_api", call_mcp_api)
    
    # 엣지 정의
    builder.add_edge("mcp_api", END)
    
    # 진입점 설정
    builder.set_entry_point("mcp_api")
    
    # 그래프 컴파일
    graph = builder.compile(checkpointer=checkpointer)
    
    return graph
```

### 2. Streamlit + LangGraph 통합
```python
import streamlit as st
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_community.callbacks import StreamlitCallbackHandler

# Streamlit 앱 설정
st.title("MCP 챗봇")

# 세션 상태 초기화
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = StreamlitChatMessageHistory(key="chat_history")

# LangGraph 워크플로우 생성
graph = build_graph()

# 콜백 핸들러 설정 (사고 과정 표시)
st_callback = StreamlitCallbackHandler(st.container())

# 대화 이력 표시
for msg in st.session_state.chat_history.messages:
    with st.chat_message(msg.type):
        st.markdown(msg.content)

# 사용자 입력
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 추가
    st.session_state.chat_history.add_user_message(prompt)
    
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # AI 응답 생성
    with st.chat_message("assistant"):
        # 초기 상태 설정
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        # LangGraph 실행 및 스트리밍
        with st.spinner("생각 중..."):
            # 메시지 준비
            messages = st.session_state.chat_history.messages
            
            # 메시지 스트리밍
            message_placeholder = st.empty()
            full_response = ""
            
            # 스트리밍 처리
            for chunk, metadata in graph.stream(
                {"messages": messages, "thread_id": st.session_state.thread_id},
                config,
                stream_mode="messages", # 메시지 토큰 스트리밍 모드
                callbacks=[st_callback]
            ):
                if isinstance(chunk, AIMessage):
                    content = chunk.content
                    full_response += content
                    message_placeholder.markdown(full_response + "▌")
                    
            # 최종 응답 표시
            message_placeholder.markdown(full_response)
        
        # 응답 저장
        st.session_state.chat_history.add_ai_message(full_response)
```

### 3. MCP API 클라이언트
```python
import httpx
import asyncio
from typing import List, Dict, Any, Optional

class MCPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json"
        }
    
    async def send_message(
        self, 
        message: str, 
        thread_id: str = None,
        context: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True
    ):
        """메시지를 MCP 서버로 전송하고 응답을 받습니다."""
        url = f"{self.base_url}/chat"
        
        payload = {
            "message": message,
            "thread_id": thread_id,
            "context": context or [],
            "stream": stream
        }
        
        if stream:
            # 스트리밍 응답 처리
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, json=payload, headers=self.headers) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            yield self._parse_chunk(chunk)
        else:
            # 일반 응답 처리
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
                
    def _parse_chunk(self, chunk: str) -> Dict[str, Any]:
        """응답 청크 파싱"""
        # 여기서 서버 응답 형식에 맞게 파싱 로직 구현
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            return {"content": chunk, "type": "text"}
```

## 사용자-LangGraph-MCP 인터랙션 시나리오

### 1. 일반 대화 시나리오
1. 사용자가 Streamlit UI를 통해 메시지 입력
2. 메시지가 StreamlitChatMessageHistory에 저장
3. LangGraph 워크플로우가 MCP API로 메시지 전송
4. MCP 서버가 응답 생성 및 반환
5. 응답이 스트리밍되어 Streamlit UI에 표시
6. 응답이 StreamlitChatMessageHistory에 저장

### 2. 인간 개입(Human-in-the-loop) 시나리오
1. 사용자가 질문 입력
2. LangGraph 워크플로우가 실행되다가 인간 개입 필요시 일시 중지
3. Streamlit UI가 사용자에게 승인/수정 요청 표시
4. 사용자가 입력 제공
5. 워크플로우가 재개되어 MCP API로 요청 전송
6. 나머지 프로세스는 일반 시나리오와 동일

## 확장 기능 구현

### 1. 다중 도구 사용 에이전트
```python
from langchain.agents import tool

@tool
def search_web(query: str) -> str:
    """웹에서 정보를 검색합니다."""
    # 검색 구현
    return f"검색 결과: {query}에 대한 정보"

@tool
def calculate(expression: str) -> str:
    """수학 표현식을 계산합니다."""
    # 계산 구현
    return f"계산 결과: {expression} = {eval(expression)}"

# 도구 목록 정의
tools = [search_web, calculate]

# LangGraph에 도구 통합
def build_agent_graph(tools):
    # ReAct 에이전트 패턴 구현
    # ...
```

### 2. 장기 메모리 시스템
```python
from langgraph.checkpoint import MemorySaver
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# 벡터 저장소 설정
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_texts([], embeddings)

# 장기 메모리 구현
class LongTermMemory:
    def __init__(self, vectorstore):
        self.vectorstore = vectorstore
    
    def add_memory(self, text, metadata=None):
        """메모리 추가"""
        self.vectorstore.add_texts([text], metadatas=[metadata or {}])
    
    def retrieve_relevant(self, query, k=3):
        """관련 메모리 검색"""
        results = self.vectorstore.similarity_search(query, k=k)
        return results
```

## 구성 요소

### 1. Streamlit 프론트엔드
- 사용자 메시지 입력 필드
- 대화 이력 표시 영역
- 설정 사이드바 (모델 선택 등)
- 세션 관리 (대화 컨텍스트 유지)

### 2. Python 백엔드
- MCP API 클라이언트
- 메시지 포맷팅 및 처리
- 응답 파싱
- 오류 처리 및 재시도 로직

### 3. MCP 서버 통합
- 요청/응답 처리
- 비동기 통신

## 기능 요구사항

### 핵심 기능
1. **대화형 인터페이스**
   - 메시지 입력 및 전송
   - 대화 이력 표시 및 스크롤
   - 메시지 타입별 시각적 구분 (사용자/시스템)

2. **API 통합**
   - MCP 서버 연결 설정
   - 요청/응답 처리

3. **대화 관리**
   - 세션 유지 및 컨텍스트 관리
   - 대화 이력 저장 및 로드
   - 대화 초기화 옵션

### 추가 기능
1. **설정 관리**
   - 모델 파라미터 조정 (온도, 최대 토큰 등)
   - UI 테마 설정

2. **고급 기능**
   - 파일 업로드/다운로드 지원
   - 응답 포맷팅 (마크다운, 코드 하이라이팅)
   - 응답 생성 중 로딩 인디케이터

## 기술 스택

### 프론트엔드
- **Streamlit**: 주 UI 프레임워크
- **Streamlit 컴포넌트**: 고급 UI 요소

### 백엔드
- **Python**: 코어 로직
- **Requests/httpx**: API 통신
- **JSON**: 데이터 직렬화
- **asyncio**: 비동기 처리 (필요시)
- **LangGraph**: 워크플로우 엔진 및 상태 관리
- **LangChain**: LLM 통합 유틸리티

## 구현 계획

### 1단계: 기본 UI 구현
- Streamlit 앱 설정
- 기본 채팅 인터페이스 구현
- 사이드바 설정 패널 구현

### 2단계: MCP API 통합
- API 클라이언트 구현
- 기본 대화 기능 연동

### 3단계: LangGraph 워크플로우 구현
- StateGraph 정의
- 메모리 시스템 구현
- 에이전트 패턴 적용

### 4단계: 고급 기능 추가
- 대화 컨텍스트 관리
- 응답 포맷팅 및 렌더링
- 오류 처리 및 예외 상황 관리

### 5단계: 최적화 및 테스트
- 성능 최적화
- 사용자 테스트
- 피드백 반영

## 폴더 구조
```
chatbot/
├── kenokim/
│   ├── app.py               # 메인 Streamlit 앱
│   ├── api/
│   │   ├── client.py        # MCP API 클라이언트
│   │   └── models.py        # API 모델/스키마
│   ├── ui/
│   │   ├── chat.py          # 채팅 UI 컴포넌트
│   │   └── sidebar.py       # 사이드바 UI 컴포넌트
│   ├── agents/
│   │   ├── workflow.py      # LangGraph 워크플로우 정의
│   │   └── tools.py         # 에이전트 도구 모음
│   ├── memory/
│   │   ├── short_term.py    # 단기 메모리 관리
│   │   └── long_term.py     # 장기 메모리 관리
│   ├── utils/
│   │   ├── formatting.py    # 텍스트 포맷팅 유틸리티
│   │   └── session.py       # 세션 관리
│   ├── config/
│   │   └── settings.py      # 앱 설정
│   └── docs/
│       └── design.md        # 설계 문서
```

## API 인터페이스

### MCP 서버 API 통합
```python
class MCPClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    async def send_message(self, message, context=None):
        """메시지를 MCP 서버로 전송하고 응답을 받습니다."""
        payload = {
            "message": message,
            "context": context or []
        }
        response = await self.session.post(f"{self.base_url}/chat", json=payload)
        return response.json()
```

## UI 컴포넌트

### 채팅 인터페이스
```python
def render_chat_interface():
    st.title("MCP 챗봇")
    
    # 대화 이력 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력
    if prompt := st.chat_input("메시지를 입력하세요"):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                response = st.session_state.client.send_message(
                    prompt, 
                    context=st.session_state.messages
                )
                st.markdown(response["content"])
        
        # 응답 저장
        st.session_state.messages.append({"role": "assistant", "content": response["content"]})
```

## 개발 및 배포 가이드라인
1. 로컬 개발 환경 설정
2. 테스트 계획 및 실행
3. 배포 파이프라인 구성
4. 모니터링 및 유지보수 계획
