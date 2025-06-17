# LangGraph ReAct Agent 구현 예제

## ReAct Agent 클래스 기반 구현

### 1. 기본 State 클래스 정의

```python
from typing import TypedDict, List, Optional, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
import json

class AgentState(TypedDict):
    """ReAct Agent의 상태를 정의하는 클래스"""
    messages: List[BaseMessage]
    current_step: int
    max_steps: int
    final_answer: Optional[str]
    tool_calls: List[dict]
    reasoning: List[str]
```

### 2. ReAct Agent 메인 클래스

```python
class ReActAgent:
    """LangGraph 기반 ReAct Pattern Agent 구현"""
    
    def __init__(self, llm: ChatOpenAI, tools: List[BaseTool], max_steps: int = 10):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 구성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("reasoning", self._reasoning_step)
        workflow.add_node("action", self._action_step)
        workflow.add_node("observation", self._observation_step)
        workflow.add_node("final_answer", self._final_answer_step)
        
        # 엣지 추가
        workflow.set_entry_point("reasoning")
        workflow.add_conditional_edges(
            "reasoning",
            self._should_continue,
            {
                "continue": "action",
                "finish": "final_answer"
            }
        )
        workflow.add_edge("action", "observation")
        workflow.add_edge("observation", "reasoning")
        workflow.add_edge("final_answer", END)
        
        return workflow.compile()
    
    def _reasoning_step(self, state: AgentState) -> AgentState:
        """추론 단계: 문제 분석 및 다음 액션 결정"""
        messages = state["messages"]
        current_step = state.get("current_step", 0)
        
        # 시스템 프롬프트 구성
        system_prompt = self._create_reasoning_prompt()
        
        # LLM에게 추론 요청
        response = self.llm.invoke([
            {"role": "system", "content": system_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages]
        ])
        
        # 추론 결과 파싱
        reasoning = self._parse_reasoning(response.content)
        
        state["reasoning"].append(reasoning)
        state["current_step"] = current_step + 1
        
        return state
    
    def _action_step(self, state: AgentState) -> AgentState:
        """액션 단계: 도구 실행"""
        messages = state["messages"]
        
        # 액션 결정을 위한 프롬프트
        action_prompt = self._create_action_prompt()
        
        response = self.llm.invoke([
            {"role": "system", "content": action_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages]
        ])
        
        # 도구 호출 파싱
        tool_call = self._parse_tool_call(response.content)
        
        if tool_call:
            state["tool_calls"].append(tool_call)
            # 실제 도구 실행은 observation 단계에서 수행
        
        return state
    
    def _observation_step(self, state: AgentState) -> AgentState:
        """관찰 단계: 도구 실행 결과 처리"""
        if not state["tool_calls"]:
            return state
            
        last_tool_call = state["tool_calls"][-1]
        tool_name = last_tool_call["name"]
        tool_args = last_tool_call["args"]
        
        if tool_name in self.tools:
            try:
                # 도구 실행
                result = self.tools[tool_name].invoke(tool_args)
                
                # 결과를 메시지로 추가
                observation_msg = ToolMessage(
                    content=f"Tool '{tool_name}' result: {result}",
                    tool_call_id=last_tool_call.get("id", "")
                )
                state["messages"].append(observation_msg)
                
            except Exception as e:
                error_msg = ToolMessage(
                    content=f"Tool '{tool_name}' error: {str(e)}",
                    tool_call_id=last_tool_call.get("id", "")
                )
                state["messages"].append(error_msg)
        
        return state
    
    def _final_answer_step(self, state: AgentState) -> AgentState:
        """최종 답변 단계"""
        messages = state["messages"]
        
        final_prompt = self._create_final_answer_prompt()
        
        response = self.llm.invoke([
            {"role": "system", "content": final_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages]
        ])
        
        state["final_answer"] = response.content
        
        # 최종 답변을 메시지에 추가
        final_msg = AIMessage(content=response.content)
        state["messages"].append(final_msg)
        
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        """계속 진행할지 결정하는 조건부 엣지"""
        current_step = state.get("current_step", 0)
        max_steps = state.get("max_steps", self.max_steps)
        
        # 최대 스텝 도달 시 종료
        if current_step >= max_steps:
            return "finish"
        
        # 최종 답변이 이미 있는 경우 종료
        if state.get("final_answer"):
            return "finish"
        
        # 마지막 메시지가 답변 완료를 나타내는 경우
        messages = state["messages"]
        if messages and self._is_answer_complete(messages[-1]):
            return "finish"
        
        return "continue"
    
    def _create_reasoning_prompt(self) -> str:
        """추론 단계를 위한 시스템 프롬프트"""
        return """
        당신은 ReAct 패턴을 따르는 AI 에이전트입니다.
        
        각 단계에서 다음을 수행하세요:
        1. Thought: 현재 상황을 분석하고 다음에 할 일을 생각하세요
        2. 사용 가능한 도구들을 고려하여 필요한 액션을 결정하세요
        3. 문제 해결을 위한 논리적 추론을 제공하세요
        
        사용 가능한 도구들:
        {tools}
        
        응답 형식:
        Thought: [여기에 추론 과정 작성]
        """.format(tools=list(self.tools.keys()))
    
    def _create_action_prompt(self) -> str:
        """액션 단계를 위한 시스템 프롬프트"""
        return """
        이전 추론을 바탕으로 실행할 액션을 결정하세요.
        
        응답 형식:
        Action: [도구 이름]
        Action Input: [도구에 전달할 인수를 JSON 형태로]
        
        예시:
        Action: search
        Action Input: {"query": "LangGraph documentation"}
        """
    
    def _create_final_answer_prompt(self) -> str:
        """최종 답변을 위한 시스템 프롬프트"""
        return """
        지금까지의 추론과 관찰 결과를 바탕으로 최종 답변을 작성하세요.
        
        응답 형식:
        Final Answer: [최종 답변]
        """
    
    def _parse_reasoning(self, content: str) -> str:
        """추론 내용 파싱"""
        if "Thought:" in content:
            return content.split("Thought:")[-1].strip()
        return content.strip()
    
    def _parse_tool_call(self, content: str) -> Optional[dict]:
        """도구 호출 파싱"""
        lines = content.strip().split('\n')
        action = None
        action_input = None
        
        for line in lines:
            if line.startswith("Action:"):
                action = line.replace("Action:", "").strip()
            elif line.startswith("Action Input:"):
                try:
                    action_input = json.loads(line.replace("Action Input:", "").strip())
                except json.JSONDecodeError:
                    action_input = line.replace("Action Input:", "").strip()
        
        if action:
            return {
                "name": action,
                "args": action_input or {},
                "id": f"call_{len(self.tools)}"
            }
        
        return None
    
    def _is_answer_complete(self, message: BaseMessage) -> bool:
        """답변이 완료되었는지 확인"""
        if isinstance(message, AIMessage):
            content = message.content.lower()
            return "final answer:" in content or "답변:" in content
        return False
    
    def run(self, query: str) -> dict:
        """ReAct Agent 실행"""
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "current_step": 0,
            "max_steps": self.max_steps,
            "final_answer": None,
            "tool_calls": [],
            "reasoning": []
        }
        
        # 그래프 실행
        result = self.graph.invoke(initial_state)
        
        return {
            "final_answer": result.get("final_answer"),
            "reasoning_steps": result.get("reasoning", []),
            "tool_calls": result.get("tool_calls", []),
            "total_steps": result.get("current_step", 0)
        }
```

