# Grafana Renderer API 문서

Grafana의 이미지 렌더링 API는 대시보드 및 패널을 이미지로 렌더링하는 기능을 제공합니다. 이 문서는 렌더링 서비스에서 제공하는 API 엔드포인트와 사용 방법을 설명합니다.

## 렌더링 API 엔드포인트

### 대시보드 렌더링

```
GET /render/dashboard/db/:dashboardName
```

전체 대시보드를 PNG 이미지로 렌더링합니다.

#### 매개변수
- **from**: 시작 시간 (Unix 타임스탬프 또는 상대 시간, 예: `now-24h`)
- **to**: 종료 시간 (Unix 타임스탬프 또는 상대 시간, 예: `now`)
- **width**: 이미지 너비 (픽셀 단위)
- **height**: 이미지 높이 (픽셀 단위)
- **orgId**: 조직 ID

### 패널 렌더링

```
GET /render/dashboard-solo/db/:dashboardName
```

대시보드에서 특정 패널만 PNG 이미지로 렌더링합니다.

#### 매개변수
- **from**: 시작 시간 (Unix 타임스탬프 또는 상대 시간)
- **to**: 종료 시간 (Unix 타임스탬프 또는 상대 시간)
- **panelId**: 렌더링할 패널의 ID
- **width**: 이미지 너비 (픽셀 단위, 기본값: 800)
- **height**: 이미지 높이 (픽셀 단위, 기본값: 400)
- **tz**: 타임존 (형식: `UTC%2BHH%3AMM`, HH와 MM은 UTC 이후 시간과 분 단위 오프셋)
- **timeout**: 시간 초과 (초 단위, 기본값: 30초)
- **scale**: 장치 스케일 팩터 (기본값: 1, 고해상도 이미지는 2 또는 4)

### 버전 정보

```
GET /render/version
```

현재 실행 중인 Grafana 렌더링 서비스의 버전 정보를 반환합니다.

## 인증

렌더링 API는 다음 인증 방법을 지원합니다:

1. **API 키**: 요청 헤더에 `Authorization: Bearer <api_key>` 포함
2. **기본 인증**: HTTP 기본 인증 헤더 사용 (사용자 이름:비밀번호)
3. **보안 토큰**: v3.6.1 이상에서는 보안 토큰을 설정하여 렌더링 엔드포인트에 대한 접근을 제한할 수 있습니다.

## 사용 예시

### cURL을 사용한 패널 렌더링

```bash
curl "http://admin:admin@grafana.example.com/render/dashboard-solo/db/my-dashboard?orgId=1&panelId=4&from=1495998275442&to=1498590275443&width=1000&height=500" > panel.png
```

### 대시보드 렌더링 및 저장

```bash
curl "http://grafana.example.com/render/dashboard/db/production-overview?orgId=1&from=now-24h&to=now&width=1200&height=800&timeout=60" --header "Authorization: Bearer eyJrIjoiT0tTcG1pUlY2RnVKZT..." > dashboard.png
```

## 고려 사항

1. 이미지 렌더링에는 상당한 메모리가 필요합니다. 최소 16GB의 여유 메모리가 권장됩니다.
2. 여러 이미지를 동시에 렌더링하면 더 많은 메모리가 필요합니다.
3. 타임아웃 값은 쿼리가 복잡한 경우 증가시킬 수 있습니다.
4. 스케일 값을 높이면 더 상세한 이미지를 생성할 수 있지만 성능과 메모리 사용량에 영향을 미칩니다.
5. 렌더링 서비스는 Chromium 브라우저를 사용하여 이미지를 생성합니다.

## 문제 해결

렌더링 API 호출 시 다음과 같은, 일반적인 문제가 발생할 수 있습니다:

- **404 Not Found**: 대시보드 또는 패널을 찾을 수 없습니다.
- **500 Internal Server Error**: 서버 측 오류가 발생했습니다.
- **504 Gateway Timeout**: 지정된 제한 시간 내에 이미지를 렌더링할 수 없습니다.

문제가 지속되면 Grafana 로그를 확인하거나 렌더링 서비스의 상세 로깅을 활성화하세요.

## 참고 자료

- [Grafana 이미지 렌더링 공식 문서](https://grafana.com/docs/grafana/latest/setup-grafana/image-rendering/)
- [Grafana 이미지 렌더링 플러그인](https://grafana.com/grafana/plugins/grafana-image-renderer/)
