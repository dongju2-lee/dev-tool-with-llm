# LangGraph 기반 AI 에이전트 API 서버 구조 설계

## 1. 핵심 원칙

- **모듈성(Modularity)**: 각 컴포넌트(API, Graph, Config)는 독립적으로 분리하여 유지보수와 확장을 용이하게 합니다.
- **단일 책임(Single Responsibility)**: 각 파일과 모듈은 하나의 명확한 역할을 가집니다.
- **확장성(Scalability)**: 새로운 에이전트나 API 버전을 쉽게 추가할 수 있는 구조를 지향합니다.
- **비동기 우선(Async First)**: FastAPI와 LangGraph의 비동기 기능을 최대한 활용하여 높은 처리량을 보장합니다.

## 2. 프로젝트 구조

```
/backend
├── app/
│   ├── __init__.py
│   │
│   ├── api/                     # 1. API 레이어: HTTP 요청 처리
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── endpoints.py     #   - API 라우트 및 엔드포인트
│   │       └── schemas.py       #   - Pydantic 데이터 모델
│   │
│   ├── core/                    # 2. Core 레이어: 핵심 설정
│   │   ├── __init__.py
│   │   └── config.py            #   - 환경 변수 및 설정 관리
│   │
│   └── graph/                   # 3. Graph 레이어: AI 에이전트 로직
│       ├── __init__.py
│       ├── instance.py          #   - LangGraph 인스턴스 생성 (Singleton)
│       └── agents/              #   - 개별 에이전트/툴 정의
│           ├── __init__.py
│           ├── tool_1.py
│           └── ...
│
└── main.py                      # FastAPI 애플리케이션 진입점
```

## 3. 주요 컴포넌트 역할

#### **1. API 레이어 (`app/api/`)**
- **역할**: 클라이언트의 HTTP 요청을 받고 응답을 반환합니다.
- `endpoints.py`:
  - FastAPI의 `APIRouter`를 사용하여 엔드포인트(`chat`, `stream` 등)를 정의합니다.
  - 요청 데이터를 `schemas.py`의 모델로 유효성 검사합니다.
  - `graph` 레이어의 에이전트 인스턴스를 호출하여 비즈니스 로직을 처리합니다.
- `schemas.py`:
  - Pydantic `BaseModel`을 사용하여 요청/응답 데이터의 형식을 명확하게 정의합니다. (예: `ChatRequest`, `ChatResponse`)

#### **2. Core 레이어 (`app/core/`)**
- **역할**: 애플리케이션의 핵심 설정을 담당합니다.
- `config.py`:
  - `pydantic-settings`를 활용하여 `.env` 파일에서 **`GEMINI_API_KEY`** 등 환경 변수를 로드합니다.
  - 설정 값을 전역적으로 공유할 수 있는 `settings` 객체를 제공합니다.

#### **3. Graph 레이어 (`app/graph/`)**
- **역할**: LangGraph를 사용한 AI 에이전트의 모든 로직을 포함합니다.
- `instance.py`:
  - **가장 중요한 파일** 중 하나로, LangGraph 에이전트(`StateGraph`)를 생성하고 컴파일합니다.
  - 애플리케이션 시작 시 **단 한번만 그래프를 생성**하여 메모리에 유지하는 **싱글턴(Singleton) 패턴**을 적용합니다. 이는 매 요청마다 그래프를 새로 만드는 오버헤드를 방지합니다.
- `agents/`:
  - 에이전트가 사용할 `Tool`이나 특정 프롬프트를 모듈화하여 관리합니다.

#### **4. `main.py`**
- **역할**: FastAPI 애플리케이션의 시작점(Entrypoint)입니다.
- uvicorn이 이 파일을 실행하여 서버를 구동합니다.
- FastAPI 앱 인스턴스를 생성하고, `api` 레이어의 라우터를 포함시키며, CORS 같은 미들웨어를 설정합니다.

## 4. 데이터 흐름 (Chat Request)

1.  **Client** → `POST /api/v1/chat`
2.  **`main.py`**: 요청을 FastAPI 앱으로 전달
3.  **`api/v1/endpoints.py`**:
    - `/chat` 엔드포인트 함수 호출
    - 요청 Body를 `ChatRequest` 스키마로 검증
4.  **`graph/instance.py`**:
    - 미리 생성된 `app_graph` 싱글턴 인스턴스 호출 (`app_graph.ainvoke(...)`)
    - 대화 상태(`thread_id`)와 함께 사용자 입력을 처리
5.  **LangGraph**:
    - 입력 분석 → 적절한 툴/에이전트 선택 → 실행 → 결과 생성
