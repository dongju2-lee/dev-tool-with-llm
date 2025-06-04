// WAV 헤더 생성 함수
function createWavHeader(audioBuffer) {
  const length = audioBuffer.length;
  const sampleRate = audioBuffer.sampleRate;
  const numberOfChannels = audioBuffer.numberOfChannels;

  const arrayBuffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(arrayBuffer);

  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numberOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, length * 2, true);

  const channelData = audioBuffer.getChannelData(0);
  let offset = 44;
  for (let i = 0; i < length; i++) {
    const sample = Math.max(-1, Math.min(1, channelData[i]));
    view.setInt16(
      offset,
      sample < 0 ? sample * 0x8000 : sample * 0x7fff,
      true
    );
    offset += 2;
  }

  return new Blob([arrayBuffer], { type: "audio/wav" });
}

// WebM/OGG를 WAV로 변환하는 함수
async function convertToWav(blob) {
  return new Promise((resolve, reject) => {
    const audioContext = new (window.AudioContext ||
      window.webkitAudioContext)();
    const fileReader = new FileReader();

    fileReader.onload = function (e) {
      audioContext
        .decodeAudioData(e.target.result)
        .then((audioBuffer) => {
          const wavBlob = createWavHeader(audioBuffer);
          resolve(wavBlob);
        })
        .catch(reject);
    };

    fileReader.onerror = reject;
    fileReader.readAsArrayBuffer(blob);
  });
}

// Base64 오디오 재생
function playAudioFromBase64(audioBase64) {
  try {
    const byteCharacters = atob(audioBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const audioBlob = new Blob([byteArray], { type: "audio/wav" });

    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.onplay = () => {
      console.log("TTS 오디오 재생 시작");
      startWaveAnimation();
    };

    audio.onended = () => {
      console.log("TTS 오디오 재생 완료");
      // 부드러운 전환으로 idle 상태로 복귀
      setTimeout(() => {
        stopWaveAnimation();
        isProcessing = false;
        updateMicButtonState();
      }, 300);
      URL.revokeObjectURL(audioUrl);
    };

    audio.onerror = (error) => {
      console.error("오디오 재생 오류:", error);
      stopWaveAnimation();
      URL.revokeObjectURL(audioUrl);
      isProcessing = false;
      updateMicButtonState();
    };

    audio.play();
  } catch (error) {
    console.error("오디오 재생 처리 오류:", error);
    isProcessing = false;
    updateMicButtonState();
  }
}

// Blob을 Base64로 변환하는 헬퍼 함수
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64Data = reader.result.split(",")[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// 마이크 초기화 함수
async function setupMicrophone() {
  try {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    microphone = audioContext.createMediaStreamSource(stream);
    microphone.connect(analyser);

    const options = {};

    if (MediaRecorder.isTypeSupported("audio/wav")) {
      options.mimeType = "audio/wav";
    } else if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
      options.mimeType = "audio/webm;codecs=opus";
    } else if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
      options.mimeType = "audio/ogg;codecs=opus";
    }

    console.log("사용할 MIME 타입:", options.mimeType || "기본값");
    mediaRecorder = new MediaRecorder(stream, options);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      const mimeType = mediaRecorder.mimeType || "audio/wav";
      const audioBlob = new Blob(audioChunks, { type: mimeType });

      console.log("생성된 Blob 정보:", {
        size: audioBlob.size,
        type: audioBlob.type,
      });

      processVoicePipeline(audioBlob);
    };

    clearCanvas();
    console.log("마이크 접근 권한이 허용되었습니다.");
    return true;
  } catch (error) {
    console.error("마이크 접근 권한 오류:", error);
    alert("음성 기능을 사용하려면 마이크 접근 권한이 필요합니다.");
    return false;
  }
}

// 음성 감지 함수
function detectVoice(dataArray) {
  let sum = 0;
  const bufferLength = dataArray.length;

  for (let i = 0; i < bufferLength; i++) {
    sum += dataArray[i];
  }

  const average = sum / bufferLength;

  voiceLevelHistory.push(average);
  voiceLevelHistory.shift();

  const avgVoiceLevel =
    voiceLevelHistory.reduce((a, b) => a + b, 0) / voiceLevelHistory.length;

  const threshold = 30;
  if (avgVoiceLevel > threshold) {
    if (!isSpeaking) {
      isSpeaking = true;
      const circleContainer = document.getElementById("circleContainer");
      if (circleContainer) {
        circleContainer.classList.remove("idle");
        circleContainer.classList.add("active");
      }
      updateMicButtonState();

      // 점들을 말하기 상태로 부드럽게 변경
      if (isRecording) {
        setDotsSpeaking();
      }
    }
  } else {
    if (isSpeaking) {
      isSpeaking = false;

      clearTimeout(speechTimer);
      speechTimer = setTimeout(() => {
        if (!isSpeaking) {
          const circleContainer = document.getElementById("circleContainer");
          if (circleContainer) {
            circleContainer.classList.add("idle");
            circleContainer.classList.remove("active");
          }
          updateMicButtonState();

          // 점들을 평상시 상태로 부드럽게 변경
          if (isRecording) {
            setDotsIdle();
          }
        }
      }, 800);
    }
  }

  return average;
}

// 오디오 시각화
function visualize() {
  if (!visualizationActive) {
    return;
  }

  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    if (!visualizationActive) {
      clearCanvas();
      return;
    }

    animationId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);

    const voiceLevel = detectVoice(dataArray);

    if (isRecording) {
      if (voiceLevel > SILENCE_THRESHOLD) {
        lastAudioLevel = voiceLevel;
        if (silenceTimer) {
          clearTimeout(silenceTimer);
          silenceTimer = null;
        }
      } else if (lastAudioLevel > SILENCE_THRESHOLD) {
        if (!silenceTimer) {
          silenceTimer = setTimeout(() => {
            console.log("침묵이 감지되어 녹음을 중지합니다.");
            stopRecording();
          }, SILENCE_DURATION);
        }
      }
      lastAudioLevel = voiceLevel;
    }
  }

  draw();
} 