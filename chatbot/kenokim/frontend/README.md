# Grafana AI Assistant Frontend

Grafana 모니터링 시스템을 위한 AI 어시스턴트 프론트엔드 애플리케이션입니다.

## 기능

- 📊 **Grafana 대시보드 데이터 조회**: 대시보드 데이터를 실시간으로 조회하고 분석
- 📈 **시스템 메트릭 분석**: CPU, 메모리, 네트워크 등 시스템 성능 메트릭 모니터링
- 🖼️ **대시보드 시각화**: 차트 생성 및 대시보드 렌더링
- ⚙️ **알람 및 설정 관리**: 모니터링 알람 설정 및 대시보드 관리
- 💬 **실시간 채팅**: 일반 채팅 및 스트리밍 응답 지원
- 🗂️ **세션 관리**: 채팅 히스토리 저장 및 세션 관리

## 기술 스택

- **React 19.1.0** - UI 프레임워크
- **TypeScript** - 타입 안정성
- **Axios** - HTTP 클라이언트
- **CSS3** - 모던 스타일링

## 백엔드 API 연동

이 프론트엔드는 다음 백엔드 API 엔드포인트와 통신합니다:

- `POST /api/v1/chat` - 일반 채팅
- `POST /api/v1/chat/stream` - 스트리밍 채팅
- `POST /api/v1/sessions` - 세션 생성
- `DELETE /api/v1/sessions/{session_id}` - 세션 삭제
- `GET /api/v1/health` - 헬스체크

## 설치 및 실행

### 1. 의존성 설치
```bash
npm install
```

### 2. 환경 설정
`src/config/environment.ts`에서 백엔드 API URL을 확인하세요:
```typescript
const config: Config = {
  development: {
    API_BASE_URL: 'http://localhost:8000'
  },
  production: {
    API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'https://your-api-domain.com'
  }
};
```

### 3. 개발 서버 실행
```bash
npm start
```

애플리케이션이 http://localhost:3000에서 실행됩니다.

### 4. 빌드
```bash
npm run build
```

## 사용법

1. **백엔드 서버 실행**: 먼저 백엔드 서버(`http://localhost:8000`)가 실행 중인지 확인하세요.

2. **새 세션 시작**: "새 세션" 버튼을 클릭하여 새로운 채팅 세션을 시작할 수 있습니다.

3. **메시지 전송**: 
   - 일반 전송: "전송" 버튼 클릭
   - 스트리밍: "스트림" 버튼 클릭 (실시간 응답)

4. **예시 질문**:
   - "CPU 사용률을 확인해줘"
   - "메모리 사용량 차트를 만들어줘"
   - "대시보드를 렌더링해줘"
   - "시스템 성능을 분석해줘"

## 주요 컴포넌트

- **App.tsx**: 메인 애플리케이션 컴포넌트
- **ChatInterface.tsx**: 채팅 인터페이스 컴포넌트
- **Sidebar.tsx**: 사이드바 및 채팅 히스토리
- **services/langserveClient.ts**: API 클라이언트

## 개발

### 프로젝트 구조
```
src/
├── components/          # React 컴포넌트
│   ├── ChatInterface.tsx
│   ├── Sidebar.tsx
│   └── *.css
├── services/           # API 서비스
│   └── langserveClient.ts
├── types/             # TypeScript 타입 정의
│   └── index.ts
├── config/            # 환경 설정
│   └── environment.ts
└── App.tsx            # 메인 애플리케이션
```

### 개발 가이드라인

1. **타입 안정성**: 모든 API 응답과 상태에 대해 TypeScript 타입을 정의합니다.
2. **에러 핸들링**: API 호출 시 적절한 에러 메시지를 사용자에게 표시합니다.
3. **반응형 디자인**: 모바일 및 태블릿 화면에서도 올바르게 동작합니다.
4. **접근성**: 키보드 내비게이션 및 스크린 리더를 고려합니다.

## 연결 상태

애플리케이션 헤더에서 백엔드 서버와의 연결 상태를 확인할 수 있습니다:
- 🟢 **Connected**: 백엔드 서버와 정상 연결
- 🔴 **Disconnected**: 연결 실패 (백엔드 서버 확인 필요)

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
