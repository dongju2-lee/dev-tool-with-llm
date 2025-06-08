# Vertex AI Gemini와 LangGraph 연동 가이드

## 개요

이 문서는 Google Cloud Vertex AI의 Gemini 모델과 LangGraph를 Python 코드에서 연동하는 방법을 설명합니다. Gemini는 Google의 최신 LLM(Large Language Model)으로, 텍스트 생성, 코드 작성, 다중 모달 대화 등 다양한 기능을 제공합니다. LangGraph는 상태 기반(stateful) LLM 워크플로우를 그래프 형태로 설계할 수 있는 라이브러리입니다.

## 사전 요구사항

- Google Cloud 계정 및 프로젝트
- Vertex AI API 활성화
- Python 3.7 이상
- 적절한 권한 설정 (Vertex AI 사용자 권한)

## 설치 방법

```bash
# 필수 패키지 설치
pip install python-dotenv
pip install google-cloud-aiplatform
pip install -U langgraph
pip install streamlit
```

## API 키 관리

Vertex AI API 키 (또는 서비스 계정 키)를 안전하게 관리하는 방법:

```python
import os
from dotenv import load_dotenv
import vertexai
from vertexai.preview.generative_models import GenerativeModel

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기 
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")  # API 키 인증 방식
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")

# Vertex AI 초기화 (API 키 방식)
vertexai.init(project=PROJECT_ID, location=LOCATION, api_key=VERTEX_API_KEY)

# Gemini 모델 로드
model = GenerativeModel("gemini-pro")
```

## 기본 LangGraph 워크플로우 구성

LangGraph를 사용하여 복잡한 AI 워크플로우를 그래프로 구성하는 방법:

```python
from langgraph.graph import MessageGraph, END

# Gemini를 호출하는 노드 함수 정의
def gemini_node(messages):
    # 마지막 메시지 내용 추출
    user_input = messages[-1]["content"] if isinstance(messages[-1], dict) else messages[-1].content
    
    # Gemini 모델로 응답 생성
    response = model.generate_content(user_input)
    
    # 응답 반환
    return [{"role": "assistant", "content": response.text}]

# 간단한 LangGraph 메시지 그래프 생성
graph = MessageGraph()
graph.add_node("gemini", gemini_node)
graph.add_edge("gemini", END)
graph.set_entry_point("gemini")
runnable = graph.compile()
```

## Streamlit 코드를 LangGraph로 리팩토링하기

### 기존 Streamlit 앱 구조

기존 Streamlit 앱은 일반적으로 다음과 같은 패턴을 가집니다:

```python
import streamlit as st
from api.client import MCPClient

# 메시지 처리 로직
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 응답 생성
    response = mcp_client.send_message(message=prompt, thread_id=thread_id)
    
    # 세션에 저장
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response_content
    })
```

### LangGraph 기반 리팩토링 1: 기능별 그래프 노드 분리

LangGraph를 사용한 리팩토링의 핵심은 기능을 그래프 노드로 분리하는 것입니다:

