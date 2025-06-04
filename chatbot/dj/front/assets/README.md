# 음성 챗봇 Assets 구조

이 디렉토리는 음성 챗봇의 프론트엔드 자산들을 모듈화하여 관리합니다.

## 📁 파일 구조

### CSS 파일들 (`/css/`)

- **`base.css`** - 기본 레이아웃과 컨테이너 스타일
- **`animations.css`** - 모든 애니메이션과 키프레임 정의
- **`dots.css`** - 점들 관련 스타일과 상태별 애니메이션
- **`button.css`** - 마이크 버튼 스타일
- **`effects.css`** - 배경 효과와 기타 시각적 효과

### JavaScript 파일들 (`/js/`)

- **`config.js`** - ⚠️ **더 이상 사용되지 않음** (환경변수로 대체)
- **`audio-manager.js`** - 오디오 관련 기능 (녹음, 재생, 변환)
- **`dots-manager.js`** - 점들 생성과 상태 관리
- **`api-client.js`** - 서버 통신 관련 기능 (스트리밍 TTS 포함)
- **`ui-controller.js`** - UI 상태 관리와 이벤트 처리
- **`voice-chatbot.js`** - 메인 초기화 및 통합

## ⚙️ 환경변수 기반 설정 시스템

### 🔧 설정 방법

1. **프로젝트 루트에 `.env` 파일 생성**
2. **`ENV_CONFIG.md` 파일의 설정 내용 복사**
3. **필요에 따라 설정값 수정**
4. **서버 재시작**

### 📋 주요 환경변수

```bash
# 서버 URL 설정
STT_SERVER_URL=http://localhost:8504
TTS_SERVER_URL=http://localhost:8504
CHATBOT_SERVER_URL=http://localhost:8800

# 스트리밍 TTS 모드 설정
TTS_USE_STREAMING=true
TTS_USE_WEBSOCKET=false
TTS_DEFAULT_VOICE=ko-KR-Chirp3-HD-Achernar

# 오디오 설정
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1

# 시각화 설정
VIZ_DOTS_COUNT=400
VIZ_COLOR_IDLE=#4A90E2

# 디버그 설정
DEBUG_ENABLED=true
```

### 🎵 TTS 모드 변경

환경변수로 쉽게 TTS 모드를 변경할 수 있습니다:

- **일반 TTS**: `TTS_USE_STREAMING=false`
- **HTTP 스트리밍**: `TTS_USE_STREAMING=true`, `TTS_USE_WEBSOCKET=false`
- **WebSocket 스트리밍**: `TTS_USE_STREAMING=true`, `TTS_USE_WEBSOCKET=true`

## 🔧 모듈 설명

### 1. 환경변수 기반 CONFIG
```javascript
// CONFIG 객체는 voice_chatbot_page.py에서 환경변수를 읽어서 동적으로 생성됩니다
const CONFIG = {
    STT_SERVER_URL: "http://localhost:8504",
    TTS_MODE: {
        USE_STREAMING: true,
        USE_WEBSOCKET: false,
        // ...
    }
    // ...
};
```

### 2. AudioManager (audio-manager.js)
```javascript
// CONFIG에서 오디오 설정을 자동으로 로드
class AudioManager {
    constructor() {
        this.sampleRate = CONFIG.AUDIO.SAMPLE_RATE;
        this.channels = CONFIG.AUDIO.CHANNELS;
        // ...
    }
}
```

### 3. DotsManager (dots-manager.js)
```javascript
// 점들의 생성, 배치, 상태 전환 관리
class DotsManager {
    createDots(count) { /* ... */ }
    setIdle() { /* ... */ }
    setSpeaking() { /* ... */ }
    // ...
}
```

### 4. ApiClient (api-client.js)
```javascript
// STT, TTS, 챗봇 서버와의 통신 (스트리밍 TTS 지원)
class ApiClient {
    async sendAudioToSTTServer(audioBase64) { /* ... */ }
    async sendTextToStreamingTTSServer(text) { /* ... */ }
    connectStreamingTTSWebSocket() { /* ... */ }
    // ...
}
```

### 5. UIController (ui-controller.js)
```javascript
// UI 상태 관리, 이벤트 처리, 시각화
class UIController {
    updateMicButtonState() { /* ... */ }
    startRecording() { /* ... */ }
    visualize() { /* ... */ }
    // ...
}
```

