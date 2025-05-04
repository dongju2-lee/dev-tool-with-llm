# Tempo MCP 서버

MCP(Monitoring Control Plane) 서버로, Tempo API와 Grafana 시스템 간의 통합 인터페이스를 제공합니다.

## 구성 요소

- `mcp_server.py`: Tempo MCP 서버의 주요 코드
- `Dockerfile`: 컨테이너화를 위한 도커 이미지 설정
- `requirements.txt`: 필요한 Python 패키지 목록

## 주요 기능

- Tempo API 통합 및 결과 포맷팅
- Grafana 인터페이스 제공
- 트레이스 데이터 검색 및 필터링을 위한 JSON-RPC API 제공
- 트레이스 기반 로그 연관 분석 지원

## API 엔드포인트

### JSON-RPC 엔드포인트

- `/rpc/v1`: JSON-RPC 2.0 프로토콜을 사용한 API 요청 처리

### 주요 메서드

- `query_tempo`: Tempo 데이터 소스에 쿼리 실행
- `get_trace`: 특정 트레이스 ID로 트레이스 조회
- `get_services`: 모니터링되는 서비스 목록 조회
- `get_operations`: 서비스별 작업 목록 조회
- `find_traces`: 다양한 조건으로 트레이스 검색

## 환경 변수

- `TEMPO_API_URL`: Tempo API 서버 URL (기본값: "http://tempo-api:8005")
- `PORT`: MCP 서버 포트 (기본값: 8004)
- `GRAFANA_URL`: Grafana 서버 URL (기본값: "http://grafana:3000")

## 실행 방법

### 도커 실행

```bash
docker build -t tempo-mcp .
docker run -p 8004:8004 -e TEMPO_API_URL=http://your-tempo-api:8005 tempo-mcp
```

### 직접 실행

```bash
pip install -r requirements.txt
python mcp_server.py
```

## 사용 예제

```python
import requests

# 트레이스 ID로 트레이스 조회 예제
response = requests.post(
    "http://localhost:8004/rpc/v1",
    json={
        "jsonrpc": "2.0",
        "method": "get_trace",
        "params": {
            "trace_id": "a4232e946496f5f98d9bfc70eb9458e1"
        },
        "id": 1
    }
)

print(response.json())

# 서비스 기반 트레이스 검색 예제
response = requests.post(
    "http://localhost:8004/rpc/v1",
    json={
        "jsonrpc": "2.0",
        "method": "query_tempo",
        "params": {
            "service": "order-service",
            "start": "2023-01-01T00:00:00Z", 
            "end": "2023-01-02T00:00:00Z",
            "limit": 20
        },
        "id": 1
    }
)

print(response.json())
```

## 관련 서비스

- `tempo-api`: Tempo API 서버와 직접 통신
- `langgraph`: LangGraph 서버를 통한 트레이스 분석 결과 전달
- `loki-mcp`: Loki MCP 서버와 통합하여 로그-트레이스 상관 관계 분석 