```python
import streamlit as st
import os
from dotenv import load_dotenv
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from langgraph.graph import StateGraph
from typing import Dict, Any, TypedDict, List

# 환경 변수 로드
load_dotenv()
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")

# 상태 타입 정의
class ChatState(TypedDict):
    messages: List[Dict[str, str]]
    current_message: str
    response: str
    show_dashboard: bool

# 초기 상태
def get_initial_state() -> ChatState:
    return {
        "messages": [],
        "current_message": "",
        "response": "",
        "show_dashboard": False
    }

# 1. 메시지 처리 노드
def process_input(state: ChatState) -> ChatState:
    # 현재 메시지를 상태에 추가
    messages = state["messages"].copy()
    messages.append({"role": "user", "content": state["current_message"]})
    
    # 대시보드 키워드 확인
    show_dashboard = any(
        keyword in state["current_message"].lower() 
        for keyword in ["대시보드", "차트", "그래프", "보여줘"]
    )
    
    return {"messages": messages, "show_dashboard": show_dashboard}

# 2. Gemini 응답 생성 노드 
def generate_response(state: ChatState) -> ChatState:
    # Vertex AI 초기화
    vertexai.init(project=PROJECT_ID, location=LOCATION, api_key=VERTEX_API_KEY)
    model = GenerativeModel("gemini-pro")
    
    # 전체 메시지 이력
    prompt = "당신은 친절한 AI 어시스턴트입니다. 다음 대화에 응답하세요:\n\n"
    for msg in state["messages"]:
        prompt += f"{msg['role']}: {msg['content']}\n"
    
    # Gemini 호출
    response = model.generate_content(prompt)
    
    # 응답 메시지 추가
    messages = state["messages"].copy()
    messages.append({"role": "assistant", "content": response.text})
    
    return {"messages": messages, "response": response.text}

# 3. 대시보드 생성 노드 (조건부 실행)
def create_dashboard(state: ChatState) -> ChatState:
    if not state["show_dashboard"]:
        return {}  # 변경 없음
        
    # 대시보드 관련 응답 추가
    dashboard_response = "여기 대시보드입니다! (이미지는 실제 렌더링될 때 생성됩니다)"
    
    # 응답 업데이트
    messages = state["messages"].copy()
    if messages and messages[-1]["role"] == "assistant":
        # 기존 응답이 있으면 업데이트
        messages[-1]["content"] = dashboard_response
    else:
        # 없으면 새로 추가
        messages.append({"role": "assistant", "content": dashboard_response})
    
    return {"messages": messages, "response": dashboard_response}

# 워크플로우 그래프 구성
workflow = StateGraph(ChatState)
workflow.add_node("process_input", process_input)
workflow.add_node("generate_response", generate_response)
workflow.add_node("create_dashboard", create_dashboard)

# 엣지 및 조건부 실행 정의
workflow.add_edge("process_input", "create_dashboard")
workflow.add_conditional_edges(
    "create_dashboard",
    lambda state: "generate_response" if not state["show_dashboard"] else END
)
workflow.add_edge("generate_response", END)

# 시작점 설정
workflow.set_entry_point("process_input")

# 그래프 컴파일
chain = workflow.compile()
```

### LangGraph 기반 리팩토링 2: Streamlit과 통합

```python
import streamlit as st
import os
from dotenv import load_dotenv
from PIL import Image, ImageDraw
import io

# 위에서 정의한 LangGraph 컴포넌트 가져오기
# from langchain_workflow import chain, get_initial_state

# 페이지 설정
st.set_page_config(
    page_title="LangGraph 슬라임 챗봇",
    page_icon="🤖",
    layout="centered"
)

# CSS 추가
st.markdown("""
<style>
    .stChatMessage {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("LangGraph 슬라임 챗봇")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "graph_state" not in st.session_state:
    st.session_state.graph_state = get_initial_state()

# 슬라임 이미지 생성 함수 (대시보드 표시용)
def create_slime_image():
    img = Image.new('RGB', (400, 400), color=(255, 240, 200))
    draw = ImageDraw.Draw(img)
    
    # 슬라임 몸체 (원)
    draw.ellipse((100, 120, 300, 320), fill=(255, 180, 80), outline=(101, 67, 33), width=3)
    
    # 눈
    draw.ellipse((150, 180, 190, 220), fill=(0, 0, 0), outline=(0, 0, 0))
    draw.ellipse((210, 180, 250, 220), fill=(0, 0, 0), outline=(0, 0, 0))
    
    # 눈 하이라이트
    draw.ellipse((155, 185, 170, 200), fill=(255, 255, 255), outline=(255, 255, 255))
    draw.ellipse((215, 185, 230, 200), fill=(255, 255, 255), outline=(255, 255, 255))
    
    # 입
    draw.arc((175, 220, 225, 270), start=0, end=180, fill=(101, 67, 33), width=3)
    
    # 볼
    draw.ellipse((140, 220, 160, 240), fill=(255, 150, 150), outline=(255, 150, 150))
    draw.ellipse((240, 220, 260, 240), fill=(255, 150, 150), outline=(255, 150, 150))
    
    # 이미지를 바이트 스트림으로 반환
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    
    return img_bytes

# 대화 이력 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            st.markdown(message.get("text", ""))
            st.image(message["content"], caption=message.get("caption", ""), use_column_width=True)
        else:
            st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 사용자 메시지 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # LangGraph 워크플로우 실행 준비
    current_state = st.session_state.graph_state.copy()
    current_state["current_message"] = prompt
    
    # 워크플로우 실행
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            # LangGraph 체인 실행
            result = chain.invoke(current_state)
            
            # 결과 처리 및 표시
            if result["show_dashboard"]:
                # 대시보드 이미지 생성 및 표시
                image = create_slime_image()
                response_text = "여기 슬라임 대시보드입니다!"
                st.markdown(response_text)
                st.image(image, caption="슬라임 대시보드", use_column_width=True)
                
                # 이미지 메시지 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "image",
                    "content": image,
                    "caption": "슬라임 대시보드",
                    "text": response_text
                })
            else:
                # 텍스트 응답 표시
                st.markdown(result["response"])
                
                # 텍스트 메시지 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"]
                })
            
            # 상태 업데이트
            st.session_state.graph_state = result
```

