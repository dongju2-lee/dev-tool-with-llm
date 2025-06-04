// 점들 컨테이너 생성
function initDotsContainer() {
  dotsContainer = document.querySelector(".dots-container");
  if (!dotsContainer) {
    dotsContainer = document.createElement("div");
    dotsContainer.className = "dots-container idle";
    const voiceCircle = document.querySelector(".voice-circle");
    if (voiceCircle) {
      voiceCircle.appendChild(dotsContainer);
    }
  }
}

// 점들 생성 함수
function createDots(count = 150) {
  if (!dotsContainer) return;

  // 기존 점들 제거
  dotsContainer.innerHTML = "";
  dots = [];

  const containerSize = 300; // circle-container 크기에 맞춤
  const centerX = containerSize / 2;
  const centerY = containerSize / 2;

  for (let i = 0; i < count; i++) {
    const dot = document.createElement("div");
    dot.className = "dot";

    // 원형으로 배치하기 위한 계산
    const angle = (i / count) * Math.PI * 2;
    const radiusVariation = 0.6 + Math.random() * 0.35; // 60-95% 거리에 랜덤 배치
    const radius = (containerSize / 2 - 20) * radiusVariation; // 여백 고려

    const x = centerX + Math.cos(angle) * radius;
    const y = centerY + Math.sin(angle) * radius;

    dot.style.left = `${x}px`;
    dot.style.top = `${y}px`;

    // 점 크기 랜덤화
    const size = 3 + Math.random() * 2;
    dot.style.width = `${size}px`;
    dot.style.height = `${size}px`;

    // 원래 위치 저장
    dot.dataset.originalX = x;
    dot.dataset.originalY = y;
    dot.dataset.originalAngle = angle;
    dot.dataset.originalRadius = radius;

    dotsContainer.appendChild(dot);
    dots.push(dot);
  }
}

// 부드러운 상태 전환 함수
function smoothTransition(fromState, toState, callback) {
  // 이전 타이머 정리
  if (transitionTimeout) {
    clearTimeout(transitionTimeout);
  }

  // 전환 클래스 추가
  if (dotsContainer) {
    dotsContainer.className = `dots-container ${fromState}-to-${toState}`;
  }

  // 전환 완료 후 최종 상태 적용
  transitionTimeout = setTimeout(() => {
    if (callback) callback();
    if (dotsContainer) {
      dotsContainer.className = `dots-container ${toState}`;
    }
    currentState = toState;
  }, 1500); // 전환 시간
}

// 점들 상태 변경 함수들 (부드러운 전환 적용)
function setDotsIdle() {
  if (!currentState || currentState === "idle") {
    if (dotsContainer) {
      dotsContainer.className = "dots-container idle";
      currentState = "idle";
    }
    return;
  }

  console.log(`점들 상태 변경: ${currentState} → idle`);
  smoothTransition(currentState, "idle");
}

function setDotsSpeaking() {
  if (!currentState || currentState === "speaking") {
    if (dotsContainer) {
      dotsContainer.className = "dots-container speaking";
      currentState = "speaking";
    }
    return;
  }

  console.log(`점들 상태 변경: ${currentState} → speaking`);
  smoothTransition(currentState, "speaking");
}

function setDotsProcessing() {
  if (!currentState || currentState === "processing") {
    if (dotsContainer) {
      dotsContainer.className = "dots-container processing";
      currentState = "processing";
    }
    return;
  }

  console.log(`점들 상태 변경: ${currentState} → processing`);
  smoothTransition(currentState, "processing");
}

function setDotsTTSPlaying() {
  if (!currentState || currentState === "tts-playing") {
    if (dotsContainer) {
      dotsContainer.className = "dots-container tts-playing";
      currentState = "tts-playing";
    }
    return;
  }

  console.log(`점들 상태 변경: ${currentState} → tts-playing`);
  smoothTransition(currentState, "tts-playing");
}

// TTS 애니메이션 시작
function startWaveAnimation() {
  setDotsTTSPlaying();
  console.log("TTS 점들 애니메이션이 시작되었습니다.");
}

// TTS 애니메이션 중지
function stopWaveAnimation() {
  setDotsIdle();
  console.log("TTS 점들 애니메이션이 중지되었습니다.");
} 