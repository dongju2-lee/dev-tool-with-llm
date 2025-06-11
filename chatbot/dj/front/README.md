# 음성 챗봇 프론트엔드

Google Cloud Speech-to-Text와 Text-to-Speech API를 활용한 실시간 음성 채팅 인터페이스입니다.

## 📁 파일 구조

```
front/
├── assets/
│   ├── css/                    # 스타일시트 파일들
│   │   ├── base.css           # 기본 레이아웃 및 컨테이너 스타일
│   │   ├── animations.css     # 모든 애니메이션 정의
│   │   ├── dots.css          # 점들 관련 스타일과 상태별 애니메이션
│   │   ├── button.css        # 마이크 버튼 스타일
│   │   └── effects.css       # 배경 시스템 효과
│   └── js/                    # JavaScript 파일들
│       ├── config.js         # 설정값과 상수 정의
│       ├── audio-manager.js  # 오디오 녹음/재생 관리
│       ├── dots-manager.js   # 점들 생성과 상태 관리
│       ├── api-client.js     # 서버 통신 관리
│       ├── ui-controller.js  # UI 상태 관리와 이벤트 처리
│       └── voice-chatbot.js  # 메인 음성 챗봇 클래스
├── page_list/
│   └── voice_chatbot_page.py # Streamlit 페이지 구현
├── ENV_CONFIG.md             # 환경변수 설정 가이드
└── README.md                 # 이 파일
```

## 🎯 주요 기능

### 🎤 음성 인식 (STT)
- Google Cloud Speech-to-Text API 사용
- 실시간 음성 감지 및 자동 녹음 중지
- 한국어 음성 인식 지원
- WAV 형식 오디오 처리

### 🤖 챗봇 연동
- 외부 챗봇 서버와 REST API 통신
- 다양한 에이전트 모드 지원
- 세션 관리 기능

### 🔊 음성 합성 (TTS)
- Google Cloud Text-to-Speech API 사용
- 고품질 한국어 음성 (Chirp3-HD)
- 기본 음성으로 자동 폴백

### 🎨 시각적 피드백
- 상태별 점들 애니메이션 (대기, 듣기, 처리중, 재생중)
- 부드러운 상태 전환 효과
- 호흡 애니메이션
- 색상 기반 상태 표시

## 🏗️ 아키텍처

### 모듈 구조
```
VoiceChatbot (메인 클래스)
├── AudioManager      # 오디오 녹음/재생
├── DotsManager       # 시각적 피드백
├── ApiClient         # 서버 통신
└── UIController      # UI 상태 관리
```

### 데이터 흐름
```
1. 사용자 음성 입력
   ↓
2. AudioManager → 녹음 및 WAV 변환
   ↓
3. ApiClient → STT 서버 전송
   ↓
4. ApiClient → 챗봇 서버 전송
   ↓
5. ApiClient → TTS 서버 전송
   ↓
6. AudioManager → 오디오 재생
```

## ⚙️ 설정

모든 설정은 `assets/js/config.js` 파일에서 관리됩니다.

### 주요 설정 항목
- **서버 URL**: STT, TTS, 챗봇 서버 주소
- **오디오 설정**: 샘플링 레이트, 채널, 음성 감지 임계값
- **시각화 설정**: 점 개수, 크기, 색상, 애니메이션 속도
- **디버그 설정**: 로그 레벨, API 응답 로깅

자세한 설정 방법은 [ENV_CONFIG.md](ENV_CONFIG.md)를 참조하세요.

## 🚀 사용법

### 1. 서버 준비
```bash
# STT/TTS 서버 시작 (포트 8504)
cd voice-back
python voice_server.py

# 챗봇 서버 시작 (포트 8800)
cd chatbot-server
python app.py
```

### 2. Streamlit 앱 실행
```bash
cd front
streamlit run main.py
```

### 3. 음성 채팅 사용
1. 마이크 버튼 클릭
2. 음성 입력 (자동으로 녹음 중지)
3. STT → 챗봇 → TTS 처리 대기
4. 응답 음성 재생

## 🎨 상태별 시각적 피드백

| 상태 | 색상 | 애니메이션 | 설명 |
|------|------|------------|------|
| **IDLE** | 파란색 (#4A90E2) | 호흡 애니메이션 | 대기 상태 |
| **LISTENING** | 청록색 (#50E3C2) | 확장 애니메이션 | 음성 입력 중 |
| **PROCESSING** | 주황색 (#F5A623) | 회전 애니메이션 | 처리 중 |
| **TTS_PLAYING** | 보라색 (#BD10E0) | 파도 애니메이션 | 음성 재생 중 |

## 🔧 개발 가이드

### 새로운 기능 추가
1. 해당 모듈 클래스에 메서드 추가
2. `config.js`에 필요한 설정 추가
3. 상태가 필요하면 `STATES`에 추가
4. CSS 애니메이션이 필요하면 해당 CSS 파일에 추가

### 디버깅
브라우저 개발자 도구 콘솔에서:
```javascript
// 현재 설정 확인
console.log(CONFIG);

// 음성 챗봇 인스턴스 접근
console.log(voiceChatbot);
```

### 스타일 수정
- `base.css`: 기본 레이아웃
- `animations.css`: 애니메이션 효과
- `dots.css`: 점들 스타일
- `button.css`: 버튼 스타일
- `effects.css`: 배경 효과

## 🐛 문제 해결

### 일반적인 문제
1. **마이크 권한 오류**: 브라우저에서 마이크 권한 허용
2. **서버 연결 오류**: 서버 URL과 포트 확인
3. **음성 인식 실패**: 마이크 입력 레벨 확인
4. **TTS 재생 안됨**: 브라우저 오디오 정책 확인

### 로그 확인
```javascript
// 디버그 모드 활성화
CONFIG.DEBUG.ENABLED = true;
CONFIG.DEBUG.LOG_API_RESPONSES = true;
```

## 📝 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 