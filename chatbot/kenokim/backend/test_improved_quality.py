#!/usr/bin/env python3
"""
응답 품질 개선 테스트
"""

import asyncio
import json
from app.graph.instance import process_chat_message

# 품질 개선을 확인할 테스트 케이스들
QUALITY_TEST_CASES = [
    {
        "name": "dashboard_list_basic",
        "request": "대시보드 목록 보여줘",
        "expected_improvements": [
            "실제 대시보드 목록 포함",
            "구체적인 대시보드 이름들",
            "선택 가능한 옵션 제공"
        ]
    },
    {
        "name": "dashboard_render_specific",
        "request": "Node Exporter 대시보드 렌더링해줘",
        "expected_improvements": [
            "렌더링 시도 결과",
            "시간 범위 정보",
            "구체적인 상태 메시지"
        ]
    },
    {
        "name": "performance_analysis",
        "request": "서버 성능 분석해줘",
        "expected_improvements": [
            "실제 메트릭 수치",
            "구체적인 분석 결과",
            "정상/비정상 판단"
        ]
    },
    {
        "name": "memory_check",
        "request": "메모리 사용량 확인해줘",
        "expected_improvements": [
            "실제 메모리 수치",
            "사용률 백분율",
            "용량 정보"
        ]
    },
    {
        "name": "ambiguous_request",
        "request": "시스템 상태 알려줘",
        "expected_improvements": [
            "구체적인 메트릭들",
            "여러 지표 포함",
            "종합적인 상태 평가"
        ]
    }
]

def analyze_response_quality(response: str, tools_used: list, agent_used: str) -> dict:
    """응답 품질을 분석합니다."""
    
    # 부정적 패턴 (빈약한 응답)
    poor_patterns = [
        "알겠습니다",
        "처리했습니다", 
        "전달했습니다",
        "완료했습니다",
        "확인했습니다"
    ]
    
    # 긍정적 패턴 (좋은 응답)
    good_patterns = [
        "현재",
        "결과",
        "분석",
        "상태",
        "%",
        "GB",
        "MB",
        "대시보드",
        "메트릭"
    ]
    
    analysis = {
        "length": len(response),
        "has_poor_patterns": any(pattern in response for pattern in poor_patterns),
        "has_good_patterns": any(pattern in response for pattern in good_patterns),
        "tools_used_count": len(tools_used),
        "agent_used": agent_used,
        "has_specific_data": any(char in response for char in ['%', 'GB', 'MB', ':', '/']),
        "quality_score": 0
    }
    
    # 품질 점수 계산
    score = 0
    
    # 응답 길이 (50자 이상이면 좋음)
    if analysis["length"] >= 50:
        score += 20
    elif analysis["length"] >= 20:
        score += 10
    
    # 빈약한 패턴이 없으면 좋음
    if not analysis["has_poor_patterns"]:
        score += 20
    
    # 좋은 패턴이 있으면 좋음
    if analysis["has_good_patterns"]:
        score += 20
    
    # 도구를 사용했으면 좋음
    if analysis["tools_used_count"] > 0:
        score += 20
    
    # 구체적인 데이터가 있으면 좋음
    if analysis["has_specific_data"]:
        score += 20
    
    analysis["quality_score"] = score
    
    return analysis

async def run_quality_tests():
    """품질 개선 테스트를 실행합니다."""
    
    print("🔬 응답 품질 개선 테스트 시작")
    print("=" * 60)
    
    total_score = 0
    test_count = len(QUALITY_TEST_CASES)
    
    for i, test_case in enumerate(QUALITY_TEST_CASES, 1):
        print(f"\n📋 테스트 {i}/{test_count}: {test_case['name']}")
        print(f"📝 요청: {test_case['request']}")
        
        try:
            # 요청 처리
            result = await process_chat_message(test_case["request"])
            
            # 응답 분석
            analysis = analyze_response_quality(
                result["content"],
                result["tools_used"],
                result["agent_used"]
            )
            
            # 결과 출력
            print(f"🤖 Agent: {result['agent_used']}")
            print(f"🔧 Tools: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
            print(f"📏 응답 길이: {analysis['length']}자")
            print(f"⭐ 품질 점수: {analysis['quality_score']}/100")
            
            # 응답 내용 (처음 200자만)
            display_content = result["content"][:200]
            if len(result["content"]) > 200:
                display_content += "..."
            print(f"💬 응답: {display_content}")
            
            # 품질 분석 상세
            print(f"📊 분석:")
            print(f"  - 빈약한 패턴: {'❌ 발견됨' if analysis['has_poor_patterns'] else '✅ 없음'}")
            print(f"  - 좋은 패턴: {'✅ 있음' if analysis['has_good_patterns'] else '❌ 없음'}")
            print(f"  - 구체적 데이터: {'✅ 있음' if analysis['has_specific_data'] else '❌ 없음'}")
            
            total_score += analysis['quality_score']
            
        except Exception as e:
            print(f"❌ 오류: {str(e)}")
            
        print("-" * 60)
    
    # 전체 결과
    average_score = total_score / test_count if test_count > 0 else 0
    print(f"\n🏁 전체 결과")
    print(f"📊 평균 품질 점수: {average_score:.1f}/100")
    
    if average_score >= 80:
        print("🎉 응답 품질: 우수")
    elif average_score >= 60:
        print("👍 응답 품질: 양호")
    elif average_score >= 40:
        print("📈 응답 품질: 개선 필요")
    else:
        print("🔧 응답 품질: 대폭 개선 필요")

if __name__ == "__main__":
    asyncio.run(run_quality_tests()) 