// 캔버스 초기화
function clearCanvas() {
  const canvas = document.getElementById("audioCanvas");
  if (!canvas) return;
  
  const canvasContext = canvas.getContext("2d");
  if (canvas.width === 0 || canvas.height === 0) {
    const container = canvas.parentElement;
    canvas.width = container.offsetWidth;
    canvas.height = container.offsetHeight;
  }
  canvasContext.clearRect(0, 0, canvas.width, canvas.height);
}

// 호흡 효과 애니메이션 시작
function startBreathing() {
  const circleContainer = document.getElementById("circleContainer");
  if (!circleContainer) return;

  function updateBreath() {
    if (!isRecording && !isSpeaking && !isProcessing) {
      breathScale += breathDirection;
      if (breathScale > 1.02) {
        breathDirection = -0.0005;
      } else if (breathScale < 1.0) {
        breathDirection = 0.0005;
      }
      circleContainer.style.transform = `scale(${breathScale})`;
    }
    requestAnimationFrame(updateBreath);
  }
  updateBreath();
}

// 마이크 버튼 상태 업데이트
function updateMicButtonState() {
  const micButton = document.getElementById("micButton");
  if (!micButton) return;

  if (isProcessing) {
    micButton.classList.add("processing");
    micButton.classList.remove("active");
    micButton.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12,6 12,12 16,14"></polyline>
      </svg>
    `;
  } else if (isRecording) {
    micButton.classList.remove("processing");
    micButton.classList.add("active");
    micButton.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="23"></line>
        <line x1="8" y1="23" x2="16" y2="23"></line>
      </svg>
    `;
  } else {
    micButton.classList.remove("processing", "active", "muted");
    micButton.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="23"></line>
        <line x1="8" y1="23" x2="16" y2="23"></line>
      </svg>
    `;
  }
}

// 녹음 시작 함수
function startRecording() {
  if (!mediaRecorder || isProcessing) {
    console.error("MediaRecorder가 초기화되지 않았거나 처리 중입니다.");
    return false;
  }

  if (isRecording) {
    console.log("이미 녹음 중입니다.");
    return false;
  }

  try {
    audioChunks = [];
    isRecording = true;
    recordingStartTime = Date.now();

    mediaRecorder.start();
    console.log("녹음이 시작되었습니다.");

    updateMicButtonState();
    const circleContainer = document.getElementById("circleContainer");
    if (circleContainer) {
      circleContainer.classList.remove("idle");
    }

    setDotsIdle(); // 점들을 평상시 상태로 설정

    visualizationActive = true;
    visualize();

    notifyStreamlit({ isRecording: true });

    return true;
  } catch (error) {
    console.error("녹음 시작 오류:", error);
    resetRecording();
    return false;
  }
}

// 녹음 중지 함수
function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") {
    console.log("녹음이 활성화되지 않았습니다.");
    resetRecording();
    return false;
  }

  const recordingDuration = Date.now() - recordingStartTime;
  if (recordingDuration < MIN_RECORDING_TIME) {
    console.log("녹음 시간이 너무 짧습니다. 무시합니다.");
    resetRecording();
    return false;
  }

  clearTimeout(silenceTimer);
  silenceTimer = null;

  try {
    mediaRecorder.stop();
    isRecording = false;
    isSpeaking = false;

    visualizationActive = false;
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }

    updateMicButtonState();
    const circleContainer = document.getElementById("circleContainer");
    if (circleContainer) {
      circleContainer.classList.add("idle");
      circleContainer.classList.remove("active");
    }

    notifyStreamlit({ isRecording: false });

    console.log("녹음이 중지되었습니다.");
    return true;
  } catch (error) {
    console.error("녹음 중지 오류:", error);
    resetRecording();
    return false;
  }
}

// 녹음 상태 초기화
function resetRecording() {
  audioChunks = [];
  isRecording = false;
  isSpeaking = false;

  visualizationActive = false;
  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }

  clearCanvas();
  updateMicButtonState();
  const circleContainer = document.getElementById("circleContainer");
  if (circleContainer) {
    circleContainer.classList.add("idle");
  }

  setDotsIdle(); // 점들을 평상시 상태로 변경

  notifyStreamlit({ isRecording: false });
}

// Streamlit에 상태 알림
function notifyStreamlit(data) {
  if (window.parent && window.parent.postMessage) {
    window.parent.postMessage(
      {
        type: "streamlit:setComponentValue",
        value: data,
      },
      "*"
    );
  }
} 