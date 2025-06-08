# LangGraph 기반 AI 에이전트 API 서버

## 개요

이 프로젝트는 LangGraph와 FastAPI를 기반으로 한 AI 에이전트 시스템입니다. Supervisor 패턴을 사용하여 여러 전문화된 에이전트들이 협업하는 구조로 설계되었습니다.

## 주요 특징

- **Supervisor 패턴**: 사용자 요청을 분석하여 적절한 전문 에이전트에게 라우팅
- **모듈화된 구조**: API, Core, Graph 레이어로 명확히 분리
- **MCP 통합**: langchain-mcp-adapters를 통한 외부 시스템 연동
- **비동기 처리**: FastAPI와 LangGraph의 비동기 기능 활용

## 에이전트 구성

### 1. Supervisor Agent
- 사용자 요청을 분석하여 적절한 전문 에이전트 선택
- 구조화된 출력을 통한 지능적 라우팅

### 2. Grafana Agent (`grafana_mcp_agent.py`)
- Grafana 대시보드 데이터 조회 및 분석
- 메트릭 쿼리 및 데이터 분석
- 시스템 상태 및 성능 데이터 분석
- create_react_agent 기반으로 구현

### 3. Grafana Renderer Agent (`grafana_renderer_mcp_agent.py`)
- Grafana 대시보드 시각화 및 렌더링
- 차트, 그래프 이미지 생성
- 대시보드 스크린샷 및 리포트 생성
- create_react_agent 기반으로 구현

### 4. DevOps Agent
- 컨테이너, Kubernetes, CI/CD 관리
- 인프라 모니터링 및 자동화

### 5. General Agent
- 일반적인 질문 및 기본적인 DevOps 개념 설명

## 프로젝트 구조

```
/backend
├── app/
│   ├── __init__.py
│   │
│   ├── api/                     # API 레이어
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── endpoints.py     # API 엔드포인트
│   │       └── schemas.py       # Pydantic 모델
│   │
│   ├── core/                    # Core 레이어
│   │   ├── __init__.py
│   │   └── config.py            # 설정 관리
│   │
│   └── graph/                   # Graph 레이어
│       ├── __init__.py
│       ├── instance.py          # LangGraph 인스턴스 (Singleton)
│       ├── state.py             # 에이전트 상태 정의
│       └── agents/              # 개별 에이전트
│           ├── __init__.py
│           ├── supervisor.py
│           ├── grafana_mcp_agent.py
│           ├── grafana_renderer_mcp_agent.py
│           ├── devops_agent.py
│           └── general_agent.py
│
├── main.py                      # 진입점 (새로운 구조)
├── requirements.txt
└── langgraph.json
```

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```env
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key

# MCP 서버 설정
GRAFANA_MCP_URL=http://localhost:8001
GRAFANA_RENDERER_MCP_URL=http://localhost:8002

# 애플리케이션 설정
APP_NAME="DevOps AI Assistant API"
DEBUG=true
```

### 3. 서버 실행

#### 개발 환경
```bash
# 개발 모드 (자동 리로드)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 또는 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### LangGraph 서버 모드
```bash
langgraph up
```

## API 엔드포인트

### 채팅
- `POST /api/v1/chat` - 일반 채팅
- `POST /api/v1/chat/stream` - 스트리밍 채팅

### 세션 관리
- `POST /api/v1/sessions` - 세션 생성
- `GET /api/v1/sessions/{session_id}/messages` - 메시지 이력
- `DELETE /api/v1/sessions/{session_id}` - 세션 삭제

### 시스템
- `GET /api/v1/health` - 헬스체크
- `GET /api/v1/models` - 사용 가능한 모델
- `GET /api/v1/tools` - 사용 가능한 도구

## 사용 예시

### 1. 채팅 요청

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Grafana에서 CPU 사용률 차트를 보여줘",
    "thread_id": "test-thread"
  }'
```

### 2. 응답 예시

```json
{
  "id": "msg-123",
  "content": "CPU 사용률 차트를 생성했습니다...",
  "timestamp": "2024-01-15T10:30:00Z",
  "metadata": {
    "thread_id": "test-thread",
    "agent_used": "grafana_renderer_agent",
    "tools_used": ["render_dashboard_panel"],
    "supervisor_reasoning": "사용자가 차트를 요청했으므로 grafana_renderer_agent를 선택했습니다."
  }
}
```

## 에이전트 선택 로직

Supervisor는 다음과 같은 기준으로 에이전트를 선택합니다:

- **데이터 조회/분석** → `grafana_agent`
- **차트/이미지 생성** → `grafana_renderer_agent`  
- **인프라/DevOps 작업** → `devops_agent`
- **일반적인 질문** → `general_agent`

## 개발 가이드

### 새로운 에이전트 추가

1. `app/graph/agents/` 에 새 에이전트 파일 생성
2. `create_react_agent` 기반으로 구현
3. `supervisor.py`의 라우팅 로직에 추가
4. `instance.py`의 그래프에 노드 추가

### MCP 도구 추가

1. 해당 에이전트 파일에서 MCP 클라이언트 설정
2. 도구 필터링 로직 구현
3. ReAct 프롬프트에 도구 사용법 명시

## 로깅

모든 에이전트의 실행 과정은 상세히 로깅됩니다:

```
2024-01-15 10:30:00 - INFO - Supervisor selected: grafana_renderer_agent
2024-01-15 10:30:01 - INFO - Grafana renderer agent processing request
2024-01-15 10:30:05 - INFO - Chart rendered successfully
```

## 문제 해결

### 일반적인 문제

1. **MCP 연결 실패**: MCP 서버 URL과 상태 확인
2. **API 키 오류**: 환경 변수 설정 확인  
3. **에이전트 라우팅 실패**: Supervisor 로그 확인

### 디버깅

```bash
# 로그 레벨 설정
export LOG_LEVEL=DEBUG

# 자세한 에이전트 실행 과정 확인
python -c "
import asyncio
from app.graph.instance import process_chat_message
result = asyncio.run(process_chat_message('테스트 메시지'))
print(result)
"
```

## 기여하기

1. 이슈 생성
2. 기능 브랜치 생성
3. 코드 작성 및 테스트
4. Pull Request 제출

## 라이선스

MIT License 