### 3. 도구 정의 예제

```python
from langchain_core.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="검색할 쿼리")

class SearchTool(BaseTool):
    name = "search"
    description = "웹 검색을 수행합니다"
    args_schema: Type[BaseModel] = SearchInput
    
    def _run(self, query: str) -> str:
        # 실제 검색 로직 구현
        return f"검색 결과: {query}에 대한 정보"

class CalculatorInput(BaseModel):
    expression: str = Field(description="계산할 수식")

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "수학 계산을 수행합니다"
    args_schema: Type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str) -> str:
        try:
            result = eval(expression)
            return f"계산 결과: {result}"
        except Exception as e:
            return f"계산 오류: {str(e)}"
```

### 4. 사용 예제

```python
from langchain_openai import ChatOpenAI

# LLM 및 도구 초기화
llm = ChatOpenAI(model="gpt-4", temperature=0)
tools = [SearchTool(), CalculatorTool()]

# ReAct Agent 생성
agent = ReActAgent(llm=llm, tools=tools, max_steps=5)

# Agent 실행
query = "2024년 AI 기술 트렌드를 검색하고, 그 중 3가지 주요 트렌드를 요약해주세요"
result = agent.run(query)

print("Final Answer:", result["final_answer"])
print("Reasoning Steps:", result["reasoning_steps"])
print("Tool Calls:", result["tool_calls"])
print("Total Steps:", result["total_steps"])
```

### 5. 고급 ReAct Agent 클래스 (메모리 기능 포함)

```python
class AdvancedReActAgent(ReActAgent):
    """메모리 기능이 포함된 고급 ReAct Agent"""
    
    def __init__(self, llm: ChatOpenAI, tools: List[BaseTool], max_steps: int = 10):
        super().__init__(llm, tools, max_steps)
        self.memory = []  # 대화 히스토리 저장
        self.working_memory = {}  # 작업 메모리
    
    def _reasoning_step(self, state: AgentState) -> AgentState:
        """메모리를 활용한 추론 단계"""
        # 이전 대화 히스토리 참조
        if self.memory:
            memory_context = self._format_memory_context()
            state["messages"].insert(0, HumanMessage(content=f"이전 대화 맥락: {memory_context}"))
        
        state = super()._reasoning_step(state)
        
        # 작업 메모리 업데이트
        self._update_working_memory(state)
        
        return state
    
    def _format_memory_context(self) -> str:
        """메모리 컨텍스트 포맷팅"""
        recent_memory = self.memory[-3:]  # 최근 3개 대화만 참조
        return "\n".join([f"Q: {item['query']}\nA: {item['answer']}" for item in recent_memory])
    
    def _update_working_memory(self, state: AgentState) -> None:
        """작업 메모리 업데이트"""
        if state["reasoning"]:
            last_reasoning = state["reasoning"][-1]
            # 중요한 정보 추출 및 저장
            self.working_memory[f"step_{state['current_step']}"] = last_reasoning
    
    def run(self, query: str) -> dict:
        """메모리 기능이 포함된 실행"""
        result = super().run(query)
        
        # 대화 히스토리에 추가
        self.memory.append({
            "query": query,
            "answer": result["final_answer"],
            "reasoning_steps": result["reasoning_steps"]
        })
        
        return result
```

이 예제는 LangGraph를 사용하여 ReAct 패턴을 구현하는 완전한 클래스 기반 구조를 보여줍니다. 상태 관리, 조건부 엣지, 도구 통합, 그리고 메모리 기능까지 포함하고 있습니다.
