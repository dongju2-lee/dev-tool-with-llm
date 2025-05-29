// 글로벌 변수 정의
let audioContext;
let analyser;
let microphone;
let isRecording = false;
let isSpeaking = false;
let animationId;
let speechTimer = null;
let voiceLevelHistory = Array(10).fill(0); // 음성 레벨 히스토리를 저장하기 위한 배열
let breathScale = 1.0; // 호흡 애니메이션 스케일
let breathDirection = 0.0005; // 호흡 애니메이션 방향과 속도

// 녹음 관련 변수
let mediaRecorder = null;
let audioChunks = [];
let silenceTimer = null;
let lastAudioLevel = 0;
const SILENCE_THRESHOLD = 20; // 침묵 감지 임계값
const SILENCE_DURATION = 2000; // 침묵 지속 시간 (2초)
const MIN_RECORDING_TIME = 1000; // 최소 녹음 시간 (1초)
let recordingStartTime = 0;
let visualizationActive = false; // 시각화 활성화 상태 변수 추가

// 별 효과 생성
document.addEventListener('DOMContentLoaded', function() {
    const starsContainer = document.getElementById('starsContainer');
    if (!starsContainer) {
        console.error('별 효과를 위한 starsContainer를 찾을 수 없습니다.');
        return;
    }
    
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
    
    // 마이크 버튼과 원 컨테이너 찾기
    const micButton = document.getElementById('micButton');
    const circleContainer = document.getElementById('circleContainer');
    const canvas = document.getElementById('audioCanvas');
    const waveContainer = document.getElementById('waveContainer');
    
    if (!micButton || !circleContainer || !canvas || !waveContainer) {
        console.error('필수 UI 요소를 찾을 수 없습니다.');
        return;
    }
    
    const canvasContext = canvas.getContext('2d');
    
    // 캔버스 초기화
    function clearCanvas() {
        if (canvas.width === 0 || canvas.height === 0) {
            const container = canvas.parentElement;
            canvas.width = container.offsetWidth;
            canvas.height = container.offsetHeight;
        }
        canvasContext.clearRect(0, 0, canvas.width, canvas.height);
    }
    
    // 호흡 효과 애니메이션 시작
    startBreathing();
    
    // 파도 애니메이션 시작
    function startWaveAnimation() {
        const waveBars = waveContainer.querySelectorAll('.wave-bar');
        waveBars.forEach(bar => {
            bar.classList.remove('idle');
            bar.classList.add('active');
        });
        console.log('파도 애니메이션이 시작되었습니다.');
    }
    
    // 파도 애니메이션 중지
    function stopWaveAnimation() {
        const waveBars = waveContainer.querySelectorAll('.wave-bar');
        waveBars.forEach(bar => {
            bar.classList.remove('active');
            bar.classList.add('idle');
            // idle 상태로 돌아갈 때 크기를 50px로 고정
            bar.style.height = '50px';
            bar.style.animationDuration = ''; // 애니메이션 속도 초기화
        });
        console.log('파도 애니메이션이 중지되었습니다.');
    }
    
    // 파도 애니메이션 강도 조절
    function updateWaveIntensity(voiceLevel) {
        const waveBars = waveContainer.querySelectorAll('.wave-bar');
        const intensity = Math.min(voiceLevel / 80, 1); // 더 민감하게 반응하도록 조정 (100 -> 80)
        
        waveBars.forEach((bar, index) => {
            // 음성 감지 시에만 높이 조절
            if (bar.classList.contains('active')) {
                // 25px, 50px 기준으로 높이 설정 - 최대 30% 증가
                const baseHeight = 50; // 기본 높이 50px
                const maxHeight = 65;  // 최대 높이 65px (50px * 1.3 = 30% 증가)
                const height = baseHeight + (maxHeight - baseHeight) * intensity;
                bar.style.height = `${height}px`;
                
                // 애니메이션 속도도 조절 (더 느리게)
                const baseSpeed = 1.8;
                const maxSpeed = 1.2;
                const speed = baseSpeed - (baseSpeed - maxSpeed) * intensity;
                bar.style.animationDuration = `${speed}s`;
            } else {
                // idle 상태에서는 항상 50px 유지
                bar.style.height = '50px';
            }
        });
    }
    
    // 마이크 초기화 함수
    async function setupMicrophone() {
        try {
            // 오디오 컨텍스트 생성
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            
            // 마이크 스트림 요청
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            microphone = audioContext.createMediaStreamSource(stream);
            microphone.connect(analyser);
            
            // MediaRecorder 설정
            mediaRecorder = new MediaRecorder(stream);
            
            // 데이터 수집
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            
            // 녹음 완료 처리
            mediaRecorder.onstop = () => {
                // 녹음된 오디오 블롭 생성
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                
                // 오디오 URL 생성
                const audioUrl = URL.createObjectURL(audioBlob);
                
                // 오디오 엘리먼트 생성 및 재생
                setTimeout(() => {
                    playRecordedAudio(audioUrl);
                    sendAudioToServer(audioBlob);
                }, 500);
            };
            
            // 초기 캔버스 클리어
            clearCanvas();
            
            console.log('마이크 접근 권한이 허용되었습니다.');
            return true;
        } catch (error) {
            console.error('마이크 접근 권한 오류:', error);
            alert('음성 기능을 사용하려면 마이크 접근 권한이 필요합니다.');
            return false;
        }
    }
    
    // 호흡 효과 애니메이션
    function startBreathing() {
        function updateBreath() {
            if (!isRecording || !isSpeaking) {
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
    
    // 녹음 시작 함수
    function startRecording() {
        if (!mediaRecorder) {
            console.error('MediaRecorder가 초기화되지 않았습니다.');
            return false;
        }
        
        if (isRecording) {
            console.log('이미 녹음 중입니다.');
            return false;
        }
        
        try {
            // 녹음 상태 초기화
            audioChunks = [];
            isRecording = true;
            recordingStartTime = Date.now();
            
            mediaRecorder.start();
            console.log('녹음이 시작되었습니다.');
            
            // UI 업데이트
            micButton.classList.add('active');
            circleContainer.classList.remove('idle');
            
            // 시각화 활성화
            visualizationActive = true;
            visualize();
            
            // Streamlit에 상태 전달
            notifyStreamlit({ isRecording: true });
            
            return true;
        } catch (error) {
            console.error('녹음 시작 오류:', error);
            resetRecording();
            return false;
        }
    }
    
    // 녹음 중지 함수
    function stopRecording() {
        if (!mediaRecorder || mediaRecorder.state === 'inactive') {
            console.log('녹음이 활성화되지 않았습니다.');
            resetRecording();
            return false;
        }
        
        // 최소 녹음 시간 검사
        const recordingDuration = Date.now() - recordingStartTime;
        if (recordingDuration < MIN_RECORDING_TIME) {
            console.log('녹음 시간이 너무 짧습니다. 무시합니다.');
            resetRecording();
            return false;
        }
        
        // 타이머 정리
        clearTimeout(silenceTimer);
        silenceTimer = null;
        
        try {
            mediaRecorder.stop();
            isRecording = false;
            isSpeaking = false;
            
            // 시각화 중지
            visualizationActive = false;
            if (animationId) {
                cancelAnimationFrame(animationId);
                animationId = null;
            }
            
            // UI 업데이트
            micButton.classList.remove('active');
            circleContainer.classList.add('idle');
            circleContainer.classList.remove('active');
            
            // Streamlit에 상태 전달
            notifyStreamlit({ isRecording: false });
            
            console.log('녹음이 중지되었습니다.');
            return true;
        } catch (error) {
            console.error('녹음 중지 오류:', error);
            resetRecording();
            return false;
        }
    }
    
    // 녹음 상태 초기화
    function resetRecording() {
        audioChunks = [];
        isRecording = false;
        isSpeaking = false;
        
        // 시각화 중지
        visualizationActive = false;
        if (animationId) {
            cancelAnimationFrame(animationId);
            animationId = null;
        }
        
        // 캔버스 초기화
        clearCanvas();
        
        // UI 업데이트
        micButton.classList.remove('active');
        circleContainer.classList.add('idle');
        
        // Streamlit에 상태 전달
        notifyStreamlit({ isRecording: false });
    }
    
    // 녹음된 오디오 재생
    function playRecordedAudio(audioUrl) {
        const audio = new Audio(audioUrl);
        audio.onloadedmetadata = () => {
            console.log(`오디오 길이: ${audio.duration}초`);
        };
        audio.onplay = () => {
            console.log('오디오 재생 시작');
            // 파도 애니메이션 시작
            startWaveAnimation();
        };
        audio.onended = () => {
            console.log('오디오 재생 완료');
            // 파도 애니메이션 중지
            stopWaveAnimation();
            URL.revokeObjectURL(audioUrl); // 메모리 정리
        };
        audio.play().catch(err => {
            console.error('오디오 재생 오류:', err);
            // 오류 시에도 파도 애니메이션 중지
            stopWaveAnimation();
        });
    }
    
    // 오디오 서버로 전송
    function sendAudioToServer(audioBlob) {
        console.log('sendAudioToServer 호출됨, audioBlob 크기:', audioBlob.size);
        
        // 현재 시간을 기반으로 고유한 파일명 생성
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const fileName = `audio_${timestamp}.wav`;
        
        console.log('생성할 파일명:', fileName);
        
        // Blob을 Base64로 변환하여 Streamlit으로 전송
        const reader = new FileReader();
        reader.onloadend = () => {
            // Base64 데이터 추출 (data:audio/wav;base64, 부분 제거)
            const base64Data = reader.result.split(',')[1];
            
            console.log('Base64 변환 완료, 데이터 길이:', base64Data.length);
            
            // Streamlit에 오디오 데이터 전송
            const audioData = {
                type: 'audio_data',
                fileName: fileName,
                timestamp: timestamp,
                audioBase64: base64Data,
                size: audioBlob.size,
                processed: false
            };
            
            console.log('Streamlit으로 오디오 데이터 전송:', {
                fileName: fileName,
                dataLength: base64Data.length,
                size: audioBlob.size
            });
            
            // 개선된 통신 함수 사용
            sendToStreamlit(audioData);
        };
        
        reader.onerror = (error) => {
            console.error('Base64 변환 오류:', error);
        };
        
        // Blob을 Base64로 변환 시작
        reader.readAsDataURL(audioBlob);
    }
    
    // Streamlit에 상태 알림
    function notifyStreamlit(data) {
        if (window.parent && window.parent.postMessage) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: data
            }, '*');
        }
    }
    
    // 오디오 시각화
    function visualize() {
        // 시각화가 비활성화되면 함수 종료
        if (!visualizationActive) {
            return;
        }
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        function draw() {
            // 시각화가 비활성화되면 애니메이션 중지
            if (!visualizationActive) {
                clearCanvas();
                return;
            }
            
            animationId = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);
            
            // 음성 활성화 감지
            const voiceLevel = detectVoice(dataArray);
            
            // 침묵 감지 처리
            if (isRecording) {
                if (voiceLevel > SILENCE_THRESHOLD) {
                    // 음성이 감지됨
                    lastAudioLevel = voiceLevel;
                    if (silenceTimer) {
                        clearTimeout(silenceTimer);
                        silenceTimer = null;
                    }
                } else if (lastAudioLevel > SILENCE_THRESHOLD) {
                    // 이전에 음성이 있었지만 지금은 침묵 - 타이머 시작
                    if (!silenceTimer) {
                        silenceTimer = setTimeout(() => {
                            console.log('침묵이 감지되어 녹음을 중지합니다.');
                            stopRecording();
                        }, SILENCE_DURATION);
                    }
                }
                lastAudioLevel = voiceLevel;
            }
            
            // 캔버스 그리기
            drawAudioVisualization(dataArray, voiceLevel);
        }
        
        draw();
    }
    
    // 음성 감지 함수
    function detectVoice(dataArray) {
        // 음성 신호의 평균 크기 계산
        let sum = 0;
        const bufferLength = dataArray.length;
        
        for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
        }
        
        const average = sum / bufferLength;
        
        // 음성 레벨 히스토리 업데이트 (FIFO)
        voiceLevelHistory.push(average);
        voiceLevelHistory.shift();
        
        // 평균 음성 레벨 계산
        const avgVoiceLevel = voiceLevelHistory.reduce((a, b) => a + b, 0) / voiceLevelHistory.length;
        
        // 음성이 일정 임계값을 넘으면 크기를 부드럽게 변경
        const threshold = 30;
        if (avgVoiceLevel > threshold) {
            // 말하기 상태 업데이트
            if (!isSpeaking) {
                isSpeaking = true;
                circleContainer.classList.remove('idle');
                circleContainer.classList.add('active');
                micButton.classList.add('active');
                // 녹음 중일 때 파도 애니메이션 시작
                if (isRecording) {
                    startWaveAnimation();
                }
            }
            
            // 파도 애니메이션 강도 업데이트 (녹음 중일 때만)
            if (isRecording) {
                updateWaveIntensity(avgVoiceLevel);
            }
        } else {
            // 말하기 중지 상태 감지
            if (isSpeaking) {
                isSpeaking = false;
                
                // 말하기 타이머 설정 (즉시 원 상태 변경은 하지 않고 지연시간 후 처리)
                clearTimeout(speechTimer);
                speechTimer = setTimeout(() => {
                    if (!isSpeaking) {
                        circleContainer.classList.add('idle');
                        circleContainer.classList.remove('active');
                        micButton.classList.remove('active');
                        // 녹음 중 말하기가 중지되면 파도 애니메이션도 중지
                        if (isRecording) {
                            stopWaveAnimation();
                        }
                    }
                }, 800);
            }
        }
        
        return average;
    }
    
    // 오디오 시각화 그리기
    function drawAudioVisualization(dataArray, voiceLevel) {
        // 캔버스는 사용하지 않고 음성 감지만 수행
        // 별도의 그리기 작업 없음
    }
    
    // 마이크 버튼 클릭 처리
    micButton.addEventListener('click', async function() {
        // 버튼 중복 클릭 방지
        if (micButton.disabled) return;
        micButton.disabled = true;
        
        try {
            if (isRecording) {
                // 녹음 중지
                console.log('녹음 중지 시작');
                stopRecording();
                
                // UI 즉시 업데이트
                micButton.classList.add('muted');
                micButton.classList.remove('active');
                micButton.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E64626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                        <line x1="12" y1="19" x2="12" y2="23"></line>
                        <line x1="8" y1="23" x2="16" y2="23"></line>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                `;
                console.log('녹음 중지 UI 업데이트 완료');
            } else {
                // 녹음 시작
                console.log('녹음 시작 시도');
                
                // 마이크 권한 확인
                if (!audioContext || !mediaRecorder) {
                    console.log('마이크 재초기화 필요');
                    const success = await setupMicrophone();
                    if (!success) {
                        console.error('마이크 초기화 실패');
                        return;
                    }
                }
                
                // UI 즉시 업데이트
                micButton.classList.remove('muted');
                micButton.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                        <line x1="12" y1="19" x2="12" y2="23"></line>
                        <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                `;
                
                // 녹음 시작
                startRecording();
                console.log('녹음 시작 완료');
            }
        } catch (error) {
            console.error('마이크 버튼 처리 중 오류:', error);
            // 오류 발생 시 상태 초기화
            resetRecording();
        } finally {
            // 버튼 활성화 (약간의 지연 후)
            setTimeout(() => {
                micButton.disabled = false;
            }, 300);
        }
    });
    
    // 초기화
    setupMicrophone();
});