### 6. VoiceChatbot (voice-chatbot.js)
```javascript
// 메인 클래스 - 환경변수 설정을 자동으로 로드하여 모든 모듈을 통합 관리
class VoiceChatbot {
    constructor() {
        // CONFIG에서 스트리밍 TTS 설정 자동 로드
        this.useStreamingTTS = CONFIG.TTS_MODE.USE_STREAMING;
        this.useWebSocketStreaming = CONFIG.TTS_MODE.USE_WEBSOCKET;
        // ...
    }
}
```

## 🎨 CSS 모듈 설명

### 1. Base (base.css)
- 기본 body, container 스타일
- 레이아웃 구조
- 기본 요소 배치

### 2. Animations (animations.css)
- 모든 @keyframes 정의
- 호흡 효과, 펄스, 회전 등
- 상태 전환 애니메이션

### 3. Dots (dots.css)
- 점들의 기본 스타일
- 상태별 애니메이션 (idle, speaking, processing, tts-playing)
- 부드러운 전환 효과

### 4. Button (button.css)
- 마이크 버튼 스타일
- 호버, 활성, 처리 중 상태
- 그라데이션과 그림자 효과

### 5. Effects (effects.css)
- 배경 효과
- 환경 애니메이션
- 기타 시각적 효과

## 🚀 사용법

### 개발 시
환경변수로 설정을 쉽게 변경할 수 있습니다:

```bash
# .env 파일에서 설정 변경
TTS_USE_STREAMING=true
DEBUG_ENABLED=false
VIZ_DOTS_COUNT=200
```

### 런타임 설정 변경
브라우저 콘솔에서 실시간으로 TTS 모드를 변경할 수 있습니다:

```javascript
// 일반 TTS로 변경
setTTSMode.regular()

// HTTP 스트리밍으로 변경
setTTSMode.httpStreaming()

// WebSocket 스트리밍으로 변경
setTTSMode.websocketStreaming()

// 현재 설정 확인
setTTSMode.showConfig()
```

### 확장 시
새로운 기능을 추가할 때:

1. 환경변수 추가 (`.env` 파일)
2. `voice_chatbot_page.py`의 `get_env_config()` 함수에 설정 추가
3. 해당 모듈에서 CONFIG 객체 사용

## 🔄 의존성 관계

```
voice-chatbot.js (메인)
├── 환경변수 CONFIG (동적 생성)
├── audio-manager.js (오디오)
├── dots-manager.js (점들)
├── api-client.js (API + 스트리밍 TTS)
└── ui-controller.js (UI)
    ├── audio-manager.js
    ├── dots-manager.js
    └── api-client.js
```

## 📝 유지보수 가이드

### 새로운 설정 추가
1. `.env` 파일에 환경변수 추가
2. `voice_chatbot_page.py`의 `get_env_config()` 함수에 설정 추가
3. 관련 모듈에서 `CONFIG` 객체 사용

### 새로운 상태 추가
1. 환경변수로 상태 정의
2. `dots.css`에 해당 상태 스타일 추가
3. `dots-manager.js`에 상태 변경 메서드 추가

### 새로운 애니메이션 추가
1. `animations.css`에 키프레임 정의
2. 해당 모듈의 CSS 파일에 애니메이션 적용

### 스트리밍 TTS 설정 변경
환경변수로 쉽게 변경 가능:
```bash
# HTTP 스트리밍 사용
TTS_USE_STREAMING=true
TTS_USE_WEBSOCKET=false

# WebSocket 스트리밍 사용  
TTS_USE_STREAMING=true
TTS_USE_WEBSOCKET=true

# 일반 TTS 사용
TTS_USE_STREAMING=false
```

## 🎉 새로운 기능

### Google Cloud TTS 스트리밍 지원
- **HTTP 스트리밍**: 텍스트를 청크로 나누어 지연시간 단축
- **WebSocket 스트리밍**: 실시간 양방향 스트리밍으로 최저 지연시간
- **자동 폴백**: 스트리밍 실패 시 일반 TTS로 자동 전환

### 환경변수 기반 설정
- **유연한 설정 관리**: 환경별로 다른 설정 사용 가능
- **런타임 변경**: 브라우저 콘솔에서 실시간 설정 변경
- **타입 안전성**: Python에서 타입 변환 후 JavaScript로 전달

이 구조를 통해 코드의 가독성, 유지보수성, 확장성이 크게 향상되었으며, 환경변수를 통한 유연한 설정 관리가 가능해졌습니다.