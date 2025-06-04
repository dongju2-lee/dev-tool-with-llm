// SSE 클라이언트 관리
class SSEClient {
    constructor(serverUrl = 'http://localhost:8505', clientId = null) {
        this.serverUrl = serverUrl;
        this.clientId = clientId || this.generateClientId();
        this.eventSource = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // 2초
        this.eventListeners = {};
        
        console.log(`SSE 클라이언트 생성됨 - Client ID: ${this.clientId}`);
    }
    
    generateClientId() {
        return 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
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
                    console.log('SSE 알림 수신:', data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('SSE 알림 파싱 오류:', error);
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
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isConnected = false;
        this.emit('disconnected');
        console.log('SSE 연결 해제됨');
    }
    
    handleMessage(data) {
        const { type } = data;
        
        // 타입별 이벤트 발생
        this.emit(type, data);
        this.emit('message', data);
        
        // 알림 저장 (연결 알림과 하트비트 제외)
        addStoredNotification(data);
        
        // 특별한 알림 타입 처리
        switch (type) {
            case 'connection':
                console.log('연결 확인 알림:', data.message);
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
                console.log('알 수 없는 알림 타입:', type, data);
        }
    }
    
    handleVoiceStatus(data) {
        console.log(`음성 상태 변경: ${data.message}`);
        this.emit('voiceStatusChanged', data);
    }
    
    handleNotification(data) {
        console.log(`알림 수신 [${data.type}]: ${data.title} - ${data.message}`);
        this.showNotification(data);
    }
    
    showNotification(data) {
        // 브라우저 알림 표시
        if (Notification.permission === 'granted') {
            const notification = new Notification(data.title || '알림', {
                body: data.message,
                icon: '/favicon.ico',
                tag: data.type
            });
            
            setTimeout(() => {
                notification.close();
            }, 5000);
        }
        
        // 페이지 내 알림 표시
        this.showPageNotification(data);
    }
    
    showPageNotification(data) {
        const container = this.getNotificationContainer();
        const notification = this.createNotificationElement(data);
        
        container.appendChild(notification);
        
        // 애니메이션을 위한 지연
        setTimeout(() => {
            notification.classList.add('sse-notification-show');
        }, 100);
        
        // 자동 제거
        setTimeout(() => {
            this.removeNotification(notification);
        }, 5000);
    }
    
    getNotificationContainer() {
        let container = document.getElementById('sse-notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'sse-notifications-container';
            container.className = 'sse-notifications-container';
            document.body.appendChild(container);
        }
        return container;
    }
    
    createNotificationElement(data) {
        const notification = document.createElement('div');
        notification.className = `sse-notification sse-notification-${data.type}`;
        
        const icon = this.getNotificationIcon(data.type);
        const time = new Date().toLocaleTimeString();
        
        notification.innerHTML = `
            <div class="sse-notification-header">
                <span class="sse-notification-icon">${icon}</span>
                <span class="sse-notification-title">${data.title || '알림'}</span>
                <button class="sse-notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="sse-notification-message">${data.message}</div>
            <div class="sse-notification-time">${time}</div>
        `;
        
        return notification;
    }
    
    getNotificationIcon(type) {
        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌',
            voice_status: '🎤',
            connection: '🔗'
        };
        return icons[type] || 'ℹ️';
    }
    
    removeNotification(notification) {
        notification.classList.remove('sse-notification-show');
        notification.classList.add('sse-notification-exit');
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                console.log('알림 권한:', permission);
            });
        }
    }
    
    // 이벤트 리스너 관리
    on(event, callback) {
        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }
        this.eventListeners[event].push(callback);
    }
    
    off(event, callback) {
        if (this.eventListeners[event]) {
            this.eventListeners[event] = this.eventListeners[event].filter(cb => cb !== callback);
        }
    }
    
    emit(event, data) {
        if (this.eventListeners[event]) {
            this.eventListeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`이벤트 리스너 오류 [${event}]:`, error);
                }
            });
        }
    }
    
    // 서버에 알림 전송
    async sendNotification(type, title, message, targetClientId = null) {
        try {
            const payload = {
                type,
                title,
                message,
                target_client_id: targetClientId,
                sender_client_id: this.clientId
            };
            
            const response = await fetch(`${this.serverUrl}/send-notification`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('알림 전송 성공:', result);
            return result;
            
        } catch (error) {
            console.error('알림 전송 실패:', error);
            throw error;
        }
    }
}

