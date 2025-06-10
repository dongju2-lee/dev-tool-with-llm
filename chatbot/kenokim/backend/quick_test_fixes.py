"""
수정된 Supervisor 핸드오프 로직을 빠르게 테스트하는 스크립트
"""

import asyncio
from app.graph.instance import process_chat_message

async def test_quick_scenarios():
    """핵심 시나리오들을 빠르게 테스트합니다."""
    
    test_cases = [
        {
            "name": "대시보드 목록 요청",
            "input": "대시보드 목록을 보여주세요",
            "expected_agent": "grafana_renderer_mcp_agent"
        },
        {
            "name": "특정 대시보드 렌더링",
            "input": "Node Exporter Full 대시보드를 렌더링해주세요",
            "expected_agent": "grafana_renderer_mcp_agent"
        },
        {
            "name": "서버 성능 분석",
            "input": "서버 성능을 분석해주세요",
            "expected_agent": "grafana_agent"
        },
        {
            "name": "일반 인사",
            "input": "안녕하세요",
            "expected_agent": "supervisor"
        }
    ]
    
    print("🧪 빠른 핸드오프 테스트 시작")
    print("=" * 50)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[{i}/4] {case['name']}")
        print(f"입력: {case['input']}")
        
        try:
            result = await process_chat_message(case['input'], f"test-{i}")
            
            agent_used = result.get('agent_used', 'unknown')
            tools_used = result.get('tools_used', [])
            response = result.get('content', '')
            
            print(f"사용된 에이전트: {agent_used}")
            print(f"사용된 도구: {tools_used}")
            print(f"응답 길이: {len(response)} 문자")
            
            # 예상 결과와 비교
            success = "✅" if agent_used == case['expected_agent'] else "❌"
            print(f"결과: {success} (예상: {case['expected_agent']})")
            
            if len(tools_used) > 0:
                print(f"도구 사용: ✅ {len(tools_used)}개")
            else:
                print("도구 사용: ❌ 없음")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        # 테스트 간 간격
        await asyncio.sleep(1)
    
    print("\n" + "=" * 50)
    print("빠른 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_quick_scenarios()) 