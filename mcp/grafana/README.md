# Grafana MCP 서버
- Grafana MCP (공식)
- Grafana renderer MCP (새로 개발)
- 두 가지 MCP 서버를 docker compose 로 띄웁니다.

## 준비사항
- GRAFANA_API_KEY, GRAFANA_URL 환경 변수를 설정해야 합니다.
- Grafana service account token 을 발급받아, 환경변수로 입력해야 합니다.
  - grafana 접속 - users and access 탭에서 service account 생성 후 token 발급 (admin 권한)
- grafana 와 grafana renderer 가 떠있어야 합니다.

## 사용 방법
- docker compose up -d

## 테스트 방법
- MCP inspector 로 테스트 가능합니다.
  - npx @modelcontextprotocol/inspector
  - 이후 접속해서 MCP 서버 주소 입력, 도구 테스트