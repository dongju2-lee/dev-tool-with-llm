// 글로벌 변수 정의
let audioContext;
let analyser;
let microphone;
let isRecording = false;
let isSpeaking = false;
let animationId;
let speechTimer = null;
let voiceLevelHistory = Array(10).fill(0);
let breathScale = 1.0;
let breathDirection = 0.0005;

// 녹음 관련 변수
let mediaRecorder = null;
let audioChunks = [];
let silenceTimer = null;
let lastAudioLevel = 0;
const SILENCE_THRESHOLD = 20;
const SILENCE_DURATION = 2000;
const MIN_RECORDING_TIME = 1000;
let recordingStartTime = 0;
let visualizationActive = false;

// 서버 URL 설정
const hostname = "localhost";
const VOICE_SERVER_HOST = `http://${hostname}:8504`;
const AGENT_SERVER_HOST = `http://${hostname}:8800`;

// 현재 처리 상태
let isProcessing = false;

// 점들 관련 변수
let dotsContainer = null;
let dots = [];
let currentState = "idle"; // 현재 상태 추적
let transitionTimeout = null; // 전환 타이머 