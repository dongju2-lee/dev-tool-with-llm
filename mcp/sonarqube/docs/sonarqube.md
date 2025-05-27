Q). sonarqube 는 github 에 연동하려면 로컬에서 띄우면 안되나요? public 접근이 되어야 하나요?

A). SonarQube를 GitHub에 연동할 때 두 가지 방식이 있습니다:

1. **GitHub 웹훅 방식 (Pull Request 분석 등)**: 이 경우 GitHub에서 SonarQube 서버에 접근할 수 있어야 하므로, SonarQube 서버는 인터넷에서 접근 가능한 공개 URL(public)이 필요합니다. 로컬에서 실행하는 경우 ngrok 같은 도구로 터널링이 필요합니다.

2. **CI/CD 통합 방식**: GitHub Actions나 Jenkins 등 CI/CD 도구를 통해 SonarQube 스캔을 실행하는 경우, SonarQube 서버는 CI/CD 환경에서 접근 가능하면 됩니다. 이 방식에서는 로컬 서버도 가능하지만, 팀 개발 환경에서는 모든 개발자와 CI 서버가 접근 가능한 곳에 설치하는 것이 좋습니다.

Community Edition을 사용하는 경우, 주로 CI/CD 통합 방식이 추천됩니다.

Q). sonarqube 를 github 에 연동하려면 어디에 띄워야 하나요? 추천해 주세요.

A). SonarQube 서버를 GitHub과 연동하기 위한 추천 배포 옵션:

1. **팀 개발용 서버**:
   - 내부 네트워크의 전용 서버나 VM
   - 모든 개발자가 접근할 수 있는 환경
   - 작은 팀의 경우 적합한 옵션

2. **클라우드 환경**:
   - AWS, GCP, Azure 등의 가상 머신
   - 퍼블릭 IP와 도메인 설정
   - 중간 규모 이상의 팀에 적합
   - 확장성 및 관리 용이성 제공

3. **Docker 컨테이너**:
   - Docker Compose나 Kubernetes를 통한 배포
   - 환경 일관성 및 쉬운 업그레이드
   - 개발/테스트/운영 환경 간 일관성 유지

4. **SaaS 서비스 (대안)**:
   - SonarCloud(공식 SaaS 서비스)가 자체 호스팅의 번거로움 없이 GitHub 연동 지원
   - 무료 플랜은 오픈소스 프로젝트에 제공
   - 상용 프로젝트는 유료 구독 필요

GitHub Actions를 사용한다면, SonarCloud 사용을 고려해 보는 것도 좋은 선택입니다.

Q). 띄우고 github 에 연동하는 방법을 설명해 주세요.

A). SonarQube를 설치하고 GitHub과 연동하는 단계별 가이드:

### 1. SonarQube 설치 및 설정

**Docker를 이용한 설치 (권장)**:
```bash
# docker-compose.yml 파일 생성
cat > docker-compose.yml << EOF
version: "3"
services:
  sonarqube:
    image: sonarqube:community
    ports:
      - "9000:9000"
    environment:
      - SONAR_JDBC_URL=jdbc:postgresql://db:5432/sonar
      - SONAR_JDBC_USERNAME=sonar
      - SONAR_JDBC_PASSWORD=sonar
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_extensions:/opt/sonarqube/extensions
      - sonarqube_logs:/opt/sonarqube/logs
    depends_on:
      - db
  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=sonar
      - POSTGRES_PASSWORD=sonar
      - POSTGRES_DB=sonar
    volumes:
      - postgresql:/var/lib/postgresql
      - postgresql_data:/var/lib/postgresql/data

volumes:
  sonarqube_data:
  sonarqube_extensions:
  sonarqube_logs:
  postgresql:
  postgresql_data:
EOF

# 실행
docker-compose up -d
```

### 2. 초기 설정

1. 브라우저에서 `http://[서버IP]:9000` 접속 (초기 계정: admin/admin)
2. 관리자 패스워드 변경
3. 프로젝트 생성:
   - "Projects" → "Create Project" → "Manually"
   - 프로젝트 키와 이름 입력
   - 토큰 생성 (이 토큰을 저장해두세요)

### 3. GitHub Actions와 연동 (CI/CD 방식)

1. GitHub 저장소에 `.github/workflows/sonarqube.yml` 파일 생성:

```yaml
name: SonarQube Analysis
on:
  push:
    branches:
      - main
  pull_request:
    types: [opened, synchronize, reopened]
jobs:
  sonarqube:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0
    - name: SonarQube Scan
      uses: SonarSource/sonarqube-scan-action@master
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
```

2. GitHub 저장소 설정에 시크릿 추가:
   - Settings → Secrets and variables → Actions
   - `SONAR_TOKEN`: SonarQube에서 생성한 토큰
   - `SONAR_HOST_URL`: SonarQube 서버 URL (예: http://sonarqube-server:9000)

3. 프로젝트 루트에 `sonar-project.properties` 파일 생성:

```properties
sonar.projectKey=my-project
sonar.projectName=My Project
sonar.sources=.
# 테스트 코드 제외
sonar.exclusions=**/*test*/**
# 테스트 커버리지 리포트 경로 (옵션)
# sonar.javascript.lcov.reportPaths=coverage/lcov.info
# sonar.java.binaries=target/classes
```

### 4. 결과 확인

- 워크플로우가 실행된 후 SonarQube 대시보드에서 분석 결과 확인
- 코드 품질, 버그, 취약점, 중복 코드 등의 지표 확인
- 품질 게이트 통과 여부 확인

### 추가 설정 (선택사항)

- **Webhooks 설정 (PR 분석용)**:
  1. SonarQube 프로젝트 → Administration → Webhooks → Create
  2. GitHub 저장소의 이벤트를 수신할 URL 설정
  
- **GitHub PR 데코레이션 (Developer Edition 이상)**:
  1. SonarQube → Administration → GitHub → 연동 설정
  2. GitHub App 생성 및 연결
  
위 가이드는 Community Edition 기준이며, 고급 기능(PR 데코레이션 등)은 Developer Edition 이상에서 가능합니다. Community Edition에서는 CI/CD 통합과 기본 분석 기능에 집중하는 것이 좋습니다.
