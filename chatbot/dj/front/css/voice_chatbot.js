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
