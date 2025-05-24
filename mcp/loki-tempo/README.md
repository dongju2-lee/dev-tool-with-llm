# Loki & Tempo MCP Server

Loki와 Tempo를 사용한 관찰성(Observability) MCP 서버입니다. 이 서버는 DevOps 환경에서 로그 분석과 분산 추적을 위한 도구들을 제공합니다.

## 🚀 주요 기능

### 📝 로그 분석 (Loki)
- **query_logs**: LogQL을 사용한 로그 쿼리 및 필터링
- **analyze_logs_pattern**: 로그 패턴 분석 및 이상 탐지

### 🔍 분산 추적 (Tempo) 
- **search_traces**: TraceQL을 사용한 트레이스 검색
- **get_trace_details**: 특정 트레이스의 상세 스팬 정보
- **get_service_metrics**: 서비스별 성능 지표 (응답시간, 에러율 등)

### 🔗 상관 분석
- **correlate_logs_and_traces**: 로그와 트레이스 간 상관관계 분석

### ⚙️ 관리 기능
- **check_environment**: 환경 설정 및 연결 상태 확인
- **update_environment_settings**: 런타임 환경 설정 업데이트
- **export_data**: 분석 데이터 내보내기 (JSON/CSV)

## 📋 요구사항

- Python 3.8+
- Loki 서버 (로그 수집)
- Tempo 서버 (트레이스 수집)
- Grafana (대시보드, 선택사항)

## 🛠️ 설치 및 설정

### 1. 패키지 설치

```bash
cd mcp/loki-tempo
pip install -r requirements.txt
```

### 2. 환경 설정

`example.env` 파일을 참고하여 `.env` 파일을 생성하세요:

```bash
cp example.env .env
```

`.env` 파일 설정 예시:
```env
# 서버 설정
MCP_HOST=0.0.0.0
MCP_PORT=10002

# Loki 설정
LOKI_URL=http://localhost:3100
LOKI_AUTH_USER=admin
LOKI_AUTH_PASSWORD=password

# Tempo 설정  
TEMPO_URL=http://localhost:3200
TEMPO_AUTH_USER=admin
TEMPO_AUTH_PASSWORD=password

# Grafana 대시보드 설정
GRAFANA_URL=http://localhost:3000
LOKI_DASHBOARD_ID=loki-dashboard
TEMPO_DASHBOARD_ID=tempo-dashboard

# 기본값 설정
DEFAULT_LOG_LIMIT=100
DEFAULT_TRACE_LIMIT=20
DEFAULT_TIME_RANGE=1h
```

### 3. 서버 실행

#### 직접 실행
```bash
python loki_tempo_mcp_server.py
```

#### 실행 스크립트 사용
```bash
python run_server.py
```

## 🧪 테스트

MCP 서버가 정상적으로 작동하는지 확인:

```bash
python test_mcp.py
```

테스트 항목:
- MCP 서버 연결
- 도구 목록 조회
- 환경 설정 확인
- 로그 쿼리 기능
- 트레이스 검색 기능

## 🔧 사용법

### LangGraph 프로젝트에서 사용

`chatbot/dj/back/agents/research_agent.py`에서 MCP 클라이언트 설정:

```python
MCP_SERVERS = {
    "loki_tempo": {
        "url": "http://localhost:10002/sse",
        "transport": "sse",
    }
}
```

### 도구 사용 예시

#### 1. 로그 쿼리
```python
# 에러 로그 검색
await query_logs(
    query='{service="api-server"} |= "error"',
    time_range="1h",
    limit=50
)

# 특정 서비스 로그
await query_logs(
    query='{}',
    service="user-service",
    level="error",
    time_range="24h"
)
```

#### 2. 트레이스 검색
```python
# 느린 요청 찾기
await search_traces(
    service_name="api-server",
    min_duration="1s",
    time_range="1h"
)

# 에러 트레이스 찾기
await search_traces(
    tags={"error": "true"},
    time_range="1h"
)
```

#### 3. 상관관계 분석
```python
# 특정 트레이스의 관련 로그 찾기
await correlate_logs_and_traces(
    trace_id="abc123def456",
    time_window="5m"
)
```

## 📊 장애 분석 워크플로우

1. **환경 점검**: `check_environment`로 시스템 상태 확인
2. **로그 분석**: `query_logs`로 오류 패턴 확인
3. **트레이스 분석**: `search_traces`로 성능 이슈 확인
4. **상관관계 분석**: `correlate_logs_and_traces`로 연관성 파악
5. **메트릭 확인**: `get_service_metrics`로 서비스 상태 확인
6. **패턴 분석**: `analyze_logs_pattern`로 반복 문제 식별

## 🐛 문제 해결

### 연결 오류
- Loki/Tempo 서버가 실행 중인지 확인
- URL과 포트 설정 확인
- 인증 정보 확인

### 권한 오류
- 인증 사용자명/비밀번호 확인
- Loki/Tempo 서버 권한 설정 확인

### 데이터 없음
- 로그/트레이스가 실제로 수집되고 있는지 확인
- 시간 범위 설정 확인
- 쿼리 문법 확인

## 📚 참고 자료

- [Loki LogQL 문서](https://grafana.com/docs/loki/latest/logql/)
- [Tempo TraceQL 문서](https://grafana.com/docs/tempo/latest/traceql/)
- [FastMCP 문서](https://fastmcp.org/)

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 