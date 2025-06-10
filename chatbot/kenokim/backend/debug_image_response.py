#!/usr/bin/env python3
"""
이미지 렌더링 응답 디버깅
"""

import asyncio
import json
from app.graph.instance import process_chat_message

async def debug_image_response():
    """이미지 렌더링 응답을 상세히 디버깅합니다."""
    
    print("🔍 이미지 렌더링 응답 디버깅")
    print("=" * 60)
    
    # 이미지 렌더링 요청
    query = "Node Exporter Full 대시보드를 렌더링해주세요"
    print(f"📝 요청: {query}")
    print("-" * 60)
    
    try:
        result = await process_chat_message(query)
        
        print("📊 기본 정보:")
        print(f"  - Agent: {result.get('agent_used', 'unknown')}")
        print(f"  - Tools: {result.get('tools_used', [])}")
        print(f"  - 응답 길이: {len(result.get('content', ''))}자")
        
        print("\n💬 전체 응답:")
        print(result.get('content', 'No content'))
        
        print("\n🔍 응답 분석:")
        content = result.get('content', '')
        
        # 이미지 관련 키워드 체크
        image_keywords = ['이미지', 'image', 'base64', 'data:', 'png', 'jpg', 'jpeg', 'svg']
        found_keywords = [kw for kw in image_keywords if kw.lower() in content.lower()]
        print(f"  - 이미지 관련 키워드: {found_keywords if found_keywords else '없음'}")
        
        # 데이터 형식 체크
        if 'data:image' in content:
            print("  ✅ Base64 이미지 데이터 형식 발견")
        elif '[렌더링된 이미지 데이터]' in content:
            print("  ❌ 플레이스홀더만 있음 - 실제 이미지 데이터 없음")
        elif len(content) > 1000:
            print("  🔍 긴 응답 - 이미지 데이터일 가능성 있음")
        else:
            print("  ❌ 이미지 데이터 없는 것으로 보임")
        
        # 메타데이터 확인
        if 'metadata' in result:
            print(f"\n📋 메타데이터:")
            metadata = result['metadata']
            for key, value in metadata.items():
                if key != 'original_response':  # 너무 길 수 있으므로 제외
                    print(f"  - {key}: {value}")
        
        # 원본 응답이 있다면 확인
        if result.get('metadata', {}).get('original_response'):
            original = result['metadata']['original_response']
            print(f"\n🔄 원본 응답 (처음 200자):")
            print(original[:200] + "..." if len(original) > 200 else original)
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_image_response()) 