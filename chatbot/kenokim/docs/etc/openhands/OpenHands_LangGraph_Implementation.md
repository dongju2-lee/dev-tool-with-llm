# OpenHands를 LangGraph로 구현하기

이 문서는 OpenHands 에이전트 아키텍처를 LangGraph 프레임워크를 활용하여 구현하는 방법에 대한 가이드를 제공합니다.

## 목차

1. [기본 개념 비교](#기본-개념-비교)
2. [핵심 구성 요소 매핑](#핵심-구성-요소-매핑)
3. [에이전트 구현 방법](#에이전트-구현-방법)
4. [멀티 에이전트 시스템 구축](#멀티-에이전트-시스템-구축)
5. [상태 관리 및 메모리](#상태-관리-및-메모리)
6. [인간-루프-포함(Human-in-the-loop) 구현](#인간-루프-포함-구현)
7. [구현 예제](#구현-예제)

## 기본 개념 비교

| OpenHands 개념 | LangGraph 대응 개념 | 설명 |
|----------------|---------------------|------|
| AgentController | StateGraph | 에이전트 실행 흐름을 제어하는 그래프 구조 |
| Agent | 노드(Node) | 그래프 내의 각 처리 단계를 담당하는 함수 |
| Actions/Observations | 메시지/채널 | 노드 간 데이터 전달 방식 |
| State | 상태 객체 | 그래프 실행 중 유지되는 상태 정보 |
| EventStream | 채널(Channel) | 노드 간 정보 전달 매커니즘 |
| Delegation | 서브그래프 | 다른 에이전트에게 작업을 위임하는 매커니즘 |

## 핵심 구성 요소 매핑

### 1. AgentController → StateGraph

OpenHands의 AgentController는 LangGraph에서 `StateGraph`로 구현할 수 있습니다. StateGraph는 노드와 에지를 통해 제어 흐름을 정의하며, 상태를 관리합니다.

```python
from langgraph.graph import StateGraph, END

# 기본 상태 타입 정의
class AgentState(TypedDict):
    messages: list[dict]
    current_action: Optional[str]
    observations: list[dict]
    
# StateGraph 생성
agent_graph = StateGraph(AgentState)
```

### 2. Agent → 노드(Node)

OpenHands의 Agent는 LangGraph에서 그래프의 노드로 구현됩니다. 각 노드는 특정 기능을 수행하는 함수입니다.

```python
def agent_node(state: AgentState) -> AgentState:
    """에이전트의 액션을 결정하는 노드"""
    # LLM을 사용하여 다음 액션 결정
    # ...
    return {"current_action": next_action}

agent_graph.add_node("agent", agent_node)
```

### 3. EventStream → 채널(Channel)

OpenHands의 EventStream은 LangGraph에서 다양한 채널 타입을 통해 구현할 수 있습니다:

- `LastValue`: 가장 최근 값만 유지
- `Topic`: 모든 메시지를 유지
- `Context`: 특정 컨텍스트에 메시지 저장
- `BinaryOperatorAggregate`: 합산 또는 다른 연산으로 메시지 결합

```python
from langgraph.channels import LastValue, Topic

# 메시지를 위한 Topic 채널 사용
messages_channel = Topic("messages")
# 현재 액션을 위한 LastValue 채널 사용
action_channel = LastValue("current_action")
```

### 4. RunTime → Pregel 런타임

LangGraph의 Pregel 런타임은 OpenHands의 RunTime과 유사한 역할을 합니다. 액션 실행과 관찰 생성을 담당합니다.

```python
def execute_action(state: AgentState) -> AgentState:
    """액션을 실행하고 관찰 생성"""
    action = state["current_action"]
    # 액션 실행 로직
    # ...
    return {"observations": [new_observation]}

agent_graph.add_node("executor", execute_action)
```

## 에이전트 구현 방법

### 1. ReAct 에이전트 사용

LangGraph는 OpenHands의 CodeActAgent와 유사한 ReAct 에이전트를 구현하는 기능을 기본 제공합니다.

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# 도구 정의
tools = [...]

# LLM 정의
llm = ChatOpenAI()

# ReAct 에이전트 생성
agent_runnable, agent_executor = create_react_agent(llm, tools)

# 그래프에 추가
agent_graph.add_node("agent", agent_runnable)
```

### 2. 커스텀 에이전트 정의

OpenHands의 다양한 에이전트 타입(BrowsingAgent, VisualBrowsingAgent 등)을 LangGraph에서 구현하려면 커스텀 노드를 정의해야 합니다.

```python
def browsing_agent(state: AgentState) -> dict:
    """웹 브라우징 에이전트 구현"""
    # 웹 브라우징 로직
    # ...
    return {"current_action": browse_action}

agent_graph.add_node("browsing_agent", browsing_agent)
```

## 멀티 에이전트 시스템 구축

OpenHands의 위임 메커니즘은 LangGraph의 멀티 에이전트 시스템과 서브그래프를 통해 구현할 수 있습니다.

### 1. 네트워크 아키텍처 구현

```python
# 여러 에이전트 정의
agent_graph.add_node("code_agent", code_agent_node)
agent_graph.add_node("browsing_agent", browsing_agent_node)
agent_graph.add_node("visual_agent", visual_agent_node)

# 에이전트 라우팅 로직
def router(state: AgentState) -> str:
    """작업 유형에 따라 적절한 에이전트로 라우팅"""
    task = state["messages"][-1]["content"]
    if "웹 검색" in task:
        return "browsing_agent"
    elif "이미지 분석" in task:
        return "visual_agent"
    else:
        return "code_agent"

# 에지 추가 - 라우터 사용
agent_graph.add_conditional_edges("router", router, {
    "code_agent": "executor",
    "browsing_agent": "executor",
    "visual_agent": "executor"
})
```

### 2. Command 객체를 사용한 위임

LangGraph의 Command 객체는 OpenHands의 AgentDelegateAction과 유사한 기능을 제공합니다.

```python
from langgraph.prebuilt import Command

def browsing_agent(state: AgentState) -> dict:
    # 시각적 분석이 필요하다고 판단하면
    if needs_visual_analysis():
        # 시각적 브라우징 에이전트에게 위임
        return Command.subgraph("visual_browsing_agent", {"url": current_url})
    # ...
```

## 상태 관리 및 메모리

OpenHands의 State 및 Memory 시스템은 LangGraph의 영속성 및 메모리 기능을 활용하여 구현할 수 있습니다.

### 1. Thread 기반 메모리

```python
from langgraph.checkpoint import MemorySaver

# 메모리 세이버 생성
memory_saver = MemorySaver()

# 그래프 실행 시 thread_id 지정
app = agent_graph.compile(checkpointer=memory_saver)
result = app.invoke({"messages": [user_message]}, thread_id="conversation_1")
```

### 2. 대화 이력 관리

```python
def manage_conversation_history(state: AgentState) -> AgentState:
    """컨텍스트 윈도우 크기 유지"""
    messages = state["messages"]
    if len(messages) > MAX_CONTEXT_SIZE:
        # 요약 생성 또는 이전 메시지 삭제
        summary = create_summary(messages[:len(messages)//2])
        messages = [{"role": "system", "content": summary}] + messages[len(messages)//2:]
    return {"messages": messages}

agent_graph.add_node("memory_manager", manage_conversation_history)
```

### 3. 시맨틱 검색

```python
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# 벡터 저장소 설정
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(embedding_function=embeddings)

def semantic_search(state: AgentState) -> AgentState:
    """시맨틱 검색 수행"""
    query = state["messages"][-1]["content"]
    # 관련 메모리 검색
    results = vectorstore.similarity_search(query, k=3)
    # 검색 결과 추가
    return {"context": [r.page_content for r in results]}
```

## 인간-루프-포함(Human-in-the-loop) 구현

OpenHands의 확인 모드(confirmation_mode)는 LangGraph의 인간-루프-포함 기능을 통해 구현할 수 있습니다.

```python
from langgraph.graph import interrupt_before

# 도구 호출 전에 인간 승인 요청
agent_graph.add_node("agent", agent_node, interrupt_before=["tools"])

# 인터럽트 처리
def on_interrupt(state, interrupt_data):
    """인간 승인을 위한 인터럽트 처리"""
    # 사용자 인터페이스에 표시
    # ...
    # 승인 또는 수정된 도구 호출 반환
    return {**state, "tools": approved_or_modified_tools}
```

## 구현 예제

다음은 OpenHands의 코드 개발 에이전트를 LangGraph로 구현한 간단한 예제입니다:

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from typing import TypedDict, Optional, List

# 상태 정의
class CodeAgentState(TypedDict):
    messages: List[dict]
    current_action: Optional[str]
    observations: List[dict]

# 도구 정의
@tool
def run_command(command: str) -> str:
    """터미널 명령 실행"""
    # 명령 실행 로직
    return f"명령 '{command}' 실행 결과"

@tool
def read_file(file_path: str) -> str:
    """파일 내용 읽기"""
    # 파일 읽기 로직
    return f"'{file_path}' 파일 내용"

@tool
def write_file(file_path: str, content: str) -> str:
    """파일에 내용 쓰기"""
    # 파일 쓰기 로직
    return f"'{file_path}'에 내용 작성 완료"

# 도구 목록
tools = [run_command, read_file, write_file]

# LLM 정의
llm = ChatOpenAI()

# 에이전트 노드
def code_agent_node(state: CodeAgentState):
    """코드 에이전트 구현"""
    messages = state.get("messages", [])
    observations = state.get("observations", [])
    
    # 모든 메시지와 관찰 결합
    all_messages = messages + [{"role": "system", "content": str(obs)} for obs in observations]
    
    # LLM에 전송
    response = llm.invoke(all_messages)
    
    # 다음 액션 결정
    # 실제 구현에서는 LLM 응답에서 도구 호출이나 메시지 추출 필요
    # 간단한 예시로 직접 액션 지정
    return {"current_action": "run_command('ls -la')"}

# 액션 실행 노드
def execute_action(state: CodeAgentState):
    """액션 실행"""
    action = state.get("current_action")
    
    # 액션 타입에 따라 실행
    if action.startswith("run_command"):
        cmd = action.split("('")[1].split("')")[0]
        result = run_command(cmd)
    elif action.startswith("read_file"):
        path = action.split("('")[1].split("')")[0]
        result = read_file(path)
    elif action.startswith("write_file"):
        # 간단한 구현을 위해 파라미터 파싱 생략
        result = "파일 작성 완료"
    else:
        result = "알 수 없는 액션"
    
    # 관찰 결과 추가
    return {"observations": state.get("observations", []) + [result]}

# 상태 평가 노드
def evaluate_state(state: CodeAgentState) -> str:
    """다음 단계 결정"""
    # 종료 조건 확인
    if "완료" in state.get("current_action", ""):
        return "end"
    return "agent"

# 그래프 생성
code_agent_graph = StateGraph(CodeAgentState)

# 노드 추가
code_agent_graph.add_node("agent", code_agent_node)
code_agent_graph.add_node("executor", execute_action)

# 에지 추가
code_agent_graph.add_edge("agent", "executor")
code_agent_graph.add_conditional_edges("executor", evaluate_state, {
    "agent": "agent",
    "end": END
})

# 메모리 저장소 설정
memory_saver = MemorySaver()

# 그래프 컴파일
app = code_agent_graph.compile(checkpointer=memory_saver)

# 실행
result = app.invoke({"messages": [{"role": "user", "content": "Python 파일에서 모든 함수 목록을 추출해주세요."}]}, 
                    thread_id="code_task_1")
```

## 결론

OpenHands 아키텍처는 LangGraph의 다음 핵심 기능들을 활용하여 효과적으로 구현할 수 있습니다:

1. **StateGraph**: 에이전트 제어 흐름 관리
2. **노드와 에지**: 에이전트 행동 및 전환 정의
3. **서브그래프와 Command**: 에이전트 위임 구현
4. **메모리 및 체크포인터**: 대화 및 상태 지속성 관리
5. **인터럽트**: 인간-루프-포함 기능 구현
6. **ReAct 에이전트**: 기본 제공되는 에이전트 패턴 활용

LangGraph의 이러한 기능들을 활용하면 OpenHands와 같은 복잡한 에이전트 아키텍처를 더 간결하고 모듈화된 방식으로 구현할 수 있으며, 특히 멀티 에이전트 시스템, 상태 관리, 인간-루프-포함 패턴에서 강점을 발휘할 수 있습니다. 