// 메인 초기화
document.addEventListener("DOMContentLoaded", function () {
  const micButton = document.getElementById("micButton");
  const circleContainer = document.getElementById("circleContainer");
  const canvas = document.getElementById("audioCanvas");
  const waveContainer = document.getElementById("waveContainer");

  if (!micButton || !circleContainer || !canvas) {
    console.error("필수 UI 요소를 찾을 수 없습니다.");
    return;
  }

  // 마이크 버튼 클릭 처리
  micButton.addEventListener("click", async function () {
    if (micButton.disabled || isProcessing) return;
    micButton.disabled = true;

    try {
      if (isRecording) {
        console.log("녹음 중지 시작");
        stopRecording();
      } else {
        console.log("녹음 시작 시도");

        if (!audioContext || !mediaRecorder) {
          console.log("마이크 재초기화 필요");
          const success = await setupMicrophone();
          if (!success) {
            console.error("마이크 초기화 실패");
            return;
          }
        }

        startRecording();
        console.log("녹음 시작 완료");
      }
    } catch (error) {
      console.error("마이크 버튼 처리 중 오류:", error);
      resetRecording();
    } finally {
      setTimeout(() => {
        micButton.disabled = false;
      }, 300);
    }
  });

  // Agent Mode 초기화
  resetAgentMode();
  
  initDotsContainer();
  createDots(400); // 점 생성
  setDotsIdle(); // 평상시 상태로 설정
  startBreathing(); // 호흡 애니메이션 시작
  setupMicrophone(); // 마이크 초기화
  
  // SSE 연결 초기화
  console.log("SSE 클라이언트 연결 시작...");
  connectSSE();
}); 