### LangGraph 기능별 설계 가이드

LangGraph로 리팩토링할 때 주요 고려사항:

1. **상태 타입 정의**:
   - TypedDict로 그래프가 관리하는 상태의 타입을 명확히 정의
   - 메시지 기록, 현재 입력, 응답, 플래그 등을 포함

2. **기능별 노드 분리**:
   - 각 처리 단계를 독립적인 노드 함수로 분리
   - 입력 처리, 응답 생성, 특수 응답(대시보드 등) 생성을 별도 노드로 구성

3. **조건부 흐름 제어**:
   - `add_conditional_edges`로 상태에 따른 분기 처리 구현
   - 키워드 감지, 응답 유형 등에 따라 다른 경로로 처리

4. **결과 통합 및 상태 관리**:
   - Streamlit 세션 상태와 LangGraph 상태를 동기화
   - 워크플로우 결과를 UI에 적절히 반영

5. **인간 개입 활용** (확장 가능):
   ```python
   # 인간 개입이 필요한 조건 정의
   def should_ask_human(state):
       return "불확실" in state["response"] or state["show_dashboard"]
       
   # 인간 개입 노드
   def human_review(state):
       # 실제 구현에서는 워크플로우를 일시중지하고 사용자 입력 기다림
       return {"human_approved": True}  # Streamlit에서 버튼 클릭 등으로 설정
       
   # 조건부 에지 추가
   workflow.add_conditional_edges(
       "generate_response",
       lambda state: "human_review" if should_ask_human(state) else "next_node"
   )
   ```

## 실제 구현 예시: 통합 슬라임 챗봇

위 개념을 통합한 실제 구현 예시:

