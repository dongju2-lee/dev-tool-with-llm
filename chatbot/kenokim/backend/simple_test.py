#!/usr/bin/env python3
"""
간단한 대시보드 목록 테스트
"""

import asyncio
from app.graph.instance import process_chat_message

async def test_simple():
    print("🧪 간단한 테스트")
    
    result = await process_chat_message("대시보드 목록을 보여주세요")
    
    print(f"🤖 Agent: {result['agent_used']}")
    print(f"🔧 Tools: {result['tools_used']}")
    print(f"💬 응답:")
    print(result["content"])

if __name__ == "__main__":
    asyncio.run(test_simple()) 