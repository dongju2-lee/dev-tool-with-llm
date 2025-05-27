# MCP 통합을 위한 SonarQube API (Community Edition)

SonarQube Community Edition은 코드 품질 인사이트를 제공하기 위해 MCP와 통합할 수 있는 REST API를 제공합니다. 아래는 오픈소스 버전에서 사용 가능한 5가지 핵심 API입니다.

## 1. 프로젝트 품질 게이트 상태 조회

특정 프로젝트의 품질 게이트 상태를 검색하여 사용자가 프로젝트가 품질 기준을 통과하는지 빠르게 확인할 수 있습니다.

**엔드포인트:** `GET /api/qualitygates/project_status`

**매개변수:**
- `projectKey` (필수): 프로젝트 키 식별자
- `branch` (선택): 브랜치 이름 (참고: Community Edition에서는 단일 브랜치만 지원)

**사용 예:**
```python
def get_quality_gate_status(project_key):
    """특정 프로젝트의 품질 게이트 상태를 조회합니다."""
    params = {'projectKey': project_key}
    
    response = requests.get(f"{sonar_url}/api/qualitygates/project_status", 
                           params=params, 
                           auth=(sonar_token, ''))
    
    if response.status_code == 200:
        return response.json()['projectStatus']
    else:
        raise Exception(f"품질 게이트 상태 조회 오류: {response.text}")
```

## 2. 프로젝트 이슈 조회

프로젝트의 이슈(버그, 취약점, 코드 스멜) 목록을 검색하여 사용자가 코드의 특정 문제를 이해할 수 있도록 합니다.

**엔드포인트:** `GET /api/issues/search`

**매개변수:**
- `componentKeys` (필수): 프로젝트 키
- `types` (선택): 이슈 유형 (BUG, VULNERABILITY, CODE_SMELL)
- `severities` (선택): 이슈 심각도 (BLOCKER, CRITICAL, MAJOR, MINOR, INFO)
- `statuses` (선택): 이슈 상태 (OPEN, CONFIRMED, RESOLVED, CLOSED)
- `ps` (선택): 페이지 크기 (기본값 100)
- `p` (선택): 페이지 번호 (페이지네이션)

**사용 예:**
```python
def get_project_issues(project_key, issue_types=None, severities=None, max_results=10):
    """선택적 필터링을 통해 프로젝트의 이슈를 조회합니다."""
    params = {
        'componentKeys': project_key,
        'ps': max_results
    }
    
    if issue_types:
        params['types'] = ','.join(issue_types)
    if severities:
        params['severities'] = ','.join(severities)
    
    response = requests.get(f"{sonar_url}/api/issues/search", 
                           params=params, 
                           auth=(sonar_token, ''))
    
    if response.status_code == 200:
        return response.json()['issues']
    else:
        raise Exception(f"이슈 조회 오류: {response.text}")
```

## 3. 프로젝트 메트릭 조회

프로젝트의 특정 메트릭 값(예: 코드 커버리지, 중복, 복잡성)을 가져와 코드 품질에 대한 정량적 인사이트를 제공합니다.

**엔드포인트:** `GET /api/measures/component`

**매개변수:**
- `component` (필수): 프로젝트 키
- `metricKeys` (필수): 조회할 메트릭의 쉼표로 구분된 목록

**사용 예:**
```python
def get_project_metrics(project_key, metrics):
    """프로젝트의 특정 메트릭을 조회합니다."""
    params = {
        'component': project_key,
        'metricKeys': ','.join(metrics)
    }
    
    response = requests.get(f"{sonar_url}/api/measures/component", 
                           params=params, 
                           auth=(sonar_token, ''))
    
    if response.status_code == 200:
        return response.json()['component']['measures']
    else:
        raise Exception(f"메트릭 조회 오류: {response.text}")
```

## 4. 프로젝트 구성요소 조회

프로젝트의 파일, 디렉토리, 모듈과 같은 구성요소를 조회하여 코드베이스 구조를 이해하는 데 도움이 됩니다.

**엔드포인트:** `GET /api/components/tree`

**매개변수:**
- `component` (필수): 프로젝트 키
- `qualifiers` (선택): 구성요소 유형 (DIR, FIL, UTS 등)
- `p` (선택): 페이지 번호
- `ps` (선택): 페이지 크기

**사용 예:**
```python
def get_project_components(project_key, qualifiers=None, page_size=100):
    """프로젝트의 구성요소를 조회합니다."""
    params = {
        'component': project_key,
        'ps': page_size
    }
    
    if qualifiers:
        params['qualifiers'] = ','.join(qualifiers)
    
    response = requests.get(f"{sonar_url}/api/components/tree", 
                           params=params, 
                           auth=(sonar_token, ''))
    
    if response.status_code == 200:
        return response.json()['components']
    else:
        raise Exception(f"구성요소 조회 오류: {response.text}")
```

## 5. 프로젝트 규칙 조회

SonarQube에서 사용 중인 규칙 목록을 조회하여 품질 규칙에 대한 이해를 돕습니다.

**엔드포인트:** `GET /api/rules/search`

**매개변수:**
- `languages` (선택): 특정 언어로 규칙 필터링 (java, js, py 등)
- `severities` (선택): 심각도로 필터링
- `ps` (선택): 페이지 크기
- `p` (선택): 페이지 번호

