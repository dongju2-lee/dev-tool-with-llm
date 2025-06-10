#!/usr/bin/env python3

import asyncio
from app.graph.instance import process_chat_message

async def test_output():
    result = await process_chat_message('Node Exporter Full 대시보드를 렌더링해주세요')
    content = result.get('content', '')
    
    print("=== 백엔드 응답 분석 ===")
    print(f"전체 길이: {len(content)}")
    
    if '![Dashboard Image](' in content:
        start = content.find('![Dashboard Image](') + len('![Dashboard Image](')
        end = content.find(')', start)
        img_src = content[start:end]
        print(f"이미지 src 시작: {img_src[:80]}...")
        print(f"data:image 포함 여부: {'data:image' in img_src}")
        print(f"이미지 src 전체 길이: {len(img_src)}")
    else:
        print("마크다운 이미지 태그 없음")
        print(f"content 일부: {content[:200]}...")
    
    print("\n=== 응답의 마지막 부분 ===")
    print(content[-200:])

asyncio.run(test_output()) 