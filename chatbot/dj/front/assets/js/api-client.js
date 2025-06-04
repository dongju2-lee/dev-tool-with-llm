// Agent Mode 관리
let currentAgentMode = "general"; // 기본값은 general
let currentSessionId = null; // 현재 세션 ID 추적

// Agent Mode 초기화 함수 (세션 시작 시 호출)
function resetAgentMode() {
    currentAgentMode = "general";
    console.log("Agent Mode 초기화:", currentAgentMode);
}

// Agent Mode 업데이트 함수
function updateAgentMode(newMode) {
    if (newMode && newMode !== currentAgentMode) {
        console.log(`Agent Mode 변경: ${currentAgentMode} → ${newMode}`);
        currentAgentMode = newMode;
    }
}

// 세션 변경 감지 및 Agent Mode 초기화
function checkSessionChange(sessionId) {
    if (sessionId && sessionId !== currentSessionId) {
        console.log(`세션 변경 감지: ${currentSessionId} → ${sessionId}`);
        currentSessionId = sessionId;
        resetAgentMode();
    }
}

// STT 서버로 오디오 전송
async function sendAudioToSTTServer(audioBase64) {
  try {
    console.log("  → STT 서버로 요청 전송 시작...");
    console.log("  → 서버 URL:", `${VOICE_SERVER_HOST}/transcribe`);
    console.log("  → 데이터 크기:", audioBase64.length, "문자");

    const response = await fetch(`${VOICE_SERVER_HOST}/transcribe`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        audio_data: audioBase64,
      }),
    });

    console.log("  → STT 서버 응답 상태:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("  → STT 서버 오류 응답:", errorText);
      throw new Error(`STT 서버 오류: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    console.log("  → STT 서버 응답 성공:", result);
    return result;
  } catch (error) {
    console.error("  → STT 요청 실패:", error.message);
    throw error;
  }
}

// 챗봇 서버로 메시지 전송
async function sendMessageToChatbot(message) {
  try {
    console.log("  → 챗봇 서버로 요청 전송 시작...");
    console.log("  → 서버 URL:", `${AGENT_SERVER_HOST}/ask`);
    console.log("  → 메시지:", message);
    console.log("  → 현재 Agent Mode:", currentAgentMode);

    const response = await fetch(`${AGENT_SERVER_HOST}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        message: message,
        agent_mode: currentAgentMode,
      }),
    });

    console.log("  → 챗봇 서버 응답 상태:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("  → 챗봇 서버 오류 응답:", errorText);
      throw new Error(`챗봇 서버 오류: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    console.log("  → 챗봇 서버 응답 성공", result);
    
    // 서버 응답에서 agent_mode 업데이트
    if (result.agent_mode) {
      updateAgentMode(result.agent_mode);
    }
    
    return result;
  } catch (error) {
    console.error("  → 챗봇 요청 실패:", error.message);
    throw error;
  }
}

// TTS 서버로 텍스트 전송
async function sendTextToTTSServer(text) {
  try {
    console.log("  → TTS 서버로 요청 전송 시작...");
    console.log("  → 서버 URL:", `${VOICE_SERVER_HOST}/text-to-speech`);
    console.log("  → 텍스트 길이:", text.length, "문자");

    const response = await fetch(`${VOICE_SERVER_HOST}/text-to-speech`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        text: text,
      }),
    });

    console.log("  → TTS 서버 응답 상태:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("  → TTS 서버 오류 응답:", errorText);
      throw new Error(`TTS 서버 오류: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    console.log("  → TTS 서버 응답 성공");
    return result;
  } catch (error) {
    console.error("  → TTS 요청 실패:", error.message);
    throw error;
  }
}

// 전체 음성 처리 파이프라인
async function processVoicePipeline(audioBlob) {
  if (isProcessing) {
    console.log("이미 처리 중입니다.");
    return;
  }

  isProcessing = true;
  updateMicButtonState();

  try {
    console.log("=== 음성 처리 파이프라인 시작 ===");

    // 1. 오디오를 Base64로 변환
    console.log("1단계: 오디오를 Base64로 변환 중...");
    console.log("오디오 Blob 크기:", audioBlob.size, "bytes");
    console.log("오디오 Blob 타입:", audioBlob.type);

    let finalBlob = audioBlob;
    if (!audioBlob.type.includes("wav")) {
      console.log("WAV가 아닌 형식이므로 변환을 시도합니다...");
      try {
        finalBlob = await convertToWav(audioBlob);
        console.log("WAV 변환 완료:", finalBlob.size, "bytes");
      } catch (convertError) {
        console.warn("WAV 변환 실패, 원본으로 진행:", convertError);
        finalBlob = audioBlob;
      }
    }

    const audioBase64 = await blobToBase64(finalBlob);
    console.log("✅ Base64 변환 완료, 길이:", audioBase64.length);

    // 2. STT 처리 중 상태로 변경
    console.log("2단계: STT 처리 시작");
    setDotsProcessing();

    const sttResult = await sendAudioToSTTServer(audioBase64);

    if (!sttResult.success) {
      throw new Error(
        "음성 인식 실패: " + (sttResult.error || "알 수 없는 오류")
      );
    }

    const transcript = sttResult.transcript;
    const confidence = sttResult.confidence;

    console.log(`✅ STT 완료: "${transcript}" (신뢰도: ${confidence})`);

    notifyStreamlit({
      type: "stt_result",
      transcript: transcript,
      confidence: confidence,
    });

    // 3. 챗봇 처리 (processing 상태 유지)
    console.log("3단계: 챗봇 처리 준비 완료");
    const chatbotResult = await sendMessageToChatbot(transcript);

    const chatbotResponse = chatbotResult.response;
    console.log(`✅ 챗봇 완료: "${chatbotResponse}"`);

    notifyStreamlit({
      type: "chatbot_response",
      question: transcript,
      answer: chatbotResponse,
      confidence: confidence,
    });

    // 4. TTS 처리 (processing 상태 유지)
    console.log("4단계: TTS 처리 준비 완료");
    const ttsResult = await sendTextToTTSServer(chatbotResponse);

    if (!ttsResult.success) {
      throw new Error(
        "음성 변환 실패: " + (ttsResult.error || "알 수 없는 오류")
      );
    }

    const audioData = ttsResult.audio_data;
    console.log("✅ TTS 완료, 재생 시작");

    // 5. 음성 재생 (TTS 상태로 변경)
    playAudioFromBase64(audioData);

    console.log("=== 음성 처리 파이프라인 완료 ===");
  } catch (error) {
    console.error("❌ 음성 처리 파이프라인 오류:", error);
    console.error("오류 상세:", error.message);

    notifyStreamlit({
      type: "error",
      message: error.message,
    });

    isProcessing = false;
    updateMicButtonState();
    setDotsIdle(); // 오류 시 idle 상태로 복귀
  }
}

// 전역 함수로 노출 (Streamlit에서 호출 가능)
window.resetAgentMode = resetAgentMode;
window.checkSessionChange = checkSessionChange; 