6.  **`endpoints.py`**:
    - LangGraph로부터 받은 결과를 `ChatResponse` 스키마에 맞춰 가공
7.  **Client**: 최종 JSON 응답 수신

## 5. 구현 예시

**`graph/instance.py` (싱글턴 구현)**
```python
from langgraph.graph import StateGraph

class GraphSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # 그래프 생성 로직 (StateGraph, tools, compile 등)
            builder = StateGraph(...)
            # ...
            cls._instance = builder.compile()
            print("Graph compiled and instance created.")
        return cls._instance

# 앱 전체에서 사용할 그래프 인스턴스
app_graph = GraphSingleton()
```

**`api/v1/endpoints.py`**
```python
from fastapi import APIRouter
from ..schemas import ChatRequest, ChatResponse
from ...graph.instance import app_graph

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    result = await app_graph.ainvoke({"messages": [("user", request.content)]}, config)
    # ... 결과 처리 ...
    return ChatResponse(...)
```

이 구조는 역할과 책임이 명확히 분리되어 있어, 향후 LangGraph 에이전트가 복잡해지거나 API 기능이 추가되어도 체계적으로 관리할 수 있습니다.

## 6. Supervisor 패턴을 이용한 그래프 확장

기존의 단일 에이전트 구조를 여러 전문 에이전트가 협업하는 **Supervisor-Worker** 구조로 확장할 수 있습니다. Supervisor는 사용자의 요청을 분석하여 가장 적절한 Worker(전문 에이전트)에게 작업을 위임하는 "지능적인 라우터" 역할을 수행합니다.

### **6.1. 확장된 프로젝트 구조 (`graph/` 디렉토리)**

```
/graph
├── __init__.py
├── instance.py             # Supervisor 그래프 생성 및 관리 (싱글턴)
├── state.py                # 공유될 대화 상태(AgentState) 정의
└── agents/
    ├── __init__.py
    ├── supervisor.py         # Supervisor 노드 로직
    ├── grafana_agent.py      # Worker 1: Grafana 전문가
    ├── devops_agent.py       # Worker 2: DevOps 전문가
    └── ...                   # Worker n: 추가될 전문가
```

### **6.2. Supervisor 그래프 구현 흐름 (`instance.py`)**

1.  **AgentState 정의**: 모든 에이전트가 공유할 대화 상태를 `TypedDict`로 정의합니다. (`state.py`)
2.  **Worker 에이전트 생성**: 각 전문 분야(Grafana, DevOps 등)의 LangGraph 에이전트를 생성합니다. 각 에이전트는 자체적인 툴과 프롬프트를 가집니다.
3.  **Supervisor 노드 정의**:
    - **역할**: Worker들의 리더. 사용자 입력을 받아 어떤 Worker에게 작업을 넘길지 결정합니다.
    - **구현**: **`ChatGoogleGenerativeAI` (Gemini)** 모델의 Function Calling을 사용하여 다음 작업자를 선택하도록 구성합니다.
4.  **그래프 빌드**:
    - `StateGraph(AgentState)`로 그래프를 초기화합니다.
    - 각 Worker 에이전트를 노드(Node)로 추가합니다.
    - Supervisor를 **진입점(Entry Point)** 및 **조건부 엣지(Conditional Edge)**로 설정하여, Supervisor의 결정에 따라 적절한 Worker 노드로 분기되도록 합니다.

### **6.3. 구현 예시 (`instance.py`)**

```python
from langgraph.graph import StateGraph, END
from .state import AgentState
from .agents import create_grafana_agent, create_devops_agent, create_supervisor_node

# 1. Worker 에이전트 생성
grafana_agent = create_grafana_agent()
devops_agent = create_devops_agent()

# 2. 그래프 초기화
workflow = StateGraph(AgentState)

# 3. 노드 추가
workflow.add_node("grafana_agent", grafana_agent)
workflow.add_node("devops_agent", devops_agent)
workflow.add_node("supervisor", create_supervisor_node())

# 4. 엣지 연결
workflow.add_edge("grafana_agent", END)
workflow.add_edge("devops_agent", END)

# 5. 조건부 엣지 설정 (Supervisor가 분기점 역할)
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["next"], # state의 'next' 값에 따라 분기
    {
        "grafana_agent": "grafana_agent",
        "devops_agent": "devops_agent",
        "FINISH": END,
    },
)

# 6. 진입점 설정 및 컴파일
workflow.set_entry_point("supervisor")
app_graph = workflow.compile()
```

### **6.4. 장점**