```python
# langgraph_bot.py - 메인 LangGraph 워크플로우 정의
import os
from dotenv import load_dotenv
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END

# 환경 변수 로드
load_dotenv()
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")  # API 키 방식 사용
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")

# 상태 타입 정의
class ChatState(TypedDict):
    messages: List[Dict[str, Any]]  # 채팅 이력
    current_input: str              # 현재 사용자 입력
    response: str                   # 현재 응답
    dashboard_mode: bool            # 대시보드 모드 여부
    error: str                      # 오류 메시지

# 초기 상태 생성 함수
def create_initial_state() -> ChatState:
    return {
        "messages": [],
        "current_input": "",
        "response": "",
        "dashboard_mode": False,
        "error": ""
    }

# 워크플로우 노드 정의
def process_input(state: ChatState) -> Dict:
    """사용자 입력 처리 및 모드 결정"""
    try:
        # 현재 입력에서 대시보드 키워드 감지
        is_dashboard_request = any(
            keyword in state["current_input"].lower() 
            for keyword in ["대시보드", "차트", "그래프", "보여줘"]
        )
        
        # 메시지 이력 업데이트
        messages = state["messages"].copy()
        messages.append({"role": "user", "content": state["current_input"]})
        
        return {
            "messages": messages,
            "dashboard_mode": is_dashboard_request
        }
    except Exception as e:
        return {"error": f"입력 처리 오류: {str(e)}"}

def generate_llm_response(state: ChatState) -> Dict:
    """Gemini 모델로 응답 생성"""
    try:
        # Vertex AI 초기화
        vertexai.init(project=PROJECT_ID, location=LOCATION, api_key=VERTEX_API_KEY)
        model = GenerativeModel("gemini-pro")
        
        # 컨텍스트 구성
        context = "당신은 친절한 슬라임 캐릭터 AI 어시스턴트입니다. 다음 대화에 응답하세요:\n\n"
        for msg in state["messages"]:
            if msg.get("role") == "user":
                context += f"사용자: {msg['content']}\n"
            elif msg.get("role") == "assistant":
                context += f"슬라임: {msg['content']}\n"
        
        # 모델 호출
        response = model.generate_content(context)
        
        # 응답 저장
        return {"response": response.text}
    except Exception as e:
        return {"error": f"응답 생성 오류: {str(e)}"}

def update_messages(state: ChatState) -> Dict:
    """메시지 이력 업데이트"""
    messages = state["messages"].copy()
    messages.append({"role": "assistant", "content": state["response"]})
    return {"messages": messages}

def create_dashboard_response(state: ChatState) -> Dict:
    """대시보드 응답 생성"""
    response = "슬라임 대시보드를 생성했어요! (대시보드는 Streamlit UI에서 렌더링됩니다)"
    messages = state["messages"].copy()
    messages.append({"role": "assistant", "content": response, "is_dashboard": True})
    return {"messages": messages, "response": response}

# 워크플로우 그래프 구성
def create_chat_workflow() -> StateGraph:
    workflow = StateGraph(ChatState)
    
    # 노드 추가
    workflow.add_node("process_input", process_input)
    workflow.add_node("generate_llm_response", generate_llm_response)
    workflow.add_node("update_messages", update_messages)
    workflow.add_node("create_dashboard", create_dashboard_response)
    
    # 에지 및 조건부 분기 추가
    workflow.add_edge("process_input", lambda state: 
        "create_dashboard" if state["dashboard_mode"] else "generate_llm_response")
    workflow.add_edge("generate_llm_response", "update_messages")
    workflow.add_edge("update_messages", END)
    workflow.add_edge("create_dashboard", END)
    
    # 시작점 설정
    workflow.set_entry_point("process_input")
    
    return workflow

# 워크플로우 생성 및 컴파일
chat_workflow = create_chat_workflow()
chat_chain = chat_workflow.compile()
```

