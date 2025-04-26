# Grafana MCP 테스트 인프라

이 디렉토리는 Grafana MCP Python 서버를 테스트하기 위한 인프라를 제공합니다. Docker Compose를 사용하여 다음과 같은 서비스들을 실행합니다:

- **Grafana**: 대시보드 시각화 서비스 (포트 3000)
- **Prometheus**: 모니터링 및 메트릭 데이터 저장소 (포트 9090)
- **Target API**: 테스트용 Spring Boot 애플리케이션 (포트 8080)
- **Grafana 이미지 렌더러**: 대시보드 이미지 생성 서비스 (포트 8081)

## 사용 방법

### 1. 테스트 인프라 시작

다음 명령어로 테스트 인프라를 시작합니다:

```bash
cd test_infra
docker compose up -d
```

### 2. 서비스 접속

- **Grafana**: http://localhost:3000 (계정: admin / 비밀번호: admin)
- **Prometheus**: http://localhost:9090
- **Target API**: http://localhost:8080/actuator/prometheus

### 3. Grafana MCP 서버 실행

테스트 인프라가 실행된 상태에서, 다음과 같이 Grafana MCP 서버를 시작할 수 있습니다:

```bash
# 환경 변수 설정
export GRAFANA_URL=http://localhost:3000
export GRAFANA_API_KEY=<생성한_API_키>

# MCP 서버 실행
grafana-mcp serve
```

### 4. Grafana API 키 생성 방법

1. Grafana에 로그인 (http://localhost:3000)
2. 왼쪽 메뉴 > Administration > Service accounts로 이동
3. "Add service account" 클릭
4. 이름 입력 (예: "mcp-test")과 역할 선택 (예: "Admin")
5. "Add" 클릭하여 서비스 계정 생성
6. "Add service account token" 클릭
7. 토큰 이름 입력 후 "Generate token" 클릭
8. 생성된 토큰을 `GRAFANA_API_KEY` 환경 변수로 사용

### 5. 테스트 인프라 종료

```bash
cd test_infra
docker compose down
```

볼륨을 포함하여 모든 데이터를 삭제하려면:

```bash
docker compose down -v
``` 