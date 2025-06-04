// SSE 클라이언트 관리
class SSEClient {
    constructor(serverUrl = 'http://localhost:8505', clientId = null) {
        this.serverUrl = serverUrl;
        this.clientId = clientId || this.generateClientId();
        this.eventSource = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 1초
        this.listeners = new Map();
        
        console.log(`SSE 클라이언트 초기화: ${this.clientId}`);
    }
    
    generateClientId() {
        return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    connect() {
        if (this.isConnected) {
            console.log('이미 SSE에 연결되어 있습니다.');
            return;
        }
        
        const url = `${this.serverUrl}/events/${this.clientId}`;
        console.log(`SSE 연결 시도: ${url}`);
        
        try {
            this.eventSource = new EventSource(url);
            
            this.eventSource.onopen = (event) => {
                console.log('SSE 연결 성공');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connected', { clientId: this.clientId });
            };
            
            this.eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('SSE 메시지 수신:', data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('SSE 메시지 파싱 오류:', error);
                }
            };
            
            this.eventSource.onerror = (event) => {
                console.error('SSE 연결 오류:', event);
                this.isConnected = false;
                this.emit('error', event);
                
                // 자동 재연결 시도
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`SSE 재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                    
                    setTimeout(() => {
                        this.disconnect();
                        this.connect();
                    }, this.reconnectDelay * this.reconnectAttempts);
                } else {
                    console.error('SSE 재연결 시도 횟수 초과');
                    this.emit('maxReconnectAttemptsReached');
                }
            };
            
        } catch (error) {
            console.error('SSE 연결 실패:', error);
            this.emit('connectionFailed', error);
        }
    }
    
    disconnect() {
        if (this.eventSource) {
            console.log('SSE 연결 해제');
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isConnected = false;
        this.emit('disconnected');
    }
    
    handleMessage(data) {
        const { type } = data;
        
        // 타입별 이벤트 발생
        this.emit(type, data);
        this.emit('message', data);
        
        // 특별한 메시지 타입 처리
        switch (type) {
            case 'connection':
                console.log('연결 확인 메시지:', data.message);
                break;
            case 'heartbeat':
                // heartbeat는 로그 출력하지 않음 (연결 유지용)
                break;
            case 'voice_status':
                this.handleVoiceStatus(data);
                break;
            case 'info':
            case 'success':
            case 'warning':
            case 'error':
                this.handleNotification(data);
                break;
            default:
                console.log('알 수 없는 메시지 타입:', type, data);
        }
    }
    
    handleVoiceStatus(data) {
        console.log(`음성 상태 업데이트: ${data.status} - ${data.message}`);
        this.emit('voiceStatusChanged', data);
    }
    
    handleNotification(data) {
        console.log(`알림 수신 [${data.type}]: ${data.title} - ${data.message}`);
        this.showNotification(data);
    }
    
    showNotification(data) {
        // 브라우저 알림 표시
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(data.title, {
                body: data.message,
                icon: this.getNotificationIcon(data.type),
                tag: data.type
            });
        }
        
        // 커스텀 알림 UI 표시
        this.showCustomNotification(data);
    }
    
    showCustomNotification(data) {
        // 알림 컨테이너 생성 또는 가져오기
        let container = document.getElementById('sse-notifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'sse-notifications';
            container.className = 'sse-notifications-container';
            document.body.appendChild(container);
        }
        
        // 알림 요소 생성
        const notification = document.createElement('div');
        notification.className = `sse-notification sse-notification-${data.type}`;
        notification.innerHTML = `
            <div class="sse-notification-header">
                <span class="sse-notification-icon">${this.getNotificationEmoji(data.type)}</span>
                <span class="sse-notification-title">${data.title}</span>
                <button class="sse-notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="sse-notification-message">${data.message}</div>
            ${data.timestamp ? `<div class="sse-notification-time">${new Date(data.timestamp).toLocaleTimeString()}</div>` : ''}
        `;
        
        // 알림 추가
        container.appendChild(notification);
        
        // 애니메이션 효과
        setTimeout(() => {
            notification.classList.add('sse-notification-show');
        }, 100);
        
        // 자동 제거 (오류는 수동으로만 제거)
        if (data.type !== 'error') {
            setTimeout(() => {
                notification.classList.remove('sse-notification-show');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }, 5000);
        }
    }
    
    getNotificationIcon(type) {
        const icons = {
            info: '/static/icons/info.png',
            success: '/static/icons/success.png',
            warning: '/static/icons/warning.png',
            error: '/static/icons/error.png',
            voice_status: '/static/icons/voice.png'
        };
        return icons[type] || icons.info;
    }
    
    getNotificationEmoji(type) {
        const emojis = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌',
            voice_status: '🎤',
            connection: '🔗'
        };
        return emojis[type] || 'ℹ️';
    }
    
    // 이벤트 리스너 관리
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }
    
    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }
    
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`이벤트 리스너 오류 (${event}):`, error);
                }
            });
        }
    }
    
    // 브라우저 알림 권한 요청
    async requestNotificationPermission() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            console.log('알림 권한:', permission);
            return permission === 'granted';
        }
        return false;
    }
    
    // 연결 상태 확인
    getConnectionStatus() {
        return {
            isConnected: this.isConnected,
            clientId: this.clientId,
            reconnectAttempts: this.reconnectAttempts,
            readyState: this.eventSource ? this.eventSource.readyState : null
        };
    }
}

// 글로벌 SSE 클라이언트 인스턴스
let sseClient = null;

// SSE 클라이언트 초기화 함수
function initSSEClient() {
    if (sseClient) {
        console.log('SSE 클라이언트가 이미 초기화되어 있습니다.');
        return sseClient;
    }
    
    sseClient = new SSEClient();
    
    // 기본 이벤트 리스너 등록
    sseClient.on('connected', (data) => {
        console.log('SSE 연결됨:', data);
        showSSEStatus('connected', 'SSE 연결됨');
    });
    
    sseClient.on('disconnected', () => {
        console.log('SSE 연결 해제됨');
        showSSEStatus('disconnected', 'SSE 연결 해제됨');
    });
    
    sseClient.on('error', (error) => {
        console.error('SSE 오류:', error);
        showSSEStatus('error', 'SSE 연결 오류');
    });
    
    sseClient.on('maxReconnectAttemptsReached', () => {
        console.error('SSE 재연결 시도 횟수 초과');
        showSSEStatus('error', 'SSE 재연결 실패');
    });
    
    sseClient.on('connectionFailed', (error) => {
        console.error('SSE 연결 실패:', error);
        showSSEStatus('error', 'SSE 연결 실패');
    });
    
    sseClient.on('voiceStatusChanged', (data) => {
        console.log('음성 상태 변경:', data);
        updateVoiceStatusUI(data);
    });
    
    // 알림 권한 요청
    sseClient.requestNotificationPermission();
    
    return sseClient;
}

// SSE 상태 표시 함수
function showSSEStatus(status, message) {
    // 상태 표시 UI 업데이트
    const statusElement = document.getElementById('sse-status');
    if (statusElement) {
        // 이전 애니메이션 클래스 제거
        statusElement.classList.remove('sse-status-just-connected');
        
        // SVG 벨 아이콘
        const bellIcon = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 19V20H3V19L5 17V11C5 7.9 7 5.2 10 4.3V4C10 2.9 10.9 2 12 2S14 2.9 14 4V4.3C17 5.2 19 7.9 19 11V17L21 19ZM12 22C10.9 22 10 21.1 10 20H14C14 21.1 13.1 22 12 22Z"/>
            </svg>
        `;
        
        // 상태 업데이트 (텍스트 없이 아이콘만)
        statusElement.className = `sse-status sse-status-${status}`;
        statusElement.innerHTML = `<div class="sse-status-icon">${bellIcon}</div>`;
        statusElement.title = message; // 툴팁으로 상태 메시지 표시
        
        // 연결 성공 시 반짝임 효과
        if (status === 'connected') {
            setTimeout(() => {
                statusElement.classList.add('sse-status-just-connected');
            }, 100);
            
            // 애니메이션 완료 후 클래스 제거
            setTimeout(() => {
                statusElement.classList.remove('sse-status-just-connected');
            }, 900);
        }
    }
    
    // 음성 챗봇 페이지에 상태 알림
    if (typeof notifyStreamlit === 'function') {
        notifyStreamlit({
            type: 'sse_status',
            status: status,
            message: message
        });
    }
}

// 음성 상태 UI 업데이트 함수
function updateVoiceStatusUI(data) {
    // 음성 상태에 따른 UI 업데이트
    const { status, message } = data;
    
    // 점들 상태 업데이트
    switch (status) {
        case 'idle':
            if (typeof setDotsIdle === 'function') setDotsIdle();
            break;
        case 'recording':
            // 녹음 중 상태는 로컬에서 관리
            break;
        case 'processing':
            if (typeof setDotsProcessing === 'function') setDotsProcessing();
            break;
        case 'speaking':
            if (typeof setDotsTTSPlaying === 'function') setDotsTTSPlaying();
            break;
    }
    
    // 상태 메시지 표시
    if (message) {
        console.log(`음성 상태: ${status} - ${message}`);
    }
}

// SSE 클라이언트 연결 함수
function connectSSE() {
    const client = initSSEClient();
    client.connect();
    return client;
}

// SSE 클라이언트 연결 해제 함수
function disconnectSSE() {
    if (sseClient) {
        sseClient.disconnect();
    }
}

// 페이지 언로드 시 연결 해제
window.addEventListener('beforeunload', () => {
    disconnectSSE();
}); 