#!/usr/bin/env python3
"""
Loki & Tempo MCP 서버 실행 스크립트
"""
import os
import sys
import subprocess
import signal
import time

# 현재 스크립트의 디렉토리 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def check_requirements():
    """필요한 패키지가 설치되어 있는지 확인"""
    try:
        import fastmcp
        import requests
        import dotenv  # python_dotenv가 아니라 dotenv로 import
        print("✅ 필요한 패키지가 모두 설치되어 있습니다.")
        return True
    except ImportError as e:
        print(f"❌ 필요한 패키지가 설치되지 않았습니다: {e}")
        print("다음 명령어로 설치하세요:")
        print(f"pip install -r {os.path.join(SCRIPT_DIR, 'requirements.txt')}")
        return False

def check_env_file():
    """환경 설정 파일 확인"""
    env_file = os.path.join(SCRIPT_DIR, '.env')
    env_template = os.path.join(SCRIPT_DIR, '.env.template')
    
    if not os.path.exists(env_file):
        if os.path.exists(env_template):
            print(f"❌ .env 파일이 없습니다.")
            print(f"📋 {env_template} 파일을 참고하여 .env 파일을 생성하세요.")
            print(f"   cp {env_template} {env_file}")
        else:
            print("❌ 환경 설정 파일이 없습니다.")
            print("📋 다음 내용으로 .env 파일을 생성하세요:")
            print("""
# Loki & Tempo MCP Server 환경 설정

# Loki 설정
LOKI_URL=http://localhost:3100
LOKI_AUTH_USER=
LOKI_AUTH_PASSWORD=

# Tempo 설정
TEMPO_URL=http://localhost:3200
TEMPO_AUTH_USER=
TEMPO_AUTH_PASSWORD=

# Grafana 설정
GRAFANA_URL=http://localhost:3000
LOKI_DASHBOARD_ID=
TEMPO_DASHBOARD_ID=

# MCP 서버 설정
MCP_HOST=0.0.0.0
MCP_PORT=10002

# 기본값 설정
DEFAULT_LOG_LIMIT=100
DEFAULT_TRACE_LIMIT=20
DEFAULT_TIME_RANGE=1h
            """)
        return False
    
    print("✅ .env 파일이 존재합니다.")
    return True

def check_services():
    """Loki와 Tempo 서비스 상태 확인"""
    import requests
    from dotenv import load_dotenv
    
    # .env 파일 로드
    env_file = os.path.join(SCRIPT_DIR, '.env')
    load_dotenv(env_file)
    
    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    tempo_url = os.getenv("TEMPO_URL", "http://localhost:3200")
    
    print("\n📡 서비스 연결 확인 중...")
    
    # Loki 확인
    try:
        response = requests.get(f"{loki_url}/ready", timeout=5)
        if response.status_code == 200:
            print(f"✅ Loki 서비스가 실행 중입니다: {loki_url}")
        else:
            print(f"⚠️  Loki 서비스가 준비되지 않았습니다: {response.status_code}")
    except Exception as e:
        print(f"❌ Loki 서비스에 연결할 수 없습니다: {loki_url}")
        print(f"   오류: {str(e)}")
        print("   Docker Compose로 Loki를 시작하세요:")
        print("   docker-compose up -d loki")
    
    # Tempo 확인
    try:
        response = requests.get(f"{tempo_url}/status", timeout=5)
        if response.status_code == 200:
            print(f"✅ Tempo 서비스가 실행 중입니다: {tempo_url}")
        else:
            print(f"⚠️  Tempo 서비스가 준비되지 않았습니다: {response.status_code}")
    except Exception as e:
        print(f"❌ Tempo 서비스에 연결할 수 없습니다: {tempo_url}")
        print(f"   오류: {str(e)}")
        print("   Docker Compose로 Tempo를 시작하세요:")
        print("   docker-compose up -d tempo")

def run_server():
    """MCP 서버 실행"""
    server_script = os.path.join(SCRIPT_DIR, 'loki_tempo_mcp_server.py')
    
    if not os.path.exists(server_script):
        print(f"❌ 서버 스크립트를 찾을 수 없습니다: {server_script}")
        return False
    
    print("\n🚀 Loki & Tempo MCP 서버를 시작합니다...")
    print(f"📁 작업 디렉토리: {SCRIPT_DIR}")
    print(f"🔧 서버 스크립트: {server_script}")
    
    # 작업 디렉토리를 스크립트 디렉토리로 변경
    os.chdir(SCRIPT_DIR)
    
    try:
        # 서버 실행
        process = subprocess.Popen([
            sys.executable, server_script
        ], cwd=SCRIPT_DIR)
        
        print(f"🆔 프로세스 ID: {process.pid}")
        print("📡 서버가 실행 중입니다. Ctrl+C로 종료할 수 있습니다.")
        print("\n💡 MCP 클라이언트 설정:")
        print("   {")
        print('     "mcpServers": {')
        print('       "loki-tempo": {')
        print('         "command": "python",')
        print(f'         "args": ["{server_script}"],')
        print('         "env": {')
        print('           "LOKI_URL": "http://localhost:3100",')
        print('           "TEMPO_URL": "http://localhost:3200"')
        print('         }')
        print('       }')
        print('     }')
        print('   }')
        
        # 시그널 핸들러 등록
        def signal_handler(signum, frame):
            print("\n\n🛑 서버 종료 요청을 받았습니다...")
            process.terminate()
            try:
                process.wait(timeout=5)
                print("✅ 서버가 정상적으로 종료되었습니다.")
            except subprocess.TimeoutExpired:
                print("⚠️  강제 종료합니다...")
                process.kill()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 프로세스 대기
        process.wait()
        
    except Exception as e:
        print(f"❌ 서버 실행 중 오류 발생: {e}")
        return False
    
    return True

def main():
    """메인 함수"""
    print("=" * 50)
    print("🔍 Loki & Tempo MCP Server")
    print("=" * 50)
    
    # 사전 점검
    if not check_requirements():
        sys.exit(1)
    
    if not check_env_file():
        sys.exit(1)
    
    # 서비스 상태 확인 (선택사항)
    try:
        check_services()
    except Exception as e:
        print(f"\n⚠️  서비스 확인 중 오류 발생: {e}")
        print("   서비스가 실행되지 않아도 MCP 서버는 시작됩니다.")
    
    # 서버 실행
    if not run_server():
        sys.exit(1)

if __name__ == "__main__":
    main()