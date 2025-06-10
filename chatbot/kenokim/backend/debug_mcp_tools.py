"""
MCP 도구 로딩 및 호출 디버깅 스크립트
"""

import asyncio
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from app.graph.agents.grafana_renderer_mcp_agent import get_grafana_renderer_mcp_client
from dotenv import load_dotenv

load_dotenv()

async def debug_mcp_tools():
    """MCP 도구들이 제대로 로드되고 호출되는지 디버깅합니다."""
    
    print("🔍 MCP 도구 디버깅 시작")
    print("=" * 50)
    
    # 환경 변수 확인
    grafana_url = os.getenv("GRAFANA_MCP_URL")
    renderer_url = os.getenv("GRAFANA_RENDERER_MCP_URL")
    
    print(f"📍 GRAFANA_MCP_URL: {grafana_url}")
    print(f"📍 GRAFANA_RENDERER_MCP_URL: {renderer_url}")
    
    # Grafana Renderer MCP 클라이언트 테스트
    print("\n🎨 Grafana Renderer MCP 도구 확인")
    try:
        renderer_client = get_grafana_renderer_mcp_client()
        renderer_tools = await renderer_client.get_tools()
        
        print(f"✅ 렌더러 도구 개수: {len(renderer_tools)}")
        for i, tool in enumerate(renderer_tools[:5]):  # 처음 5개만
            print(f"  {i+1}. {tool.name}: {tool.description[:100]}...")
            
        # 첫 번째 도구로 실제 호출 테스트
        if renderer_tools:
            first_tool = renderer_tools[0]
            print(f"\n🧪 첫 번째 도구 테스트: {first_tool.name}")
            
            # list_dashboards 도구 찾기
            list_tool = None
            for tool in renderer_tools:
                if 'list' in tool.name.lower() or 'dashboard' in tool.name.lower():
                    list_tool = tool
                    break
            
            if list_tool:
                print(f"📋 대시보드 목록 도구 찾음: {list_tool.name}")
                try:
                    result = await list_tool.ainvoke({})
                    print(f"✅ 호출 성공: {str(result)[:200]}...")
                except Exception as e:
                    print(f"❌ 호출 실패: {e}")
            else:
                print("❌ 대시보드 목록 도구를 찾을 수 없음")
                
    except Exception as e:
        print(f"❌ 렌더러 클라이언트 오류: {e}")
    
    # Grafana MCP 클라이언트 테스트
    print("\n📊 Grafana MCP 도구 확인")
    try:
        mcp_client = MultiServerMCPClient(
            {
                "grafana_mcp_client": {
                    "url": f"{grafana_url}/sse",
                    "transport": "sse"
                }
            }
        )
        mcp_tools = await mcp_client.get_tools()
        
        print(f"✅ MCP 도구 개수: {len(mcp_tools)}")
        for i, tool in enumerate(mcp_tools[:5]):  # 처음 5개만
            print(f"  {i+1}. {tool.name}: {tool.description[:100]}...")
            
    except Exception as e:
        print(f"❌ MCP 클라이언트 오류: {e}")
    
    print("\n" + "=" * 50)
    print("MCP 도구 디버깅 완료")

async def test_direct_mcp_call():
    """MCP 도구를 직접 호출해서 동작하는지 테스트합니다."""
    
    print("\n🔧 직접 MCP 호출 테스트")
    print("=" * 30)
    
    try:
        renderer_client = get_grafana_renderer_mcp_client()
        tools = await renderer_client.get_tools()
        
        # list_dashboards 도구 찾기
        list_dashboards_tool = None
        for tool in tools:
            if 'list' in tool.name.lower() and 'dashboard' in tool.name.lower():
                list_dashboards_tool = tool
                break
        
        if list_dashboards_tool:
            print(f"📋 대시보드 목록 도구 테스트: {list_dashboards_tool.name}")
            result = await list_dashboards_tool.ainvoke({})
            print(f"결과: {result}")
            return result
        else:
            print("❌ list_dashboards 도구를 찾을 수 없음")
            # 모든 도구 이름 출력
            print("사용 가능한 도구들:")
            for tool in tools:
                print(f"  - {tool.name}")
            return None
            
    except Exception as e:
        print(f"❌ 직접 호출 실패: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(debug_mcp_tools())
    asyncio.run(test_direct_mcp_call()) 