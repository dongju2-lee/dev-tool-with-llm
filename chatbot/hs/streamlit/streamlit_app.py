"""
MCP DevOps 어시스턴트 - Streamlit 프론트엔드 애플리케이션
"""
import os
import json
import time
import requests
import streamlit as st
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# URL 설정
MCP_URL = os.getenv("MCP_URL", "http://localhost:8001")
LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:8001")
TEMPO_MCP_URL = os.getenv("TEMPO_MCP_URL", "http://localhost:8014")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://localhost:3200")

# Streamlit 페이지 설정
st.set_page_config(
    page_title="MCP DevOps 어시스턴트",
    page_icon="🛠️",
    layout="wide",
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "context" not in st.session_state:
    st.session_state.context = {}

if "services" not in st.session_state:
    st.session_state.services = []

# LangGraph API 요청 함수
def query_langgraph(user_input):
    start_time = time.time()
    
    # 요청 데이터 구성
    data = {
        "user_id": "streamlit_user",
        "query": user_input,
        "context": st.session_state.context
    }
    
    try:
        # LangGraph API 요청
        response = requests.post(f"{LANGGRAPH_URL}/analyze", json=data, timeout=120)
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            # 컨텍스트 업데이트
            if "context" in result:
                st.session_state.context = result["context"]
                
            # API 응답 처리
            api_response = result.get("response", {})
            return api_response, response_time
        else:
            return f"오류: LangGraph API 응답 코드 {response.status_code}\n{response.text}", response_time
    except requests.exceptions.ConnectionError:
        return "오류: LangGraph 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.", time.time() - start_time
    except requests.exceptions.Timeout:
        return "오류: LangGraph API 요청 시간이 초과되었습니다. 나중에 다시 시도하세요.", time.time() - start_time
    except Exception as e:
        return f"오류: {str(e)}", time.time() - start_time

# Tempo 트레이스 조회 함수
def query_tempo_traces(service_name=None, time_period="1h", error_only=False, trace_id=None):
    try:
        if trace_id:
            # 특정 트레이스 ID 조회
            response = requests.get(f"{TEMPO_MCP_URL}/api/tempo/trace/{trace_id}", timeout=30)
        else:
            # 여러 트레이스 검색
            data = {
                "service_name": service_name or "api-gateway",
                "error_traces": error_only,
                "time_period": time_period
            }
            response = requests.post(f"{TEMPO_MCP_URL}/api/tempo/query_traces", json=data, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Tempo API 오류: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Tempo 조회 오류: {str(e)}"}

# 서비스 목록 가져오기
def get_services():
    try:
        response = requests.get(f"{LANGGRAPH_URL}/services", timeout=10)
        if response.status_code == 200:
            result = response.json()
            services = result.get("services", [])
            st.session_state.services = services
            return services
        else:
            return []
    except:
        return []

# 메인 인터페이스
st.title("🛠️ MCP DevOps 어시스턴트")
st.markdown("""
이 어시스턴트는 로그 분석, 메트릭 모니터링 및 알림 체크를 도와줍니다.
""")

# 사이드바
with st.sidebar:
    st.header("📋 사용 가이드")
    
    st.subheader("지원하는 기능")
    st.markdown("""
    - 📊 **로그 분석**: 서비스 로그 조회 및 분석
    - 🔍 **트레이스 추적**: 서비스 트레이스 조회 및 분석
    - 📈 **메트릭 분석**: 시스템 성능 지표 조회 (준비 중)
    - 🔔 **알림 체크**: 알림 상태 확인 (준비 중)
    """)
    
    # 서비스 목록 표시
    services = get_services()
    if services:
        st.subheader("지원하는 서비스")
        service_text = ", ".join([f"`{s}`" for s in services if s != "all"]) 
        st.markdown(f"{service_text}")
    
    st.subheader("예시 쿼리")
    st.markdown("""
    - "지난 1시간 동안의 api-gateway 서비스 오류 로그를 보여줘"
    - "오늘 auth 서비스에서 발생한 ERROR 로그 분석해줘"
    - "지난 4시간 동안의 서비스 오류 로그를 보여주고 트레이스를 추적해줘"
    - "payment-service의 최근 트레이스를 보여줘"
    - "현재 MCP 서비스의 상태는 어때?"
    """)
    
    # 서버 상태 확인
    st.subheader("서버 상태")
    try:
        health_response = requests.get(f"{LANGGRAPH_URL}/health", timeout=5)
        if health_response.status_code == 200:
            st.success("LangGraph 서버 연결됨 ✅")
        else:
            st.error(f"LangGraph 서버 응답 오류: {health_response.status_code}")
    except:
        st.error("LangGraph 서버 연결 실패 ❌")
        
    try:
        tempo_health_response = requests.get(f"{TEMPO_MCP_URL}/health", timeout=5)
        if tempo_health_response.status_code == 200:
            st.success("Tempo MCP 서버 연결됨 ✅")
        else:
            st.error(f"Tempo MCP 서버 응답 오류: {tempo_health_response.status_code}")
    except:
        st.error("Tempo MCP 서버 연결 실패 ❌")
    
    # 채팅 초기화 버튼
    if st.button("채팅 초기화"):
        st.session_state.messages = []
        st.session_state.context = {}
        st.success("채팅이 초기화되었습니다.")

# 채팅 이력 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 받기
user_input = st.chat_input("질문을 입력하세요...")

if user_input:
    # 사용자 메시지 표시
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 어시스턴트 응답 생성 중 표시
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("응답 생성 중...")
        
        # LangGraph API 요청
        response_data, response_time = query_langgraph(user_input)
        
        # 응답 내용 구성
        if isinstance(response_data, str):
            # 오류 응답인 경우
            final_response = response_data
        else:
            # 정상 응답인 경우
            # LLM 요약 정보가 있으면 우선적으로 표시
            if "summary" in response_data and response_data["summary"]:
                final_response = response_data["summary"]
            else:
                # 요약이 없는 경우 기본 응답 구성
                final_response = "요청을 처리했습니다."
                
                # 의도 표시
                intent = response_data.get("intent")
                if intent:
                    if intent == "LOG_QUERY":
                        intent_str = "로그 쿼리"
                    elif intent == "TRACE_QUERY":
                        intent_str = "트레이스 쿼리"
                    else:
                        intent_str = intent
                    final_response += f"\n\n**의도**: {intent_str}"
                
                # 로그 데이터가 있으면 표시
                log_data = response_data.get("log_data", [])
                if log_data:
                    final_response += f"\n\n**로그 데이터**: {len(log_data)}개 항목 찾음"
        
        # 트레이스 URL이 있는지 확인
        trace_urls = []
        if "trace_data" in response_data and response_data["trace_data"] is not None:
            traces = response_data.get("trace_data", [])
            for trace in traces:
                if "traceUrl" in trace:
                    trace_urls.append(trace["traceUrl"])
        
        # 트레이스 URL 표시
        if trace_urls:
            final_response += "\n\n**트레이스 링크:**\n"
            for i, url in enumerate(trace_urls):
                final_response += f"- [트레이스 {i+1}]({url})\n"
        
        # 응답 표시
        message_placeholder.markdown(final_response)
        
        # 디버그 정보 (개발 중일 때만 표시)
        st.caption(f"응답 시간: {response_time:.2f}초")
    
    # 어시스턴트 메시지 저장
    st.session_state.messages.append({"role": "assistant", "content": final_response}) 