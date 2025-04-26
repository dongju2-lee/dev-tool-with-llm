import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// 커스텀 메트릭 정의
const itemCreationTrend = new Trend('item_creation_time');
const userCreationTrend = new Trend('user_creation_time');
const slowEndpointTrend = new Trend('slow_endpoint_time');
const errorRate = new Rate('error_rate');
const successfulRequests = new Counter('successful_requests');

// 부하 테스트 옵션 설정 - 스파이크 테스트
export const options = {
  // 스파이크 테스트 구성: 짧은 시간 동안 매우 높은 부하 발생
  stages: [
    { duration: '20s', target: 10 },   // 워밍업: 20초 동안 점진적으로 10명의 가상 사용자로 증가
    { duration: '20s', target: 10 },   // 안정화: 20초 동안 10명 유지
    { duration: '10s', target: 200 },  // 스파이크: 10초 동안 200명으로 급증
    { duration: '30s', target: 200 },  // 스파이크 유지: 30초 동안 200명 유지
    { duration: '10s', target: 10 },   // 정상화: 10초 동안 10명으로 감소
    { duration: '30s', target: 10 },   // 정리: 30초 동안 10명 유지
    { duration: '10s', target: 0 },    // 종료: 10초 동안 0명으로 감소
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% 요청이 3초 미만
    'item_creation_time': ['p(90)<2000'], // 90%의 아이템 생성이 2초 미만
    'user_creation_time': ['p(90)<2000'], // 90%의 사용자 생성이 2초 미만
    'slow_endpoint_time': ['p(75)<5000'], // 75%의 느린 엔드포인트 호출이 5초 미만
    'error_rate': ['rate<0.1'], // 에러율 10% 미만
    http_req_failed: ['rate<0.1'], // 요청 실패율 10% 미만
  },
};

// 테스트할 API 서버 URL
const BASE_URL = __ENV.API_URL || 'http://localhost:8080';

// 임의의 아이템 데이터 생성
function generateRandomItem() {
  const itemNames = ['책', '컴퓨터', '스마트폰', '의자', '책상', '모니터', '키보드', '마우스', '헤드폰', '스피커'];
  const randomName = itemNames[Math.floor(Math.random() * itemNames.length)];
  
  return {
    name: `${randomName} ${Math.floor(Math.random() * 10000)}`,
    description: `${randomName}에 대한 상세 설명입니다. 품질이 좋고 가격도 합리적입니다. ID: ${Math.random().toString(36).substring(2, 10)}`,
    price: Math.floor(Math.random() * 1000000) + 1000,
    tax: Math.floor(Math.random() * 100000),
  };
}

// 임의의 사용자 데이터 생성
function generateRandomUser() {
  const randomId = Math.floor(Math.random() * 100000);
  return {
    username: `user${randomId}`,
    email: `user${randomId}@example.com`,
    full_name: `테스트 사용자 ${randomId}`,
  };
}

// 메인 테스트 함수
export default function () {
  // VU(가상 사용자) ID 기반으로 다양한 시나리오 실행
  // 짝수 VU는 아이템 관련 작업, 홀수 VU는 사용자 관련 작업 수행
  const vuId = __VU % 2;
  
  // 1. 모든 VU는 기본 상태 체크 수행
  group('서버 상태 확인', () => {
    const res = http.get(`${BASE_URL}/`);
    const success = check(res, {
      'Root API is working': (r) => r.status === 200,
    });
    
    if (success) {
      successfulRequests.add(1);
    } else {
      errorRate.add(1);
    }
  });
  
  // 짧은 휴식
  sleep(Math.random() * 2);
  
  if (vuId === 0) {
    // 짝수 VU: 아이템 관련 작업
    group('아이템 작업', () => {
      // 아이템 목록 조회
      let res = http.get(`${BASE_URL}/items`);
      check(res, {
        'Get items successful': (r) => r.status === 200,
      });
      
      // 새 아이템 생성
      const newItem = generateRandomItem();
      const startTime = new Date();
      res = http.post(`${BASE_URL}/items`, JSON.stringify(newItem), {
        headers: { 'Content-Type': 'application/json' },
      });
      const endTime = new Date();
      
      // 아이템 생성 시간 측정
      itemCreationTrend.add(endTime - startTime);
      
      const success = check(res, {
        'Create item successful': (r) => r.status === 201,
      });
      
      if (success) {
        successfulRequests.add(1);
        
        // 생성된 아이템 조회
        const itemId = res.json().id;
        res = http.get(`${BASE_URL}/items/${itemId}`);
        check(res, {
          'Get created item successful': (r) => r.status === 200,
          'Item data is correct': (r) => r.json().name === newItem.name,
        });
      } else {
        errorRate.add(1);
      }
      
      // 서버 통계 확인
      res = http.get(`${BASE_URL}/stats`);
      check(res, {
        'Stats API is working': (r) => r.status === 200,
      });
    });
  } else {
    // 홀수 VU: 사용자 관련 작업
    group('사용자 작업', () => {
      // 새 사용자 생성
      const newUser = generateRandomUser();
      const startTime = new Date();
      let res = http.post(`${BASE_URL}/users`, JSON.stringify(newUser), {
        headers: { 'Content-Type': 'application/json' },
      });
      const endTime = new Date();
      
      // 사용자 생성 시간 측정
      userCreationTrend.add(endTime - startTime);
      
      const success = check(res, {
        'Create user successful': (r) => r.status === 201,
      });
      
      if (success) {
        successfulRequests.add(1);
        
        // 생성된 사용자 조회 (지연 발생 API)
        const username = res.json().username;
        const slowStartTime = new Date();
        res = http.get(`${BASE_URL}/users/${username}`);
        const slowEndTime = new Date();
        
        // 느린 엔드포인트 응답 시간 측정
        slowEndpointTrend.add(slowEndTime - slowStartTime);
        
        check(res, {
          'Get user successful': (r) => r.status === 200,
          'User data is correct': (r) => r.json().username === newUser.username,
        });
      } else {
        errorRate.add(1);
      }
    });
  }
  
  // 랜덤 휴식
  sleep(Math.random() * 3 + 1);
} 