```python
# app.py - Streamlit 인터페이스
import streamlit as st
from PIL import Image, ImageDraw
import io
from langgraph_bot import chat_chain, create_initial_state

# 페이지 설정
st.set_page_config(
    page_title="LangGraph 슬라임 챗봇",
    page_icon="🤖",
    layout="centered"
)

# 타이틀 설정
st.title("LangGraph 슬라임 챗봇")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 슬라임 이미지 생성 함수
def create_slime_image():
    # (이전과 동일한 이미지 생성 코드)
    # ...
    return img_bytes

# 대화 이력 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("is_dashboard", False):
            # 대시보드 메시지의 경우 이미지도 표시
            st.markdown(message["content"])
            # 이미지 생성 및 표시
            image = create_slime_image()
            st.image(image, caption="슬라임 대시보드", use_column_width=True)
        else:
            # 일반 텍스트 메시지
            st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("무엇이든 물어보세요"):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 사용자 메시지 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # LangGraph 워크플로우 상태 초기화
    state = create_initial_state()
    state["messages"] = st.session_state.messages[:-1]  # 현재 입력 제외 이전 이력
    state["current_input"] = prompt
    
    # LangGraph 워크플로우 실행
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            # 워크플로우 실행 및 결과 획득
            result = chat_chain.invoke(state)
            
            # 결과 표시
            last_message = result["messages"][-1]
            if last_message.get("is_dashboard", False):
                # 대시보드 메시지의 경우 이미지도 표시
                st.markdown(last_message["content"])
                image = create_slime_image()
                st.image(image, caption="슬라임 대시보드", use_column_width=True)
            else:
                # 일반 텍스트 메시지
                st.markdown(last_message["content"])
                
            # 결과 저장
            st.session_state.messages = result["messages"]
```

## 추가 기능 확장

1. **메모리 관리**: LangGraph의 메모리 시스템을 활용하여 대화 이력을 효율적으로 관리할 수 있습니다.

2. **병렬 처리**: 여러 작업을 병렬로 실행하여 응답 시간을 단축할 수 있습니다.
   ```python
   # 분할 정복 패턴
   from langgraph.graph import END, StateGraph
   from langgraph.pregel import Pregel
   
   # 병렬 처리할 노드들 정의
   # ...
   
   # Pregel 활용 병렬 처리
   pregel = Pregel(lambda: {"result": ""})
   pregel.map("parallel_task", parallel_task_function)
   pregel.combine("combine_results", combine_function)
   
   # 메인 그래프에 통합
   workflow.add_node("parallel_processing", pregel)
   ```

3. **인간 개입 (Human-in-the-loop)**: 필요시 워크플로우를 일시 중지하고 사용자 입력을 기다릴 수 있습니다.
   ```python
   from langgraph.checkpoint.memory import MemorySaver
   
   # 체크포인터 설정
   checkpointer = MemorySaver()
   
   # 인간 개입 노드 정의
   def human_intervention(state):
       # 이 함수는 Streamlit 앱에서 다시 호출될 때까지 대기
       return {}
   
   # 그래프 구성 시 체크포인터 설정
   workflow = StateGraph(ChatState, checkpointer=checkpointer)
   
   # 인간 개입 노드 추가
   workflow.add_node("human_review", human_intervention)
   ```

## 문제 해결

1. **API 키 오류**: API 키가 올바르게 설정되었는지 확인하고, 필요한 권한이 있는지 확인하세요.

2. **워크플로우 실행 오류**: 각 노드의 입출력이 타입 시스템과 일치하는지 확인하세요.

3. **성능 최적화**: 대용량 상태는 메모리 사용량에 영향을 줄 수 있으므로, 필요한 데이터만 상태에 유지하세요.

## 추가 자료

- [Vertex AI 공식 문서](https://cloud.google.com/vertex-ai/docs)
- [LangGraph 공식 문서](https://python.langchain.com/docs/langgraph)
- [Gemini API 레퍼런스](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)

## 팁과 모범 사례

1. **환경 변수 관리**
   - 중요한 인증 정보와 설정은 항상 `.env` 파일에 보관하고 버전 제어에서 제외하세요.
   - `python-dotenv` 라이브러리로 쉽게 환경 변수를 로드할 수 있습니다.

2. **그래프 설계**
   - 단순한 워크플로우는 `MessageGraph`를, 복잡한 상태 관리가 필요한 경우 `StateGraph`를 사용하세요.
   - 노드 함수는 명확하고 단일 책임을 가지도록 설계하세요.

3. **비용 및 성능 최적화**
   - 개발 중에는 `gemini-pro`보다 빠르고 저렴한 `gemini-flash`와 같은 모델을 사용해 보세요.
   - 비용 모니터링 도구를 설정하여 API 사용량을 추적하세요.
