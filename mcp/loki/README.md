# Loki MCP 서버

MCP(Monitoring Control Plane) 서버로, Loki API와 Grafana 시스템 간의 통합 인터페이스를 제공합니다.

## 구성 요소

- `mcp_server.py`: Loki MCP 서버의 주요 코드
- `Dockerfile`: 컨테이너화를 위한 도커 이미지 설정
- `requirements.txt`: 필요한 Python 패키지 목록

## 주요 기능

- Loki API 통합 및 결과 포맷팅
- Grafana 인터페이스 제공
- 로그 데이터 검색 및 필터링을 위한 JSON-RPC API 제공
- 데이터 소스 관리 및 연결

## API 엔드포인트

### JSON-RPC 엔드포인트

- `/rpc/v1`: JSON-RPC 2.0 프로토콜을 사용한 API 요청 처리

### 주요 메서드

- `query_loki`: Loki 데이터 소스에 쿼리 실행
- `get_loki_labels`: Loki의 사용 가능한 라벨 목록 조회
- `list_loki_label_values`: 특정 라벨의 가능한 값 목록 조회
- `list_datasources`: 구성된 데이터 소스 목록 조회

## 환경 변수

- `LOKI_API_URL`: Loki API 서버 URL (기본값: "http://loki-api:8002")
- `PORT`: MCP 서버 포트 (기본값: 8003)
- `GRAFANA_URL`: Grafana 서버 URL (기본값: "http://grafana:3000")

## 실행 방법

### 도커 실행

```bash
docker build -t loki-mcp .
docker run -p 8003:8003 -e LOKI_API_URL=http://your-loki-api:8002 loki-mcp
```

### 직접 실행

```bash
pip install -r requirements.txt
python mcp_server.py
```

## 사용 예제

```python
import requests

# 로그 쿼리 예제
response = requests.post(
    "http://localhost:8003/rpc/v1",
    json={
        "jsonrpc": "2.0",
        "method": "query_loki",
        "params": {
            "query": '{service="order-service"}',
            "start": "2023-01-01T00:00:00Z",
            "end": "2023-01-02T00:00:00Z",
            "limit": 100
        },
        "id": 1
    }
)

print(response.json())
```

## 관련 서비스

- `loki-api`: Loki API 서버와 직접 통신
- `langgraph`: LangGraph 서버를 통한 로그 분석 결과 전달
- `tempo-mcp`: Tempo MCP 서버와 통합하여 로그-트레이스 상관 관계 분석 