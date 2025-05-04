# LangGraph 서버

LangGraph 서버는 자연어 쿼리를 분석하고 적절한 응답을 생성하는 워크플로우를 실행하는 컴포넌트입니다.

## 주요 기능

- 사용자 쿼리의 의도 감지 (로그 조회, 메트릭 분석, 알림 확인 등)
- Loki 라벨을 활용한 정확한 파라미터 추출 (서비스 이름, 로그 레벨, 시간 범위 등)
- API 서버를 통한 로그/메트릭 데이터 쿼리
- 로그 데이터 분석 및 요약 생성
- 사용자 친화적인 응답 구성
- Grafana-MCP를 통한 Loki 및 Tempo 데이터 접근 (직접 API 호출하지 않음)
- LLM을 활용한 라벨 기반 LogQL 쿼리 생성

## 워크플로우 구조

```
의도 감지 → 라벨 조회 → 파라미터 추출(LLM 활용) → 로그 쿼리 → 트레이스 연동 → 로그 분석 → 응답 생성
```

## 사용 기술

- LangGraph: 워크플로우 구성 및 실행
- LangChain: LLM 프롬프트 및 체인 구성
- Gemini Flash 2.0: 자연어 처리 및 로그 분석
- FastAPI: 웹 API 서버
- Pydantic: 데이터 모델 정의
- Grafana-MCP: Loki 및 Tempo 데이터 접근용 통합 인터페이스

## 환경 변수

| 환경 변수 | 설명 | 기본값 |
|---------|------|--------|
| `GOOGLE_API_KEY` | Google Gemini API 키 | (필수) |
| `API_URL` | API 서버 URL | http://localhost:8002 |
| `MCP_URL` | Grafana MCP URL | http://localhost:8000 |
| `TEMPO_MCP_URL` | Tempo MCP URL | http://localhost:8004 |
| `GRAFANA_URL` | Grafana URL | http://localhost:8003 |
| `PORT` | 서버 포트 | 8001 |

## API 엔드포인트

- **GET** `/health`: 서버 상태 확인
- **POST** `/analyze`: 쿼리 분석 및 처리
  - 요청 본문:
    ```json
    {
      "user_id": "user123",
      "query": "지난 1시간 동안의 api-gateway 서비스 오류 로그를 분석해줘",
      "context": {}
    }
    ```
  - 응답:
    ```json
    {
      "response": "분석 결과...",
      "context": {}
    }
    ```
- **GET** `/services`: 사용 가능한 서비스 목록 조회
- **GET** `/labels`: Loki에서 사용 가능한 라벨 목록 조회
- **GET** `/get_all_labels`: 모든 라벨과 해당 값 조회

## 라벨 활용 LLM 처리 과정

1. Grafana-MCP를 통해 Loki에서 사용 가능한 모든 라벨과 값 조회
2. 라벨 정보와 함께 사용자 쿼리를 LLM에 전달하여 정확한 파라미터 추출
3. 추출된 파라미터로 LogQL 쿼리 생성
4. 트레이스 ID 연계를 통한 통합 분석 제공

## 실행 방법

### 로컬 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python langgraph_server.py
```

### Docker 환경

```bash
# 직접 빌드 및 실행
docker build -t mcp-langgraph -f Dockerfile .
docker run -p 8001:8001 -e GOOGLE_API_KEY=your_api_key mcp-langgraph

# docker-compose 사용
docker-compose up langgraph
```

## 로그

로그는 기본적으로 `logs/langgraph.log` 파일에 기록됩니다. Docker 환경에서는 `/app/logs` 디렉토리에 마운트됩니다.

## 의존 관계

LangGraph 서버는 다음 서비스에 의존합니다:
- Grafana-MCP (8003): Loki 로그 데이터 접근 및 라벨 조회
- Tempo-MCP (8004): 트레이스 데이터 조회
- API 서버 (8002): 추가 서비스 연동 