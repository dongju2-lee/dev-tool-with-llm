# DevOps Tool with LLM (개발 도구 LLM)

DevOps Tool with LLM은 DevOps 개발자들이 일상적인 작업을 보다 효율적으로 수행할 수 있도록 도와주는 LLM 기반 챗봇 솔루션입니다. 다양한 DevOps 도구들과 통합되어 작업 자동화, 문제 해결, 모니터링 등의 기능을 제공합니다.

## 🚀 주요 기능

- **통합 모니터링**: Grafana, Loki, Tempo를 통한 통합 모니터링 솔루션
- **Git 작업 관리**: GitHub 작업 자동화 및 관리
- **Slack 통합**: Slack을 통한 알림 및 상호작용
- **쿠버네티스 관리**: K8s 클러스터 관리 및 문제 해결 지원
- **CI/CD 파이프라인**: ArgoCD를 활용한 GitOps 기반 배포 자동화
- **성능 테스트**: K6를 통한 API 및 서비스 성능 테스트

## 🏗️ 아키텍처

이 프로젝트는 다음 세 가지 주요 컴포넌트로 구성됩니다:

1. **MCP (Model Context Protocol)**: 다양한 DevOps 도구들과 통합되는 중앙 관리 서버
2. **API 서버**: MCP서버와 통신을 하는 API 서버
3. **챗봇**: LLM 기반 사용자 인터페이스로, 개발자의 질문과 명령을 처리, streamlit을 사용하며 랭그래프를 이용하여 대화

## 📂 디렉토리 구조

```
dev-tool-with-llm/
│
├── api-server/              # API 서버 컴포넌트
│   ├── slack/               # Slack 통합 API
│   ├── github/              # GitHub 통합 API
│   ├── tempo/               # Tempo 통합 (분산 추적)
│   ├── loki/                # Loki 통합 (로그 관리)
│   ├── grafana/             # Grafana 통합 (시각화)
│   ├── argocd/              # ArgoCD 통합 (배포 관리)
│   └── k6/                  # K6 통합 (성능 테스트)
│
├── chatbot/                 # LLM 기반 챗봇 인터페이스
│   └── dj/                  # 챗봇 프로젝트 디렉토리
│
└── mcp/                     # Management Control Plane
    ├── slack/               # Slack 통합 서비스
    ├── github/              # GitHub 통합 서비스
    ├── k8s/                 # 쿠버네티스 관리 기능
    ├── tempo/               # Tempo 통합 (분산 추적)
    ├── loki/                # Loki 통합 (로그 관리)
    ├── grafana/             # Grafana 통합 (시각화)
    ├── argocd/              # ArgoCD 통합 (배포 관리)
    └── k6/                  # K6 통합 (성능 테스트)
```

## 🛠️ 지원하는 도구

- **Slack**: 채팅 기반 알림 및 명령 실행
- **GitHub**: 저장소 관리, PR 검토, 이슈 트래킹
- **Kubernetes**: 클러스터 상태 확인 및 문제 해결
- **ArgoCD**: GitOps 배포 관리
- **Grafana/Loki/Tempo**: 모니터링 및 로깅
- **K6**: 성능 테스트 및 보고서 생성

## 🚦 시작하기

(개발 진행 중입니다. 향후 설치 및 설정 가이드가 추가될 예정입니다.)

## 📖 사용 예시

```
사용자: "프로덕션 환경에서 최근 5개의 실패한 배포를 보여줘"
챗봇: "다음은 최근 실패한 5개의 배포입니다: ..."

사용자: "현재 CPU 사용량이 높은 상위 3개의 파드를 찾아줘"
챗봇: "현재 CPU 사용량이 높은 파드는 다음과 같습니다: ..."

사용자: "지난 24시간 동안의 API 응답 시간 그래프를 Slack에 공유해줘"
챗봇: "그래프를 생성하여 Slack 채널에 공유했습니다."
```

## 🧩 확장성

추가 도구 및 서비스를 쉽게 통합할 수 있는 플러그인 아키텍처를 제공합니다. 자체 통합을 개발하여 필요에 맞게 확장할 수 있습니다.

## 📄 라이선스

MIT


