## 시나리오 1
- 사용자는 'user-service' 에 최근 하루동안 문제가 발생함을 확인하고, 원인이 무엇인지 찾고 싶어한다. 챗봇을 통해 Agent 에게 원인 파악을 지시한다.
- Agent 는 loki agent 에게 요청하여 최근에 이상 로그가 있었는지 확인한다.
- Agent 는 grafana agent 에게 요청하여 대시보드 목록을 확인하고, 'user-service' 와 관련된 어떤 패널이 있는지 확인한다. 
  - 'user-service' 의 대시보드 패널 중 '