**사용 예:**
```python
def get_rules(languages=None, severities=None, max_results=50):
    """SonarQube 규칙을 조회합니다."""
    params = {'ps': max_results}
    
    if languages:
        params['languages'] = ','.join(languages)
    if severities:
        params['severities'] = ','.join(severities)
    
    response = requests.get(f"{sonar_url}/api/rules/search", 
                           params=params, 
                           auth=(sonar_token, ''))
    
    if response.status_code == 200:
        return response.json()['rules']
    else:
        raise Exception(f"규칙 조회 오류: {response.text}")
```

## 6. 취약점 분석 실행 방법

SonarQube Community Edition에서는 직접적인 분석 실행을 위한 RESTful API를 제한적으로 제공합니다. 프로젝트 분석은 주로 SonarScanner 도구를 통해 수행됩니다. 하지만 MCP 통합에서는 다음과 같은 방식으로 분석을 실행할 수 있습니다:

### 6.1 SonarScanner 명령 실행

**방법:** 서버에서 SonarScanner 명령을 프로그래밍 방식으로 실행하고 결과를 모니터링합니다.

**사용 예:**
```python
def run_sonar_analysis(project_key, project_path, additional_properties=None):
    """SonarScanner를 사용하여 프로젝트 분석을 실행합니다."""
    # 기본 명령 생성
    command = f"sonar-scanner -Dsonar.projectKey={project_key}"
    
    # 추가 속성 적용
    if additional_properties:
        for key, value in additional_properties.items():
            command += f" -D{key}={value}"
    
    # 현재 디렉토리 저장
    current_dir = os.getcwd()
    
    try:
        # 프로젝트 디렉토리로 이동
        os.chdir(project_path)
        
        # 명령 실행
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 결과 수집
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"SonarScanner 실행 오류: {stderr}")
        
        return {
            "status": "success",
            "output": stdout
        }
        
    finally:
        # 원래 디렉토리로 복귀
        os.chdir(current_dir)
```

### 6.2 분석 완료 상태 확인

SonarScanner를 실행한 후 분석 상태를 확인하기 위해 웹훅 또는 폴링 방식으로 상태를 체크할 수 있습니다.

**엔드포인트:** `GET /api/ce/activity`

**매개변수:**
- `component` (선택): 프로젝트 키로 필터링
- `status` (선택): 상태로 필터링 (SUCCESS, FAILED, CANCELED, IN_PROGRESS)

**사용 예:**
```python
def check_analysis_status(project_key):
    """프로젝트 분석 상태를 확인합니다."""
    params = {
        'component': project_key,
        'ps': 1  # 최신 분석 1개만 조회
    }
    
    response = requests.get(f"{sonar_url}/api/ce/activity", 
                           params=params, 
                           auth=(sonar_token, ''))
    
    if response.status_code == 200:
        tasks = response.json().get('tasks', [])
        if tasks:
            return {
                "id": tasks[0].get('id'),
                "status": tasks[0].get('status'),
                "submittedAt": tasks[0].get('submittedAt'),
                "executedAt": tasks[0].get('executedAt')
            }
        else:
            return {"status": "NO_ACTIVITY"}
    else:
        raise Exception(f"분석 상태 조회 오류: {response.text}")
```

### 6.3 취약점 분석 결과 요약

분석이 완료된 후, 특히 보안 취약점 관련 결과를 요약하는 데 사용할 수 있습니다.

**사용 예:**
```python
def get_vulnerability_summary(project_key):
    """프로젝트의 취약점 분석 결과를 요약합니다."""
    # 취약점 수 조회
    metrics = get_project_metrics(project_key, ["vulnerabilities", "security_rating"])
    
    # 취약점 상세 내용 조회
    vulnerabilities = get_project_issues(
        project_key, 
        issue_types=["VULNERABILITY"],
        max_results=100
    )
    
    # 심각도별 분류
    severity_counts = {}
    for vuln in vulnerabilities:
        severity = vuln.get('severity', 'UNKNOWN')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    return {
        "total_vulnerabilities": len(vulnerabilities),
        "security_rating": next((m.get('value') for m in metrics if m.get('metric') == 'security_rating'), None),
        "severity_distribution": severity_counts,
        "vulnerabilities": vulnerabilities
    }
```

## MCP 통합 고려사항

SonarQube Community Edition API를 MCP와 통합할 때 고려할 사항:

1. **인증 처리**: SonarQube 토큰을 안전하게 저장하고 인증 관리
2. **응답 형식 변환**: JSON 응답을 사용자 친화적인 형식으로 변환
3. **오류 처리**: API 실패에 대한 명확한 오류 메시지 제공
4. **기능 제한 인식**: Community Edition에서는 다중 브랜치 분석, 풀 리퀘스트 분석, 보안 핫스팟과 같은 일부 고급 기능이 제한됨
5. **컨텍스트 인식**: 도구가 관련 추천을 위해 프로젝트 컨텍스트를 이해할 수 있도록 지원
6. **분석 자동화**: SonarScanner를 프로그래밍 방식으로 실행하는 래퍼 함수 구현

## Community Edition 참고사항

SonarQube Community Edition에서는 다음 기능을 사용할 수 없습니다:
- 브랜치 분석 (단일 브랜치만 지원)
- 풀 리퀘스트 분석
- 포트폴리오 및 애플리케이션 관리
- 코드 보안 핫스팟
- 고급 보고서
- 고급 권한 관리
- 직접적인 분석 트리거 API (Developer Edition 이상에서 제공)
