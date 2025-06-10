import asyncio
import logging
from app.graph.instance import process_chat_message

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_supervisor_worker_handoff():
    """수정된 supervisor의 worker handoff 동작을 테스트합니다."""
    print("🔍 수정된 Supervisor-Worker Handoff 테스트 시작\n")
    
    test_cases = [
        {
            "name": "대시보드 목록 요청",
            "message": "대시보드 목록을 보여주세요",
            "expected_agent": "grafana_renderer_mcp_agent",
            "expected_result": "목록이 포함된 응답"
        },
        {
            "name": "특정 대시보드 렌더링",
            "message": "Node Exporter Full 대시보드를 렌더링해주세요",
            "expected_agent": "grafana_renderer_mcp_agent",
            "expected_result": "이미지가 포함된 응답"
        },
        {
            "name": "간단한 인사",
            "message": "안녕하세요",
            "expected_agent": "supervisor",
            "expected_result": "직접 응답"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"--- 테스트 {i}: {test_case['name']} ---")
        print(f"메시지: {test_case['message']}")
        
        try:
            # 실제 처리
            result = await process_chat_message(test_case['message'], f"test-thread-{i}")
            
            # 결과 분석
            response_content = result.get('content', '')
            agent_used = result.get('agent_used', 'unknown')
            tools_used = result.get('tools_used', [])
            
            print(f"✅ 처리 완료")
            print(f"사용된 에이전트: {agent_used}")
            print(f"사용된 도구들: {tools_used}")
            print(f"응답 길이: {len(response_content)} 문자")
            
            # 응답 내용 미리보기
            if len(response_content) > 200:
                preview = response_content[:200] + "..."
                print(f"응답 미리보기: {preview}")
                
                # 이미지 데이터 확인
                if len(response_content) > 10000:
                    print("🖼️ 대용량 응답 (이미지 포함 가능성 높음)")
                else:
                    print("📝 텍스트 응답")
            else:
                print(f"응답 전체: {response_content}")
            
            # 기대 결과와 비교
            success = True
            if test_case['expected_result'] == "이미지가 포함된 응답":
                if len(response_content) < 10000:
                    print("⚠️ 예상보다 짧은 응답 (이미지 없을 가능성)")
                    success = False
                else:
                    print("✅ 이미지가 포함된 것으로 보임")
            elif test_case['expected_result'] == "목록이 포함된 응답":
                if len(response_content) < 100:
                    print("⚠️ 예상보다 짧은 응답 (목록 없을 가능성)")
                    success = False
                else:
                    print("✅ 적절한 길이의 응답")
            
            results.append({
                "test_name": test_case['name'],
                "success": success,
                "agent_used": agent_used,
                "response_length": len(response_content),
                "tools_used": len(tools_used)
            })
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            results.append({
                "test_name": test_case['name'],
                "success": False,
                "error": str(e)
            })
        
        print("-" * 50)
        await asyncio.sleep(2)  # 각 테스트 간 간격
    
    # 결과 요약
    print(f"\n📊 테스트 결과 요약")
    print("=" * 50)
    
    successful_tests = [r for r in results if r.get('success', False)]
    print(f"성공한 테스트: {len(successful_tests)}/{len(results)}")
    
    for result in results:
        status = "✅" if result.get('success', False) else "❌"
        print(f"{status} {result['test_name']}")
        
        if result.get('success', False):
            print(f"   에이전트: {result.get('agent_used', 'N/A')}")
            print(f"   응답 길이: {result.get('response_length', 0)} 문자")
            print(f"   도구 사용: {result.get('tools_used', 0)}개")
        else:
            print(f"   오류: {result.get('error', 'Unknown error')}")
    
    print(f"\n💡 개선사항:")
    if len(successful_tests) < len(results):
        print("- output_mode 추가 조정 고려")
        print("- 프롬프트 명확성 개선")
        print("- 에러 핸들링 강화")
    else:
        print("- 모든 테스트 통과! 🎉")

async def main():
    """메인 함수"""
    await test_supervisor_worker_handoff()

if __name__ == "__main__":
    asyncio.run(main()) 