LangGraph와 Gemini를 Python에서 함께 호출하는 방법 (2025년 기준)
LangGraph는 Python에서 상태 기반(stateful) LLM 워크플로우를 그래프 형태로 설계할 수 있는 라이브러리이고, Gemini는 Google의 강력한 멀티모달 LLM API입니다. 두 기술을 연동하면, Gemini 모델을 LangGraph의 노드(node)로 활용하여 복잡한 에이전트 워크플로우를 구현할 수 있습니다.

아래는 2025년 기준 최신 Gemini API와 LangGraph를 Python에서 연동하는 기본적인 방법입니다.

1. 필수 패키지 설치
bash
pip install -U langgraph
pip install google-genai
langgraph: LangGraph 본체

google-genai: Gemini Python 클라이언트

2. Gemini API 키 발급 및 환경 변수 설정
Google AI Studio(https://aistudio.google.com/)에서 Gemini API 키를 발급

환경 변수 또는 코드에서 API 키 지정

python
import os
os.environ["API_KEY"] = "YOUR_GEMINI_API_KEY"
3. Gemini 모델을 LangGraph 노드로 활용하기
Gemini API를 직접 호출하는 함수를 LangGraph의 노드로 등록할 수 있습니다.

python
from google import genai
from langgraph.graph import MessageGraph, END

# Gemini 클라이언트 초기화
client = genai.Client(api_key=os.environ["API_KEY"])

# Gemini 호출 함수 정의
def gemini_node(messages):
    prompt = messages[-1]["content"]  # 마지막 메시지(사용자 입력) 사용
    response = client.models.generate_content(
        model='gemini-2.0-flash',  # 최신 모델명 사용
        contents=prompt
    )
    return [{"role": "assistant", "content": response.text}]

# LangGraph 메시지 그래프 생성
graph = MessageGraph()
graph.add_node("gemini", gemini_node)
graph.add_edge("gemini", END)
graph.set_entry_point("gemini")
runnable = graph.compile()
위 예시에서 gemini_node는 LangGraph의 노드로, 입력 메시지를 받아 Gemini API로 답변을 생성합니다.

4. LangGraph 워크플로우 실행
python
user_input = "파이썬 pandas 패키지는 무엇에 쓰이나요?"
state = [{"role": "user", "content": user_input}]
result = runnable.invoke({"messages": state})
print(result["messages"][-1]["content"])
사용자의 입력을 메시지 형태로 넘기면, Gemini가 답변을 생성해 반환합니다.

5. (선택) Gemini의 코드 실행 기능 활용
Gemini 2.0 이상에서는 코드 실행(Code Execution) 기능도 API로 사용할 수 있습니다. 예를 들어, 수식 계산이나 데이터 분석 결과를 실시간으로 얻고 싶을 때 아래와 같이 사용할 수 있습니다:

python
from google.genai import types

response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents="""
    1부터 50까지의 소수의 합을 계산하고, 파이썬 코드를 실행해 결과를 보여줘.
    """,
    config=types.GenerateContentConfig(
        tools=[types.Tool(code_execution=types.ToolCodeExecution)]
    )
)
print(response.text)
요약
LangGraph의 노드에 Gemini API 호출 함수를 등록하면, 복잡한 LLM 워크플로우 내에서 Gemini를 자유롭게 활용할 수 있습니다.

최신 Gemini 모델명(gemini-2.0-flash 등)과 API 키를 정확히 사용해야 하며, 필요시 코드 실행 기능도 활성화할 수 있습니다.

LangGraph의 상태 관리와 Gemini의 강력한 언어/멀티모달 처리 능력을 결합하여, 다양한 AI 에이전트 및 챗봇을 Python에서 손쉽게 구현할 수 있습니다.

참고: 실제 워크플로우에 따라 LangGraph의 다양한 그래프 구조(StateGraph 등)와 조건부 분기, 툴 연동 등을 활용해 더 복잡한 에이전트도 구현할 수 있습니다.