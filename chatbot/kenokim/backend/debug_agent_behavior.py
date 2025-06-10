"""
LangGraph Agent의 MCP 도구 호출 동작을 디버깅하는 스크립트
"""

import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from app.graph.agents.grafana_renderer_mcp_agent import make_grafana_renderer_agent
from app.core.config import settings

async def debug_agent_tool_calls():
    """LangGraph Agent가 도구를 어떻게 호출하는지 디버깅합니다."""
    
    print("🔍 LangGraph Agent 도구 호출 디버깅")
    print("=" * 50)
    
    # LLM 초기화
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0
    )
    
    # Agent 생성
    print("🤖 Grafana Renderer Agent 생성 중...")
    agent = await make_grafana_renderer_agent(llm)
    
    # Agent가 갖고 있는 도구들 확인
    print(f"✅ Agent 생성 완료")
    
    # Agent의 도구들 확인
    if hasattr(agent, 'tools'):
        print(f"📊 Agent에 등록된 도구 개수: {len(agent.tools)}")
        for i, tool in enumerate(agent.tools[:10]):  # 처음 10개만
            print(f"  {i+1}. {tool.name}: {tool.description[:80]}...")
    else:
        print("❌ Agent에 tools 속성이 없음")
    
    # 간단한 메시지로 Agent 테스트
    test_messages = [
        "대시보드 목록을 보여주세요",
        "list_dashboards를 호출해 주세요",
        "대시보드가 몇 개나 있는지 확인해 주세요"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n[{i}/3] 테스트 메시지: {message}")
        
        try:
            # Agent 실행
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                {"configurable": {"thread_id": f"debug-{i}"}}
            )
            
            # 결과 분석
            if "messages" in result:
                messages = result["messages"]
                print(f"📨 생성된 메시지 개수: {len(messages)}")
                
                # 도구 호출 확인
                tool_calls_found = False
                for msg in messages:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tool_calls_found = True
                        print(f"🔧 도구 호출 발견: {len(msg.tool_calls)}개")
                        for tool_call in msg.tool_calls:
                            print(f"  - {tool_call.get('name', 'unknown')}")
                    
                    if hasattr(msg, 'additional_kwargs') and 'tool_calls' in msg.additional_kwargs:
                        tool_calls_found = True
                        print(f"🔧 추가 도구 호출 발견")
                
                if not tool_calls_found:
                    print("❌ 도구 호출 없음")
                
                # 최종 응답
                ai_messages = [msg for msg in messages if hasattr(msg, 'type') and msg.type == 'ai']
                if ai_messages:
                    final_response = ai_messages[-1].content
                    print(f"💬 최종 응답: {final_response[:100]}...")
                
        except Exception as e:
            print(f"❌ Agent 실행 오류: {e}")
        
        print("-" * 30)

async def test_direct_react_agent():
    """React Agent를 직접 테스트해보고 문제점을 파악합니다."""
    
    print("\n🧪 React Agent 직접 테스트")
    print("=" * 40)
    
    from langgraph.prebuilt import create_react_agent
    from app.graph.agents.grafana_renderer_mcp_agent import get_grafana_renderer_mcp_client
    
    # LLM 초기화
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0
    )
    
    # MCP 도구들만 가져오기
    try:
        client = get_grafana_renderer_mcp_client()
        mcp_tools = await client.get_tools()
        print(f"📊 MCP 도구 개수: {len(mcp_tools)}")
        
        # 간단한 프롬프트로 React Agent 생성
        simple_prompt = """
당신은 Grafana 대시보드 관리 전문가입니다.
사용자가 대시보드 목록을 요청하면 반드시 list_dashboards 도구를 사용해서 실제 목록을 조회해야 합니다.
도구를 사용하지 않고 추측하거나 임의의 답변을 하지 마세요.
"""
        
        react_agent = create_react_agent(
            model=llm,
            tools=mcp_tools,
            prompt=simple_prompt
        )
        
        # 명확한 도구 사용 요청
        test_input = {"messages": [HumanMessage(content="list_dashboards 도구를 사용해서 대시보드 목록을 조회해 주세요")]}
        
        print("🚀 React Agent 실행 중...")
        result = await react_agent.ainvoke(test_input)
        
        # 결과 분석
        if "messages" in result:
            messages = result["messages"]
            print(f"📨 메시지 개수: {len(messages)}")
            
            for i, msg in enumerate(messages):
                print(f"  {i+1}. {msg.type}: {str(msg.content)[:100]}...")
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    print(f"     🔧 도구 호출: {[tc.get('name') for tc in msg.tool_calls]}")
        
    except Exception as e:
        print(f"❌ React Agent 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(debug_agent_tool_calls())
    asyncio.run(test_direct_react_agent()) 