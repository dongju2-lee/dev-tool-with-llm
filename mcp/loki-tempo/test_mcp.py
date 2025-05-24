#!/usr/bin/env python3
"""
Loki & Tempo MCP 서버 테스트 스크립트
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta

# MCP 클라이언트 임포트
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:
    print("❌ langchain-mcp-adapters 패키지가 설치되지 않았습니다.")
    print("다음 명령어로 설치하세요: pip install langchain-mcp-adapters")
    sys.exit(1)

# MCP 서버 설정 - 다른 MCP 서버들과 동일하게 SSE transport 사용
MCP_SERVERS = {
    "loki_tempo": {
        "url": "http://localhost:10002/sse",
        "transport": "sse",
    }
}

async def test_connection():
    """MCP 서버 연결 테스트"""
    print("🔗 MCP 서버 연결 테스트...")
    try:
        client = MultiServerMCPClient(MCP_SERVERS)
        print("✅ MCP 클라이언트 생성 성공")
        return client
    except Exception as e:
        print(f"❌ MCP 서버 연결 실패: {e}")
        return None

async def test_get_tools(client):
    """도구 목록 가져오기 테스트"""
    print("\n🛠️ 사용 가능한 도구 확인...")
    try:
        tools = client.get_tools()
        print(f"✅ 총 {len(tools)}개의 도구를 발견했습니다:")
        
        for i, tool in enumerate(tools, 1):
            name = getattr(tool, 'name', 'Unknown')
            description = getattr(tool, 'description', '설명 없음')
            print(f"  {i}. {name}: {description[:80]}...")
        
        return tools
    except Exception as e:
        print(f"❌ 도구 목록 가져오기 실패: {e}")
        return []

async def test_environment_check(client):
    """환경 설정 확인 테스트"""
    print("\n🔧 환경 설정 확인...")
    try:
        # check_environment 도구 찾기
        tools = client.get_tools()
        check_env_tool = None
        
        for tool in tools:
            if getattr(tool, 'name', '') == 'check_environment':
                check_env_tool = tool
                break
        
        if not check_env_tool:
            print("❌ check_environment 도구를 찾을 수 없습니다.")
            print("📋 사용 가능한 도구:")
            for tool in tools:
                print(f"  - {getattr(tool, 'name', 'Unknown')}")
            return False
        
        # 도구 실행
        result = await check_env_tool.ainvoke({})
        print("✅ 환경 설정 확인 성공:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True
        
    except Exception as e:
        print(f"❌ 환경 설정 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_logs(client):
    """로그 쿼리 테스트"""
    print("\n📝 로그 쿼리 테스트...")
    try:
        tools = client.get_tools()
        query_logs_tool = None
        
        for tool in tools:
            if getattr(tool, 'name', '') == 'query_logs':
                query_logs_tool = tool
                break
        
        if not query_logs_tool:
            print("❌ query_logs 도구를 찾을 수 없습니다.")
            return False
        
        # 간단한 로그 쿼리 실행
        result = await query_logs_tool.ainvoke({
            "query": "{}",  # 모든 로그
            "time_range": "1h",
            "limit": 10
        })
        
        print("✅ 로그 쿼리 성공:")
        if isinstance(result, dict):
            log_count = result.get('log_count', 0)
            print(f"  📊 조회된 로그 수: {log_count}")
            if log_count > 0:
                logs = result.get('logs', [])
                if logs:
                    first_log = logs[0]
                    if isinstance(first_log, dict):
                        print(f"  📋 첫 번째 로그: {first_log.get('log', first_log.get('message', ''))[:100]}...")
        else:
            print(f"  📄 결과: {str(result)[:200]}...")
            
        return True
        
    except Exception as e:
        print(f"❌ 로그 쿼리 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_search_traces(client):
    """트레이스 검색 테스트"""
    print("\n🔍 트레이스 검색 테스트...")
    try:
        tools = client.get_tools()
        search_traces_tool = None
        
        for tool in tools:
            if getattr(tool, 'name', '') == 'search_traces':
                search_traces_tool = tool
                break
        
        if not search_traces_tool:
            print("❌ search_traces 도구를 찾을 수 없습니다.")
            return False
        
        # 트레이스 검색 실행
        result = await search_traces_tool.ainvoke({
            "time_range": "1h",
            "limit": 5
        })
        
        print("✅ 트레이스 검색 성공:")
        if isinstance(result, dict):
            trace_count = result.get('trace_count', 0)
            print(f"  📊 발견된 트레이스 수: {trace_count}")
            if trace_count > 0:
                traces = result.get('traces', [])
                if traces:
                    first_trace = traces[0]
                    print(f"  🔗 첫 번째 트레이스 ID: {first_trace.get('trace_id', 'N/A')}")
                    print(f"  🏢 서비스: {first_trace.get('root_service', 'N/A')}")
        else:
            print(f"  📄 결과: {str(result)[:200]}...")
            
        return True
        
    except Exception as e:
        print(f"❌ 트레이스 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_test_tool(client):
    """간단한 테스트 도구 실행"""
    print("\n🧪 기본 테스트 도구 실행...")
    try:
        tools = client.get_tools()
        test_tool = None
        
        for tool in tools:
            if getattr(tool, 'name', '') == 'test_tool':
                test_tool = tool
                break
        
        if not test_tool:
            print("❌ test_tool 도구를 찾을 수 없습니다.")
            return False
        
        # 테스트 도구 실행
        result = await test_tool.ainvoke({})
        
        print("✅ 테스트 도구 실행 성공:")
        print(f"  📄 결과: {result}")
            
        return True
        
    except Exception as e:
        print(f"❌ 테스트 도구 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_all_functions():
    """모든 기능 테스트"""
    print("=" * 60)
    print("🧪 Loki & Tempo MCP 서버 기능 테스트")
    print("=" * 60)
    
    # 연결 테스트
    client = await test_connection()
    if not client:
        print("\n❌ 테스트 중단: MCP 서버에 연결할 수 없습니다.")
        print("🔧 다음을 확인하세요:")
        print("   1. MCP 서버가 실행 중인지 확인")
        print("   2. 포트 10002가 사용 중인지 확인")
        print("   3. 환경 설정이 올바른지 확인")
        return False
    
    success_count = 0
    total_tests = 5
    
    # 도구 목록 테스트
    tools = await test_get_tools(client)
    if tools:
        success_count += 1
    
    # 기본 테스트 도구 실행
    if await test_test_tool(client):
        success_count += 1
    
    # 환경 설정 확인 테스트
    if await test_environment_check(client):
        success_count += 1
    
    # 로그 쿼리 테스트
    if await test_query_logs(client):
        success_count += 1
    
    # 트레이스 검색 테스트
    if await test_search_traces(client):
        success_count += 1
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"✅ 성공: {success_count}/{total_tests}")
    print(f"❌ 실패: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 모든 테스트가 성공했습니다!")
        print("🚀 MCP 서버가 정상적으로 작동합니다.")
    elif success_count > 0:
        print("⚠️ 일부 테스트가 성공했습니다.")
        print("🔧 실패한 테스트들을 확인하고 수정하세요.")
    else:
        print("❌ 모든 테스트가 실패했습니다.")
        print("🔧 서버 설정과 환경을 점검하세요.")
    
    return success_count >= 2  # 최소 2개 테스트 성공하면 OK

async def main():
    """메인 함수"""
    try:
        success = await test_all_functions()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 