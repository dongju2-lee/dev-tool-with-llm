"""
음성 챗봇 페이지 구현
"""

import streamlit as st
import time
import os
from pathlib import Path

def voice_chatbot_page():
    """음성 챗봇 페이지 구현"""
    # 페이지 타이틀 숨기기
    st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        header {
            visibility: hidden;
        }
        #MainMenu {
            visibility: hidden;
        }
        footer {
            visibility: hidden;
        }
        .stDeployButton {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 음성 인터페이스 HTML 구현 (CSS와 JS를 직접 포함)
    voice_interface_html = """
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: white;
        }
        
        .voice-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            width: 100%;
            position: relative;
        }
        
        .circle-container {
            width: 200px;  /* 원 크기 축소 (300px -> 200px) */
            height: 200px; /* 원 크기 축소 (300px -> 200px) */
            position: relative;
            margin-bottom: 60px;
            filter: drop-shadow(0 0 15px rgba(32, 156, 238, 0.3));
            transition: all 1.2s cubic-bezier(0.34, 1.56, 0.64, 1); /* 부드러운 전환 효과 */
        }
        
        /* 말할 때 원이 부드럽게 커지는 애니메이션 */
        .circle-container.active {
            transform: scale(1.05);
            transition: all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        /* 호흡 애니메이션 (살짝 크기가 변하는 효과) */
        @keyframes breathe {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        
        .circle-container.idle {
            animation: breathe 4s ease-in-out infinite;
        }
        
        .voice-circle {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: radial-gradient(circle at center, #2979c2 0%, #1a5c99 40%, #0d4075 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
            box-shadow: inset 0 0 30px rgba(109, 193, 255, 0.4);
        }
        
        .voice-circle::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at center, rgba(109, 193, 255, 0.2) 0%, rgba(109, 193, 255, 0.1) 30%, transparent 70%);
            animation: rotate 20s linear infinite;
        }
        
        @keyframes rotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .voice-visualizer {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1;
        }
        
        .voice-indicator {
            position: absolute;
            bottom: -60px;
            width: 100%;
            text-align: center;
            color: #1a5c99;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .info-icon {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: 1px solid #1a5c99;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .controls {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 40px; /* 버튼 위치를 아래로 조정 */
            gap: 30px;
        }
        
        .mic-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: #f0f8ff;
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 20px rgba(32, 156, 238, 0.2);
        }
        
        .mic-button:hover {
            background-color: #e1f5fe;
            transform: scale(1.05);
        }
        
        .mic-button.muted {
            background-color: #fddede;
        }
        
        .mic-button svg {
            width: 24px;
            height: 24px;
            color: #1a5c99;
        }
        
        /* 마이크 버튼 활성화 시 빛나는 효과 */
        .mic-button.active {
            box-shadow: 0 0 0 4px rgba(32, 156, 238, 0.2), 0 2px 20px rgba(32, 156, 238, 0.4);
        }
        
        .cancel-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: #f0f8ff;
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 20px rgba(32, 156, 238, 0.2);
        }
        
        .cancel-button:hover {
            background-color: #e1f5fe;
        }
        
        .audio-canvas {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
        }
        
        /* 오디오 시각화를 위한 스타일 */
        @keyframes pulse {
            0% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.2); opacity: 0.8; }
            100% { transform: scale(1); opacity: 0.5; }
        }
        
        .audio-pulse {
            position: absolute;
            background: rgba(109, 193, 255, 0.25);
            border-radius: 50%;
            width: 70%;
            height: 70%;
            animation: pulse 2s infinite;
        }
        
        /* 여러 겹의 펄스 애니메이션 */
        .audio-pulse-1 {
            animation-delay: 0s;
            background: radial-gradient(circle, rgba(144, 202, 249, 0.3) 0%, rgba(109, 193, 255, 0.15) 70%);
        }
        
        .audio-pulse-2 {
            animation-delay: 0.5s;
            width: 60%;
            height: 60%;
            background: radial-gradient(circle, rgba(144, 202, 249, 0.25) 0%, rgba(109, 193, 255, 0.1) 70%);
        }
        
        .audio-pulse-3 {
            animation-delay: 1s;
            width: 50%;
            height: 50%;
            background: radial-gradient(circle, rgba(144, 202, 249, 0.2) 0%, rgba(109, 193, 255, 0.05) 70%);
        }
        
        /* 별 효과 */
        .stars {
            position: absolute;
            width: 100%;
            height: 100%;
            pointer-events: none;
            overflow: hidden;
        }
        
        .star {
            position: absolute;
            background-color: white;
            border-radius: 50%;
            opacity: 0;
            animation: twinkle-star 3s ease infinite;
        }
        
        @keyframes twinkle-star {
            0%, 100% { opacity: 0; }
            50% { opacity: 0.8; }
        }
    </style>
    
    <div class="voice-container">
        <div id="circleContainer" class="circle-container idle">
            <div class="voice-circle">
                <canvas id="audioCanvas" class="audio-canvas"></canvas>
                <div class="stars" id="starsContainer"></div>
                <div class="voice-visualizer">
                    <div class="audio-pulse audio-pulse-1"></div>
                    <div class="audio-pulse audio-pulse-2"></div>
                    <div class="audio-pulse audio-pulse-3"></div>
                </div>
            </div>
        </div>
        
        <div class="voice-indicator">
            Standard voice
            <div class="info-icon">i</div>
        </div>
        
        <div class="controls">
            <button id="micButton" class="mic-button">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                </svg>
            </button>
        </div>
    </div>
    
    <script>
        // 별 효과 생성
        document.addEventListener('DOMContentLoaded', function() {
            const starsContainer = document.getElementById('starsContainer');
            const circleRadius = starsContainer.offsetWidth / 2;
            
            // 별 생성 함수
            function createStars(count) {
                for (let i = 0; i < count; i++) {
                    const star = document.createElement('div');
                    star.classList.add('star');
                    
                    // 별 위치 (원 안에 랜덤하게 배치)
                    let angle = Math.random() * Math.PI * 2;
                    let distance = Math.random() * circleRadius * 0.8;
                    let x = circleRadius + Math.cos(angle) * distance;
                    let y = circleRadius + Math.sin(angle) * distance;
                    
                    star.style.left = `${x}px`;
                    star.style.top = `${y}px`;
                    
                    // 별 크기
                    const size = Math.random() * 2 + 1;
                    star.style.width = `${size}px`;
                    star.style.height = `${size}px`;
                    
                    // 애니메이션 지연
                    star.style.animationDelay = `${Math.random() * 3}s`;
                    star.style.animationDuration = `${3 + Math.random() * 4}s`;
                    
                    starsContainer.appendChild(star);
                }
            }
            
            // 40-60개의 별 생성
            createStars(Math.floor(Math.random() * 20) + 40);
        });

        // 페이지 로드 시 마이크 권한 요청
        document.addEventListener('DOMContentLoaded', function() {
            let audioContext;
            let analyser;
            let microphone;
            let isRecording = true;
            let isSpeaking = false;
            let animationId;
            let speechTimer = null;
            let voiceLevelHistory = Array(10).fill(0); // 음성 레벨 히스토리를 저장하기 위한 배열
            let breathScale = 1.0; // 호흡 애니메이션 스케일
            let breathDirection = 0.0005; // 호흡 애니메이션 방향과 속도
            
            const micButton = document.getElementById('micButton');
            const circleContainer = document.getElementById('circleContainer');
            const canvas = document.getElementById('audioCanvas');
            const canvasContext = canvas.getContext('2d');
            
            // 캔버스 크기 설정
            function resizeCanvas() {
                const container = canvas.parentElement;
                canvas.width = container.offsetWidth;
                canvas.height = container.offsetHeight;
            }
            
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
            
            // 부드러운 스케일 변화를 위한 함수
            function updateBreathingScale(voiceLevel) {
                // 음성 레벨 히스토리 업데이트 (FIFO)
                voiceLevelHistory.push(voiceLevel);
                voiceLevelHistory.shift();
                
                // 평균 음성 레벨 계산
                const avgVoiceLevel = voiceLevelHistory.reduce((a, b) => a + b, 0) / voiceLevelHistory.length;
                
                // 음성이 일정 임계값을 넘으면 크기를 부드럽게 변경
                const threshold = 30;
                if (avgVoiceLevel > threshold) {
                    // 음성 레벨에 따라 스케일 목표치 계산 (1.0 ~ 1.05)
                    const targetScale = 1.0 + Math.min((avgVoiceLevel - threshold) / 100, 0.05);
                    
                    // 현재 스케일에서 목표 스케일로 부드럽게 보간
                    breathScale += (targetScale - breathScale) * 0.1;
                } else {
                    // 기본 호흡 애니메이션 (말하지 않을 때)
                    breathScale += breathDirection;
                    if (breathScale > 1.02) {
                        breathDirection = -0.0005;
                    } else if (breathScale < 1.0) {
                        breathDirection = 0.0005;
                    }
                }
                
                // 스케일 적용
                circleContainer.style.transform = `scale(${breathScale})`;
                
                return avgVoiceLevel > threshold;
            }
            
            // 음성 활성화 감지 및 애니메이션
            function detectSpeech(dataArray) {
                // 음성 신호의 평균 크기 계산
                let sum = 0;
                const bufferLength = dataArray.length;
                
                for (let i = 0; i < bufferLength; i++) {
                    sum += dataArray[i];
                }
                
                const average = sum / bufferLength;
                
                // 부드러운 호흡 스케일 업데이트 및 말하기 상태 감지
                const newSpeakingState = updateBreathingScale(average);
                
                // 말하기 상태가 변경되었을 때만 처리
                if (newSpeakingState !== isSpeaking) {
                    isSpeaking = newSpeakingState;
                    
                    if (isSpeaking) {
                        // 말하기 시작 - 원 커지는 효과를 위한 클래스 전환
                        circleContainer.classList.remove('idle');
                        micButton.classList.add('active');
                        
                        // 말하기 타이머 초기화
                        clearTimeout(speechTimer);
                    } else {
                        // 말하기 중지 - 타이머 설정 (0.8초 후 원 크기 원상복구)
                        clearTimeout(speechTimer);
                        speechTimer = setTimeout(() => {
                            circleContainer.classList.add('idle');
                            micButton.classList.remove('active');
                        }, 800);
                    }
                }
                
                return average;
            }
            
            // 마이크 초기화 및 권한 요청
            async function initMicrophone() {
                try {
                    // 오디오 컨텍스트 생성
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    analyser = audioContext.createAnalyser();
                    analyser.fftSize = 256;
                    
                    // 마이크 스트림 요청
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    microphone = audioContext.createMediaStreamSource(stream);
                    microphone.connect(analyser);
                    
                    // 시각화 시작
                    visualize();
                    
                    console.log('마이크 접근 권한이 허용되었습니다.');
                } catch (error) {
                    console.error('마이크 접근 권한 오류:', error);
                    alert('음성 기능을 사용하려면 마이크 접근 권한이 필요합니다.');
                }
            }
            
            // 오디오 시각화
            function visualize() {
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                
                function draw() {
                    if (!isRecording) {
                        // 녹음 중지 상태에서는 시각화 중지
                        canvasContext.clearRect(0, 0, canvas.width, canvas.height);
                        return;
                    }
                    
                    animationId = requestAnimationFrame(draw);
                    analyser.getByteFrequencyData(dataArray);
                    
                    // 음성 활성화 감지
                    const voiceLevel = detectSpeech(dataArray);
                    
                    canvasContext.clearRect(0, 0, canvas.width, canvas.height);
                    
                    // 원형으로 오디오 시각화
                    const centerX = canvas.width / 2;
                    const centerY = canvas.height / 2;
                    const radius = Math.min(centerX, centerY) * 0.8;
                    
                    // 빛나는 효과를 위한 그라데이션
                    const gradient = canvasContext.createRadialGradient(
                        centerX, centerY, radius * 0.2,
                        centerX, centerY, radius
                    );
                    gradient.addColorStop(0, 'rgba(144, 202, 249, 0.6)');
                    gradient.addColorStop(0.5, 'rgba(109, 193, 255, 0.4)');
                    gradient.addColorStop(1, 'rgba(109, 193, 255, 0)');
                    
                    // 음성 레벨에 따라 시각화 크기 조정 (부드럽게)
                    const amplitudeFactor = 0.5 + (voiceLevel / 255) * 0.5;
                    
                    // 원 주변에 오디오 스펙트럼 그리기
                    for (let i = 0; i < bufferLength; i++) {
                        const value = dataArray[i];
                        const percent = value / 255;
                        const barHeight = radius * percent * amplitudeFactor;
                        const angle = (i * Math.PI * 2) / bufferLength;
                        
                        const x1 = centerX + Math.cos(angle) * (radius - barHeight);
                        const y1 = centerY + Math.sin(angle) * (radius - barHeight);
                        const x2 = centerX + Math.cos(angle) * radius;
                        const y2 = centerY + Math.sin(angle) * radius;
                        
                        canvasContext.beginPath();
                        canvasContext.moveTo(x1, y1);
                        canvasContext.lineTo(x2, y2);
                        
                        // 바 색상 더 밝고 선명하게 조정
                        canvasContext.strokeStyle = `rgba(221, 242, 255, ${percent * 0.9})`;
                        canvasContext.lineWidth = 2.5;
                        canvasContext.stroke();
                    }
                    
                    // 중앙에 발광 효과
                    canvasContext.beginPath();
                    canvasContext.arc(centerX, centerY, radius * 0.4, 0, Math.PI * 2);
                    canvasContext.fillStyle = gradient;
                    canvasContext.fill();
                    
                    // 음성 레벨에 따라 내부 원 크기 조정
                    const innerCircleSize = radius * 0.2 * (1 + voiceLevel / 255);
                    canvasContext.beginPath();
                    canvasContext.arc(centerX, centerY, innerCircleSize, 0, Math.PI * 2);
                    canvasContext.fillStyle = 'rgba(144, 202, 249, 0.45)';
                    canvasContext.fill();
                }
                
                draw();
            }
            
            // 마이크 버튼 클릭 처리
            micButton.addEventListener('click', function() {
                isRecording = !isRecording;
                
                if (isRecording) {
                    // 녹음 시작
                    micButton.classList.remove('muted');
                    micButton.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                            <line x1="12" y1="19" x2="12" y2="23"></line>
                            <line x1="8" y1="23" x2="16" y2="23"></line>
                        </svg>
                    `;
                    visualize();
                    circleContainer.classList.add('idle');
                } else {
                    // 녹음 중지
                    micButton.classList.add('muted');
                    micButton.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E64626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                            <line x1="12" y1="19" x2="12" y2="23"></line>
                            <line x1="8" y1="23" x2="16" y2="23"></line>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                        </svg>
                    `;
                    cancelAnimationFrame(animationId);
                    circleContainer.classList.remove('idle');
                    circleContainer.style.transform = 'scale(1)';
                    micButton.classList.remove('active');
                }
                
                // Streamlit에 상태 전달
                if (window.parent && window.parent.postMessage) {
                    window.parent.postMessage({
                        type: 'recordingState',
                        isRecording: isRecording
                    }, '*');
                }
            });
            
            // 초기화
            initMicrophone();
        });
    </script>
    """
    
    # HTML 구성요소 삽입
    st.components.v1.html(voice_interface_html, height=700)
    
    # Streamlit에서 녹음 상태 확인을 위한 세션 상태 초기화
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = True
    
    # JavaScript에서 전달된 녹음 상태를 처리하기 위한 콜백 함수
    st.markdown("""
    <script>
        window.addEventListener('message', function(event) {
            if (event.data.type === 'recordingState') {
                // Streamlit에 이벤트 전달 (추후 확장을 위해)
                const streamlitDoc = window.parent.document;
                const event = new CustomEvent('recordingStateChange', { 
                    detail: { isRecording: event.data.isRecording } 
                });
                streamlitDoc.dispatchEvent(event);
            }
        });
    </script>
    """, unsafe_allow_html=True)
    
    # 디버깅용 (실제 앱에서는 숨김 처리 가능)
    with st.expander("디버깅 정보", expanded=False):
        st.write("녹음 상태:", "활성화" if st.session_state.is_recording else "비활성화")
        
        if st.button("음성 처리 테스트"):
            with st.spinner("음성을 처리 중입니다..."):
                # 실제로는 여기서 음성 인식 및 챗봇 처리 로직이 필요함
                time.sleep(2)
                
                # 음성 처리 결과 표시 (예시)
                st.session_state.last_voice_input = "안녕하세요, 무엇을 도와드릴까요?"
                st.session_state.last_response = "안녕하세요! 오늘 도움이 필요하신 내용이 있으신가요?"
            
            # 처리 결과 표시
            if 'last_voice_input' in st.session_state and 'last_response' in st.session_state:
                st.text_area("음성 입력:", value=st.session_state.last_voice_input, height=100)
                st.text_area("챗봇 응답:", value=st.session_state.last_response, height=100)