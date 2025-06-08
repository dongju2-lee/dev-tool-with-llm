# DevOps Agent System Design

## 1. High-Level Architecture

| # | Description |
|---|-------------|
| 1 | **Supervisor Pattern** – 상위 Supervisor Agent 가 DevOps 전 과정을 오케스트레이션 |
| 2 | **Sub-Agents (React Agents)** – Grafana, k6, Loki, Tempo 등 각 도구별 전용 에이전트 |
| 3 | **LangGraph Subgraph** – Sub-Agents 간 의존 관계를 DAG 로 명시, 병렬/순차 실행 제어 |
| 4 | **Vector DB Knowledge Base** – DevOps 시나리오(목표·조건·도구·절차)를 저장 후 RAG 활용 |
| 5 | **LLM Planner** – Gemini-Pro 등 추론형 모델로 도구 호출 플래닝 |
| 6 | **LangGraph Pre-built Agents** – Planning / ToolExecutor / Guardrail … 최대한 재사용 |

---

## 2. Key Questions

> Q1. 이 설계가 타당한가요? 개선할 점이 있을까요? 다른 패턴이 있을까요?
>
> Q2. 활용할 만한 LangGraph pre-built agents 라이브러리는 무엇인가요? *(2025/05 기준)*
>
> Q3. Vector DB 에 저장할 DevOps 시나리오의 예시는?

---

## 3. 설계 평가 및 Q&A *(2025-05-06)*

### 3-1. 설계 평가 & 개선 포인트

**타당성 요약**

- **Supervisor + Sub-Agent 구조**: 병렬 DevOps 작업에 적합.
- **LangGraph Subgraph**: 빌드→테스트→배포→관측 흐름을 명시적 DAG 로 표현.
- **Vector DB + 시나리오 RAG**: Latent planning 패턴에 부합.

**개선 아이디어**

| 구분 | 제안 |
|------|------|
| 회로 차단 | Timeout·Retry·Circuit-breaker 미들웨어로 장애 전파 억제 |
| 메타-모니터링 | Supervisor 자체 메트릭/로그 → Grafana·Loki 전송 (Agent-of-Agents 시야) |
| Composite Agent | Loki+Tempo+Prometheus 등 연계 도구를 하나의 Composite Monitoring Agent 로 캡슐화 |
| 대안 패턴 | Kafka/Redis 이벤트 기반 Saga, 혹은 HTN+LLM 방식 고려 |

### 3-2. 2025/05 기준 LangGraph Pre-built Agents

| Agent | 주요 기능 |
|-------|-----------|
| **PlanningAgent (v0.9)** | 고수준 Plan 생성, GPT-4o·Gemini Pro 최적화 템플릿 내장 |
| **ToolExecutorAgent** | OpenAPI/JSONSchema → 함수호출 변환, Tool 실행 래퍼 |
| **VectorRecallAgent** | 벡터 DB 검색 + 응답 단일 스텝 |
| **SubGraphSupervisor** | 다중 Subgraph DAG 묶기, 재시도 전략 제공 |
| **GuardrailAgent** | 보안/정책 점검 후 DevOps 액션 승인·거부 |
| **SelfHealingAgent** | 실패 Run 분석 → Patch PR 작성 → 재실행 (β) |
| **ConversationMemoryAgent** | 휴먼-에이전트 대화 로그 요약·컨텍스트화 |
| **BenchmarkRunnerAgent** | k6·Locust·Vegeta 부하 테스트 래퍼 |

### 3-3. Vector DB 시나리오 스키마 & 예시

```json
{
  "id": "deploy-bluegreen-eks",
  "goal": "EKS 클러스터에 새 버전을 블루-그린 방식으로 배포한 뒤 정상성 확인 후 트래픽 전환",
  "conditions": [
    "서비스 무중단 유지",
    "CPU > 70% 또는 ErrorRate > 5% 발생 시 자동 롤백"
  ],
  "tools": ["kubectl", "PrometheusAPI", "GrafanaAPI", "Argo Rollouts"],
  "steps": [
    "새 Deployment green 버전 apply",
    "probes 통과 대기(최대 5분)",
    "Canary traffic 10% → 50% → 100% 전환",
    "Prometheus 메트릭 검사 (latency, error)",
    "문제 시 'argo rollback' 실행"
  ],
  "rollback": "기존 blue Deployment 로 traffic 100% 복귀"
}
```

추가 패턴: `scale-hpa-on-queue-depth`, `run-k6-smoke-test-after-deploy`, `backup-postgres-before-migration`, `patch-vulnerability-cve`, `rotate-secrets-vault` 등

---

## 4. Summary

- **장애 복원력·보안·관측성** 증대를 위해 회로 차단, Guardrail, 메타-모니터링 적용 권장.
- Pre-built Agents(Planning / ToolExecutor / Guardrail …) 를 적극 활용해 Supervisor 로직 단순화.
- Vector DB 에는 *목표-조건-도구-절차* 구조로 시나리오를 저장하여 유사도 기반 계획 효율 극대화.