- **명확한 역할 분리**: 각 에이전트는 자신의 전문 분야에만 집중할 수 있습니다.
- **확장 용이성**: 새로운 기술이나 도메인이 필요할 때, 해당 분야의 Worker 에이전트를 추가하고 Supervisor의 선택지에만 등록하면 되므로 기존 코드에 미치는 영향이 적습니다.
- **유연한 대화 흐름**: Supervisor가 대화의 전체 맥락을 관리하며, 필요에 따라 여러 에이전트를 순차적으로 또는 병렬로 호출하는 복잡한 워크플로우를 구성할 수 있습니다.

이러한 Supervisor 패턴을 적용하면, 단순한 챗봇을 넘어 여러 전문가가 협업하여 복잡한 문제를 해결하는 고도화된 AI 시스템을 구축할 수 있습니다.

## 7. 외부 시스템 연동: MultiServerMCPClient 통합

`langchain-mcp-adapters`는 외부 MCP(Model Context Protocol) 서버에 노출된 복잡한 API들을 표준 LangChain `Tool` 객체로 변환하여, LangGraph 에이전트가 외부 시스템과 쉽게 통신할 수 있도록 지원합니다.

특히 여러 외부 시스템(Grafana, Jenkins, K8s 등)을 연동해야 할 경우, 각 시스템을 개별 MCP 서버로 래핑하고 `MultiServerMCPClient`를 사용해 중앙에서 통합 관리하는 것이 효율적입니다.

### **7.1. 통합 아키텍처**

- **중앙 클라이언트 관리**: `MultiServerMCPClient` 인스턴스를 `graph/instance.py`나 별도의 `core/clients.py`에서 생성하고 관리합니다. 이 클라이언트는 다양한 MCP 서버(Grafana용, DevOps용 등)의 연결 정보를 가집니다.
- **동적 도구 로딩**: 애플리케이션 시작 시 또는 첫 요청 시, 이 클라이언트를 통해 모든 MCP 서버의 도구들을 비동기적으로 로드합니다.
- **에이전트로 도구 주입**: 로드된 전체 도구 목록은 Supervisor에 의해 각 전문 에이전트(Worker)에게 전달됩니다. 각 에이전트는 자신에게 필요한 도구만 필터링하여 사용합니다.

### **7.2. 구현 예시**

#### **1. 중앙 클라이언트 및 도구 로더 (`graph/instance.py`)**

```python
# graph/instance.py
from langchain_mcp_adapters.client import MultiServerMCPClient

# 1. 중앙에서 관리되는 MCP 클라이언트 설정
# 각 서비스는 자체 MCP 서버를 통해 도구를 노출한다고 가정
mcp_client = MultiServerMCPClient({
    "grafana": {
        "url": "http://mcp-grafana-server:8000/mcp", 
        "transport": "streamable_http"
    },
    "devops": {
        "url": "http://mcp-devops-server:8000/mcp",
        "transport": "streamable_http"
    }
})

async def get_all_mcp_tools():
    """애플리케이션에서 사용할 모든 MCP 도구를 비동기적으로 로드합니다."""
    return await mcp_client.get_tools()
```

#### **2. 에이전트의 도구 활용 (`agents/grafana_agent.py`)**

```python
# agents/grafana_agent.py
from typing import List
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent

def create_grafana_agent(llm: ChatGoogleGenerativeAI, all_tools: List[BaseTool]):
    """전체 MCP 도구 목록을 받아 필요한 도구만 필터링하여 Grafana 에이전트를 생성합니다."""
    
    # 1. Grafana 관련 도구만 필터링 (예: 도구 이름에 'grafana'가 포함된 경우)
    grafana_tools = [tool for tool in all_tools if tool.name.startswith("grafana_")]
    
    # 2. 에이전트 프롬프트 정의
    prompt = ... # Grafana 에이전트의 역할과 지침을 정의하는 프롬프트
    
    # 3. LLM에 필터링된 도구를 바인딩하여 에이전트가 사용할 도구를 인식시킴
    agent_llm = llm.bind_tools(grafana_tools)
    
    # 4. Tool Calling 에이전트 생성
    agent = create_tool_calling_agent(agent_llm, grafana_tools, prompt)
    
    return AgentExecutor(agent=agent, tools=grafana_tools, verbose=True)
```
이러한 중앙 집중식 도구 관리 방식은 각 에이전트가 연결의 복잡성을 신경 쓰지 않고 자신의 비즈니스 로직에만 집중할 수 있게 하며, 전체 시스템의 유지보수성과 확장성을 크게 향상시킵니다.
