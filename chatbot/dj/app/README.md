# 다중 에이전트 기반 개발 도구 챗봇

이 프로젝트는 LangGraph v0.3.x와 LangChain v0.3.x를 사용하여 구현된 다중 에이전트 아키텍처 기반 개발 도구 챗봇입니다.

## 주요 기능

- **다중 에이전트 아키텍처**: 각 에이전트가 특정 역할을 담당하여 복잡한 쿼리 처리
- **오케스트레이션**: 중앙 오케스트레이터가 에이전트 간의 상호작용 관리
- **계획 및 실행**: 사용자 요청을 분석하여 단계별 계획 수립 및 실행
- **검증 및 응답 생성**: 생성된 결과의 검증 및 일관된 응답 제공

## 아키텍처 개요

시스템은 다음과 같은 주요 구성 요소로 이루어져 있습니다:

1. **슈퍼바이저 에이전트**: 최초 사용자 요청을 분석하고 적절한 에이전트로 라우팅
2. **오케스트레이터 에이전트**: 전체 워크플로우를 관리하고 에이전트 간의 조정 담당
3. **계획 에이전트**: 복잡한 작업을 더 작은 단계로 분할하여 계획 수립
4. **날씨 에이전트**: 위치 기반 날씨 정보 조회 및 제공
5. **검증 에이전트**: 생성된 결과의 정확성, 완전성, 품질 검증
6. **응답 에이전트**: 최종 사용자 응답 생성 및 형식화

## 디렉토리 구조

```
app/
  ├── agent/                  # 에이전트 모듈
  │   ├── supervisor_agent.py # 슈퍼바이저 에이전트
  │   ├── orchestrator_agent.py # 오케스트레이터 에이전트
  │   ├── planning_agent.py   # 계획 에이전트
  │   ├── weather_agent.py    # 날씨 에이전트
  │   ├── validation_agent.py # 검증 에이전트
  │   └── respond_agent.py    # 응답 에이전트
  ├── graph/                  # 그래프 모듈
  │   └── dev_tool_graph.py   # 에이전트 그래프 정의
  ├── state/                  # 상태 관리 모듈
  │   └── base_state.py       # 기본 상태 클래스 및 열거형
  ├── utils/                  # 유틸리티 모듈
  │   └── logger_config.py    # 로깅 구성
  ├── app.py                  # FastAPI 애플리케이션
  ├── config.py               # 구성 설정
  └── requirements.txt        # 종속성 정의
```

## 설치 및 실행

### 사전 요구 사항

- Python 3.10 이상
- pip (Python 패키지 관리자)

### 설치

1. 저장소 복제:
   ```bash
   git clone https://github.com/yourusername/dev-tool-chatbot.git
   cd dev-tool-chatbot
   ```

2. 가상 환경 생성 및 활성화:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. 종속성 설치:
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정:
   `.env` 파일을 생성하고 다음 값을 설정합니다:
   ```
   LOG_LEVEL=INFO
   WEATHER_API_KEY=your_api_key
   GOOGLE_API_KEY=your_google_api_key
   GOOGLE_PROJECT_ID=your_project_id
   PORT=8000
   ```

### 실행

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

서버가 시작되면 `http://localhost:8000`에서 API에 액세스할 수 있습니다.

## API 엔드포인트

- `GET /`: 서비스 상태 확인
- `GET /status`: 서비스 상세 상태 정보
- `POST /chat`: 챗봇과 메시지 교환
- `POST /reset`: 대화 상태 재설정

### 샘플 요청 (chat 엔드포인트)

```json
{
  "message": "서울의 오늘 날씨가 어때?",
  "conversation_id": "optional_conversation_id"
}
```

### 샘플 응답

```json
{
  "conversation_id": "conv_1234567890",
  "messages": [
    {
      "role": "assistant",
      "content": "서울의
 현재 날씨는 맑고 기온은 22°C입니다. 오늘은 대체로 맑은 날씨가 이어질 전망이며, 최고 기온은 25°C, 최저 기온은 18°C로 예상됩니다. 습도는 65%이며, 바람은 3.2m/s로 약하게 불고 있습니다. 오늘 야외 활동하기 좋은 날씨입니다."
    }
  ],
  "created_at": 1682500000.0
}
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요. 