// 글로벌 SSE 클라이언트 인스턴스
let sseClient = null;

// 알림 저장소
let storedNotifications = [];
let isNotificationsVisible = false;

// 알림 저장 함수
function addStoredNotification(data) {
    // 연결 알림과 하트비트는 저장하지 않음
    if (data.type === 'connection' || data.type === 'heartbeat') {
        return;
    }
    
    const notification = {
        id: Date.now() + Math.random(),
        type: data.type,
        title: data.title,
        message: data.message,
        timestamp: data.timestamp || new Date().toISOString(),
        data: data.data
    };
    
    storedNotifications.unshift(notification); // 최신 알림을 앞에 추가
    
    // 최대 50개 알림만 저장
    if (storedNotifications.length > 50) {
        storedNotifications = storedNotifications.slice(0, 50);
    }
    
    updateBellStatus();
    console.log('알림 저장됨:', notification);
}

// 알림 확인 처리
function confirmNotification(notificationId) {
    console.log('알림 확인 시작:', notificationId);
    console.log('삭제 전 알림 개수:', storedNotifications.length);
    
    // 알림 요소 찾기
    const notificationElements = document.querySelectorAll('.sse-notification-item');
    let targetElement = null;
    
    notificationElements.forEach(element => {
        const confirmButton = element.querySelector('.sse-notification-confirm');
        if (confirmButton && confirmButton.getAttribute('onclick').includes(notificationId)) {
            targetElement = element;
        }
    });
    
    // 저장된 알림에서 즉시 제거
    const originalLength = storedNotifications.length;
    storedNotifications = storedNotifications.filter(notification => notification.id != notificationId); // == 대신 != 사용
    console.log('삭제 후 알림 개수:', storedNotifications.length);
    
    if (originalLength === storedNotifications.length) {
        console.warn('알림이 삭제되지 않았습니다. ID 확인:', notificationId);
        // ID 타입 변환 시도
        storedNotifications = storedNotifications.filter(notification => String(notification.id) !== String(notificationId));
        console.log('타입 변환 후 삭제 시도, 알림 개수:', storedNotifications.length);
    }
    
    // 벨 상태 즉시 업데이트
    updateBellStatus();
    
    if (targetElement) {
        // 삭제 애니메이션 시작
        targetElement.classList.add('removing');
        
        // 애니메이션 완료 후 화면 업데이트
        setTimeout(() => {
            updateNotificationsDisplay();
            console.log('알림 확인 완료:', notificationId);
        }, 300);
    } else {
        // 요소를 찾지 못한 경우 바로 화면 업데이트
        updateNotificationsDisplay();
        console.log('알림 확인 완료 (요소 없음):', notificationId);
    }
}

// 벨 상태 업데이트
function updateBellStatus() {
    const hasNotifications = storedNotifications.length > 0;
    const statusElement = document.getElementById('sse-status');
    
    if (statusElement) {
        if (hasNotifications) {
            statusElement.className = 'sse-status sse-status-has-notifications';
            statusElement.title = `새 알림 ${storedNotifications.length}개`;
        } else {
            statusElement.className = 'sse-status sse-status-connected';
            statusElement.title = 'SSE 연결됨';
        }
    }
}

// 알림 목록 토글
function toggleNotifications() {
    isNotificationsVisible = !isNotificationsVisible;
    
    let container = document.getElementById('sse-notifications-container-list');
    
    if (isNotificationsVisible) {
        if (!container) {
            container = createNotificationsContainer();
        }
        container.classList.add('show');
        updateNotificationsDisplay();
    } else {
        if (container) {
            container.classList.remove('show');
        }
    }
}

