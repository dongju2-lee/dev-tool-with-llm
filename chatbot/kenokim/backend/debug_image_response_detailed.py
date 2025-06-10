#!/usr/bin/env python3
"""
이미지 데이터의 상세 분석을 위한 디버깅
"""

import asyncio
import json
import base64
from app.graph.instance import process_chat_message

async def analyze_image_data():
    """실제 이미지 데이터를 상세히 분석합니다."""
    
    print("🔍 이미지 데이터 상세 분석")
    print("=" * 60)
    
    query = "Node Exporter Full 대시보드를 렌더링해주세요"
    print(f"📝 요청: {query}")
    print("-" * 60)
    
    try:
        result = await process_chat_message(query)
        
        # 메타데이터에서 원본 응답 확인
        metadata = result.get('metadata', {})
        if 'original_response' in metadata:
            original = metadata['original_response']
            print(f"🔄 원본 응답 길이: {len(original)}자")
            
            # LangGraph 상태의 마지막 메시지를 확인
            if hasattr(original, 'get') and 'messages' in original:
                messages = original['messages']
                print(f"📊 메시지 개수: {len(messages)}")
                
                for i, msg in enumerate(messages):
                    print(f"\n💬 메시지 {i+1}:")
                    print(f"  - 타입: {type(msg).__name__}")
                    
                    if hasattr(msg, 'content'):
                        content = msg.content
                        if isinstance(content, str):
                            if content.startswith('iVBORw0KGgo'):  # PNG base64 시작
                                print(f"  ✅ Base64 이미지 데이터 발견!")
                                print(f"  - 길이: {len(content)}자")
                                print(f"  - 시작: {content[:50]}...")
                                print(f"  - 끝: ...{content[-50:]}")
                                
                                # Base64 유효성 검증
                                try:
                                    decoded = base64.b64decode(content[:100])
                                    if decoded.startswith(b'\x89PNG'):
                                        print("  ✅ 유효한 PNG 이미지 데이터")
                                    else:
                                        print("  ❌ PNG 헤더 없음")
                                except Exception as e:
                                    print(f"  ❌ Base64 디코딩 실패: {e}")
                            else:
                                print(f"  📝 텍스트 콘텐츠: {content[:100]}...")
                        else:
                            print(f"  🔍 비텍스트 콘텐츠: {type(content)}")
                    
                    if hasattr(msg, 'name'):
                        print(f"  - 에이전트: {msg.name}")
            else:
                print("  ❌ LangGraph 메시지 구조 없음")
        
        # 최종 응답 확인
        final_content = result.get('content', '')
        print(f"\n📤 최종 응답:")
        print(f"  - 길이: {len(final_content)}자")
        print(f"  - 내용: {final_content}")
        
        if '[렌더링된 이미지 데이터]' in final_content:
            print("  ❌ 플레이스홀더가 그대로 남음")
        elif final_content.startswith('data:image'):
            print("  ✅ 이미지 데이터 URL 형식")
        elif 'iVBORw0KGgo' in final_content:
            print("  ✅ Base64 이미지 데이터 포함")
        else:
            print("  ❌ 이미지 데이터 없음")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_image_data()) 