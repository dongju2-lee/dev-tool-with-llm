# Grafana MCP 테스트 인프라

### docker compose up 실행 시 아래 컨테이너를 띄웁니다.
- target-api (spring boot)
- prometheus
- grafana
- grafana-renderer (대시보드 PNG 조회)
- loki (로그 수집 및 분석)
- tempo (분산 추적)

### Grafana 대시보드 접근 방법
1. 브라우저에서 `http://localhost:3000`으로 접속
2. 계정: admin / 비밀번호: admin
3. 기본 대시보드:
   - Spring Boot 대시보드: 애플리케이션 메트릭 확인
   - Application Logs: Loki를 사용한 로그 분석
   - Application Traces: Tempo를 사용한 분산 추적
   - Observability Dashboard: 메트릭, 로그, 트레이스 통합 대시보드