// 알림 컨테이너 생성
function createNotificationsContainer() {
    const container = document.createElement('div');
    container.id = 'sse-notifications-container-list';
    container.className = 'sse-notifications-container-list';
    
    container.innerHTML = `
        <div class="sse-notifications-header">
            받은 알림
        </div>
        <div class="sse-notifications-list" id="sse-notifications-list">
            <!-- 알림들이 여기에 표시됩니다 -->
        </div>
    `;
    
    document.body.appendChild(container);
    return container;
}

// 알림 목록 업데이트
function updateNotificationsDisplay() {
    const listElement = document.getElementById('sse-notifications-list');
    if (!listElement) return;
    
    if (storedNotifications.length === 0) {
        listElement.innerHTML = `
            <div class="sse-notifications-empty">
                새로운 알림이 없습니다
            </div>
        `;
        return;
    }
    
    listElement.innerHTML = storedNotifications.map(notification => `
        <div class="sse-notification-item ${notification.type}">
            <div class="sse-notification-header-item">
                <div class="sse-notification-title-item">${notification.title}</div>
                <div class="sse-notification-time">${formatTime(notification.timestamp)}</div>
            </div>
            <div class="sse-notification-content">${notification.message}</div>
            <div class="sse-notification-actions">
                <button class="sse-notification-confirm" onclick="confirmNotification('${notification.id}')">
                    확인
                </button>
            </div>
        </div>
    `).join('');
}

// 시간 포맷팅 함수
function formatTime(timestamp) {
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffMins < 1) {
        return '방금 전';
    } else if (diffMins < 60) {
        return `${diffMins}분 전`;
    } else if (diffHours < 24) {
        return `${diffHours}시간 전`;
    } else {
        return time.toLocaleDateString();
    }
}

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
    let statusElement = document.getElementById('sse-status');
    
    if (!statusElement) {
        statusElement = document.createElement('div');
        statusElement.id = 'sse-status';
        statusElement.className = 'sse-status';
        
        // SVG 벨 아이콘
        statusElement.innerHTML = `
            <div class="sse-status-icon">
                <svg viewBox="0 0 24 24">
                    <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
                </svg>
            </div>
        `;
        
        document.body.appendChild(statusElement);
    }
    
    // onclick 이벤트 항상 설정 (함수명 변경 대응)
    statusElement.onclick = toggleNotifications;
    
    // 상태에 따른 클래스 설정
    statusElement.className = `sse-status sse-status-${status}`;
    statusElement.title = message;
    
    // 연결 성공 시 반짝임 효과
    if (status === 'connected') {
        statusElement.classList.add('sse-status-just-connected');
        setTimeout(() => {
            statusElement.classList.remove('sse-status-just-connected');
        }, 800);
    }
    
    // 알림이 있는지 확인하여 상태 업데이트
    updateBellStatus();
}

// 음성 상태 UI 업데이트 함수
function updateVoiceStatusUI(data) {
    // 음성 상태에 따른 UI 업데이트 로직
    console.log('음성 상태 UI 업데이트:', data);
}

// 외부 클릭 시 알림 목록 닫기
document.addEventListener('click', (event) => {
    const notificationsContainer = document.getElementById('sse-notifications-container-list');
    const statusElement = document.getElementById('sse-status');
    
    if (isNotificationsVisible && notificationsContainer && statusElement) {
        // 벨 아이콘이나 알림 컨테이너 내부를 클릭한 경우가 아니라면 닫기
        if (!statusElement.contains(event.target) && !notificationsContainer.contains(event.target)) {
            isNotificationsVisible = false;
            notificationsContainer.classList.remove('show');
        }
    }
});

// 페이지 로드 시 자동 초기화
document.addEventListener('DOMContentLoaded', () => {
    console.log('SSE 클라이언트 자동 초기화 시작');
    const client = initSSEClient();
    client.connect();
}); 