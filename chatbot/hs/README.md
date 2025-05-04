# 마이크로서비스 기반 로그 및 트레이스 분석 시스템

이 프로젝트는 마이크로서비스 아키텍처 환경에서 로그와 트레이스 데이터를 수집, 저장, 분석하기 위한 통합 시스템입니다. LLM(Large Language Model)을 활용하여 로그와 트레이스 데이터를 분석하고, 시스템 상태 및 오류를 직관적으로 이해할 수 있도록 지원합니다.

## 시스템 구성 요소

프로젝트는 다음과 같은 구성 요소로 이루어져 있습니다:

- **LangGraph 서버**: LLM 기반 로그 및 트레이스 분석 기능 제공
- **Loki API**: 로그 쿼리 및 검색 기능 제공
- **Loki MCP**: Loki API와 Grafana 시스템 간의 통합 인터페이스
- **Tempo API**: 트레이스 쿼리 및 검색 기능 제공
- **Tempo MCP**: Tempo API와 Grafana 시스템 간의 통합 인터페이스
- **Streamlit 애플리케이션**: 사용자 인터페이스 제공

## 시작하기

### 사전 요구 사항

- Docker 및 Docker Compose
- Python 3.9 이상 (직접 실행 시)
- Loki 및 Tempo 인스턴스 접근 권한

### 환경 변수 설정

주요 환경 변수는 `.env` 파일에 설정할 수 있습니다:

```
GOOGLE_API_KEY=your_google_api_key
LOKI_URL=http://loki:3100
TEMPO_URL=http://tempo:3200
GRAFANA_URL=http://grafana:3000
```

### 실행 방법

Docker Compose를 사용하여 전체 시스템을 시작:

```bash
docker-compose up -d
```

서비스 접근:

- Streamlit UI: http://localhost:8501
- LangGraph API: http://localhost:8001
- Loki MCP API: http://localhost:8003
- Tempo MCP API: http://localhost:8004

## 주요 기능

### 로그 분석

- 로그 쿼리 및 필터링
- 로그 패턴 분석
- 오류 및 경고 감지
- 서비스별 로그 통계

### 트레이스 분석

- 분산 트레이싱 데이터 조회
- 서비스 간 호출 관계 시각화
- 성능 병목 지점 식별
- 오류 발생 지점 탐지

### LLM 기반 분석

- 자연어 쿼리를 통한 로그 및 트레이스 검색
- 로그와 트레이스 데이터의 통합 분석
- 문제 상황에 대한 요약 및 해결 방안 제시

## 폴더 구조

- `langgraph/`: LLM 기반 로그 및 트레이스 분석 서버
- `loki-api/`: Loki API 서버
- `loki-mcp/`: Loki MCP 서버
- `tempo-api/`: Tempo API 서버
- `tempo-mcp/`: Tempo MCP 서버
- `streamlit/`: Streamlit 기반 UI
- `logs/`: 시스템 로그 파일
- `mcp-grafana-main/`: Grafana 통합 코드

## 기여 방법

1. 이 리포지토리를 포크합니다.
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`).
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`).
4. 브랜치에 변경 사항을 푸시합니다 (`git push origin feature/amazing-feature`).
5. Pull Request를 생성합니다.

## 라이선스

이 프로젝트는 MIT 라이선스에 따라 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요. 