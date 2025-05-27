# Grafana Dashboard API 문서

Grafana Dashboard API는 대시보드와 패널을 관리하고 데이터를 쿼리하기 위한 다양한 엔드포인트를 제공합니다. 이 문서는 주요 API 엔드포인트와 사용 방법을 설명합니다.

## 대시보드 API 엔드포인트

### 대시보드 목록 조회

```
GET /api/dashboards
GET /api/search
```

대시보드 목록을 검색하고 조회합니다. 다양한 필터링 옵션을 지원합니다.

#### 매개변수
- **query**: 검색 쿼리 텍스트
- **tag**: 태그 기반 필터링
- **type**: 대시보드 또는 폴더 유형 필터링
- **folder**: 특정 폴더 내 대시보드 검색
- **limit**: 반환할 최대 결과 수

### 단일 대시보드 조회

```
GET /api/dashboards/uid/:uid
```

UID를 기반으로 단일 대시보드의 전체 정보를 조회합니다.

### 대시보드 생성/업데이트

```
POST /api/dashboards/db
```

새 대시보드를 생성하거나 기존 대시보드를 업데이트합니다.

### 대시보드 삭제

```
DELETE /api/dashboards/uid/:uid
```

특정 UID를 가진 대시보드를 삭제합니다.

## 패널 관련 API

Grafana의 패널은 대시보드 JSON 모델의 일부로 관리됩니다. 개별 패널을 직접 관리하는 API는 없지만, 대시보드 API를 통해 패널을 포함한 전체 대시보드를 관리할 수 있습니다.

### 대시보드 내 패널 유형

Grafana는 다음과 같은 다양한 패널 유형을 지원합니다:

- **Time series**: 시계열 데이터 시각화
- **Bar chart**: 바 차트 시각화
- **Stat**: 단일 통계 값 표시
- **Gauge**: 게이지 형태로 값 표시
- **Heatmap**: 히트맵 시각화
- **Table**: 테이블 형태로 데이터 표시
- **Pie chart**: 파이 차트 시각화
- 그 외 다양한 패널 유형들

## 대시보드 데이터 쿼리 API

```
POST /api/ds/query
```

이 API는 데이터 소스에서 데이터를 쿼리하기 위해 사용됩니다. 대시보드의 패널은 내부적으로 이 API를 사용하여 시각화할 데이터를 가져옵니다.

### 요청 본문 예시 (Prometheus)

```json
{
  "queries": [
    {
      "refId": "A",
      "datasource": {
        "uid": "prometheus-uid"
      },
      "expr": "up",
      "format": "time_series"
    }
  ],
  "from": "now-1h",
  "to": "now"
}
```

## 대시보드 버전 관리 API

```
GET /api/dashboards/uid/:uid/versions
GET /api/dashboards/uid/:uid/versions/:id
POST /api/dashboards/uid/:uid/restore
```

대시보드의 버전 기록을 관리하고 이전 버전으로 복원할 수 있는 API를 제공합니다.

## 대시보드 권한 API

```
GET /api/dashboards/uid/:uid/permissions
POST /api/dashboards/uid/:uid/permissions
```

대시보드의 권한을 조회하고 설정할 수 있는 API를 제공합니다.

## 대시보드 태그 API

```
GET /api/dashboards/tags
```

대시보드에서 사용 중인 모든 태그 목록을 반환합니다.

## 대시보드 프로비저닝 API

Grafana는 YAML 파일을 통한 대시보드 프로비저닝을 지원합니다. 프로비저닝된 대시보드는 API를 통해 직접 수정할 수 없으며, 소스 파일을 수정하여 업데이트해야 합니다.

## 사용 예시

### cURL을 사용한 대시보드 목록 조회

```bash
curl -H "Authorization: Bearer API_KEY" http://your-grafana-instance/api/search
```

### cURL을 사용한 단일 대시보드 조회

```bash
curl -H "Authorization: Bearer API_KEY" http://your-grafana-instance/api/dashboards/uid/dashboard-uid
```

## 참고 사항

- 모든 API 요청에는 적절한 인증이 필요합니다 (API 키 또는 Bearer 토큰).
- API 응답은 기본적으로 JSON 형식으로 반환됩니다.
- 대시보드 JSON 모델은 복잡할 수 있으므로, Grafana UI를 통해 대시보드를 생성한 후 API를 통해 해당 모델을 조회하여 참고하는 것이 좋습니다.
