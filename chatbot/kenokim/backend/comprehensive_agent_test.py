"""
종합적인 Agent 테스트 및 평가 스크립트

여러 시나리오를 테스트하고 LLM을 통해 응답 품질을 평가합니다.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from app.graph.instance import process_chat_message
from app.core.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestScenario:
    """테스트 시나리오 정의"""
    name: str
    description: str
    user_input: str
    expected_agent: str
    expected_behavior: str
    success_criteria: str
    category: str

@dataclass
class TestResult:
    """테스트 결과"""
    scenario: TestScenario
    agent_response: str
    agent_used: str
    tools_used: List[str]
    response_length: int
    execution_time: float
    llm_evaluation: Dict[str, Any]
    success: bool
    error: str = None

class AgentEvaluator:
    """LLM을 이용한 Agent 응답 평가"""
    
    def __init__(self):
        self.evaluator_llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1
        )
    
    async def evaluate_response(self, scenario: TestScenario, response: str, agent_used: str, tools_used: List[str]) -> Dict[str, Any]:
        """LLM을 통해 응답을 평가합니다."""
        
        evaluation_prompt = f"""
다음 시나리오에 대한 AI Agent의 응답을 평가해주세요.

**테스트 시나리오:**
- 카테고리: {scenario.category}
- 설명: {scenario.description}
- 사용자 입력: "{scenario.user_input}"
- 기대 에이전트: {scenario.expected_agent}
- 기대 동작: {scenario.expected_behavior}
- 성공 기준: {scenario.success_criteria}

**Agent 응답 결과:**
- 사용된 에이전트: {agent_used}
- 사용된 도구: {tools_used}
- 응답 내용: "{response}"
- 응답 길이: {len(response)} 문자

**평가 기준:**
1. **에이전트 선택 적절성** (1-5점): 올바른 전문 에이전트가 선택되었는가?
2. **요청 이해도** (1-5점): 사용자의 요청을 정확히 이해했는가?
3. **응답 완성도** (1-5점): 요청에 대한 완전한 답변을 제공했는가?
4. **응답 품질** (1-5점): 응답이 명확하고 유용한가?
5. **전반적 만족도** (1-5점): 전체적으로 만족스러운 응답인가?

다음 JSON 형태로 평가해주세요:
{{
    "agent_selection_score": <1-5>,
    "understanding_score": <1-5>,
    "completeness_score": <1-5>,
    "quality_score": <1-5>,
    "overall_score": <1-5>,
    "total_score": <합계>,
    "max_score": 25,
    "percentage": <백분율>,
    "success": <true/false>,
    "strengths": ["강점1", "강점2"],
    "weaknesses": ["약점1", "약점2"],
    "recommendations": ["개선사항1", "개선사항2"],
    "summary": "한 줄 평가 요약"
}}
"""

        try:
            response_obj = await self.evaluator_llm.ainvoke(evaluation_prompt)
            evaluation_text = response_obj.content
            
            # JSON 추출 시도
            start_idx = evaluation_text.find('{')
            end_idx = evaluation_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = evaluation_text[start_idx:end_idx]
                evaluation = json.loads(json_str)
            else:
                # JSON 추출 실패 시 기본 평가
                evaluation = {
                    "agent_selection_score": 3,
                    "understanding_score": 3,
                    "completeness_score": 3,
                    "quality_score": 3,
                    "overall_score": 3,
                    "total_score": 15,
                    "max_score": 25,
                    "percentage": 60,
                    "success": False,
                    "strengths": ["응답 생성됨"],
                    "weaknesses": ["평가 실패"],
                    "recommendations": ["평가 시스템 개선 필요"],
                    "summary": "평가 처리 실패"
                }
            
            return evaluation
            
        except Exception as e:
            logger.error(f"평가 중 오류 발생: {e}")
            return {
                "agent_selection_score": 1,
                "understanding_score": 1,
                "completeness_score": 1,
                "quality_score": 1,
                "overall_score": 1,
                "total_score": 5,
                "max_score": 25,
                "percentage": 20,
                "success": False,
                "strengths": [],
                "weaknesses": ["평가 오류"],
                "recommendations": ["시스템 점검 필요"],
                "summary": f"평가 오류: {str(e)}"
            }

class ComprehensiveAgentTester:
    """종합적인 Agent 테스트 클래스"""
    
    def __init__(self):
        self.evaluator = AgentEvaluator()
        self.test_scenarios = self._define_test_scenarios()
        self.results: List[TestResult] = []
    
    def _define_test_scenarios(self) -> List[TestScenario]:
        """테스트 시나리오들을 정의합니다."""
        
        scenarios = [
            # 대시보드 목록 관련
            TestScenario(
                name="대시보드_목록_요청",
                description="사용 가능한 대시보드 목록을 요청하는 시나리오",
                user_input="대시보드 목록을 보여주세요",
                expected_agent="grafana_renderer_mcp_agent",
                expected_behavior="대시보드 목록을 조회하고 사용자에게 제공",
                success_criteria="실제 대시보드 목록이 포함된 응답",
                category="dashboard_list"
            ),
            
            TestScenario(
                name="사용가능한_대시보드_문의",
                description="어떤 대시보드가 있는지 자연어로 문의",
                user_input="어떤 대시보드들을 볼 수 있나요?",
                expected_agent="grafana_renderer_mcp_agent",
                expected_behavior="대시보드 목록 조회 및 안내",
                success_criteria="대시보드 이름들이 나열된 응답",
                category="dashboard_list"
            ),
            
            # 대시보드 렌더링 관련
            TestScenario(
                name="특정_대시보드_렌더링",
                description="Node Exporter Full 대시보드 렌더링 요청",
                user_input="Node Exporter Full 대시보드를 렌더링해주세요",
                expected_agent="grafana_renderer_mcp_agent",
                expected_behavior="대시보드를 렌더링하여 이미지 제공",
                success_criteria="렌더링된 이미지 데이터 또는 성공 메시지",
                category="dashboard_render"
            ),
            
            TestScenario(
                name="대시보드_시각화_요청",
                description="대시보드를 보여달라는 자연어 요청",
                user_input="Prometheus Stats 대시보드를 보여줘",
                expected_agent="grafana_renderer_mcp_agent",
                expected_behavior="해당 대시보드 렌더링",
                success_criteria="대시보드 렌더링 시도 및 결과 제공",
                category="dashboard_render"
            ),
            
            # 데이터 분석 관련
            TestScenario(
                name="시스템_성능_분석",
                description="시스템 성능 분석 요청",
                user_input="서버 성능을 분석해주세요",
                expected_agent="grafana_agent",
                expected_behavior="성능 메트릭 분석 수행",
                success_criteria="성능 분석 결과 또는 분석 과정 설명",
                category="data_analysis"
            ),
            
            TestScenario(
                name="메모리_사용량_확인",
                description="메모리 사용량 확인 요청",
                user_input="현재 메모리 사용량을 확인해주세요",
                expected_agent="grafana_agent",
                expected_behavior="메모리 메트릭 조회 및 분석",
                success_criteria="메모리 사용량 정보 제공",
                category="data_analysis"
            ),
            
            # 일반적인 상호작용
            TestScenario(
                name="인사_및_소개",
                description="기본적인 인사 및 시스템 소개 요청",
                user_input="안녕하세요, 무엇을 도와드릴 수 있나요?",
                expected_agent="supervisor",
                expected_behavior="친근한 인사 및 기능 소개",
                success_criteria="적절한 인사말과 기능 안내",
                category="general"
            ),
            
            TestScenario(
                name="도움말_요청",
                description="사용 가능한 기능에 대한 도움말 요청",
                user_input="어떤 기능들을 사용할 수 있나요?",
                expected_agent="supervisor",
                expected_behavior="사용 가능한 기능들 안내",
                success_criteria="기능 목록 및 사용법 안내",
                category="general"
            ),
            
            # 애매한 요청
            TestScenario(
                name="모호한_그라파나_요청",
                description="구체적이지 않은 Grafana 관련 요청",
                user_input="그라파나 관련해서 뭔가 해주세요",
                expected_agent="grafana_renderer_mcp_agent",
                expected_behavior="구체적인 요청 사항 문의 또는 기본 동작 수행",
                success_criteria="적절한 안내 또는 기본 기능 제공",
                category="ambiguous"
            ),
            
            # 오류 상황
            TestScenario(
                name="존재하지_않는_대시보드",
                description="존재하지 않는 대시보드 요청",
                user_input="NonExistent Dashboard를 렌더링해주세요",
                expected_agent="grafana_renderer_mcp_agent",
                expected_behavior="대시보드를 찾을 수 없다는 안내",
                success_criteria="적절한 오류 메시지 및 대안 제시",
                category="error_handling"
            )
        ]
        
        return scenarios
    
    async def run_single_test(self, scenario: TestScenario) -> TestResult:
        """단일 테스트 시나리오를 실행합니다."""
        
        print(f"\n🧪 테스트 실행: {scenario.name}")
        print(f"📝 설명: {scenario.description}")
        print(f"💬 입력: {scenario.user_input}")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Agent에 요청
            response_data = await process_chat_message(
                scenario.user_input, 
                f"test-{scenario.name}-{int(start_time)}"
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            agent_response = response_data.get('content', '')
            agent_used = response_data.get('agent_used', 'unknown')
            tools_used = response_data.get('tools_used', [])
            
            print(f"🤖 사용된 에이전트: {agent_used}")
            print(f"🛠️ 사용된 도구: {tools_used}")
            print(f"📊 응답 길이: {len(agent_response)} 문자")
            print(f"⏱️ 실행 시간: {execution_time:.2f}초")
            
            # LLM 평가
            print("🔍 LLM 평가 중...")
            llm_evaluation = await self.evaluator.evaluate_response(
                scenario, agent_response, agent_used, tools_used
            )
            
            success = llm_evaluation.get('success', False)
            print(f"✅ 평가 결과: {'성공' if success else '실패'} ({llm_evaluation.get('percentage', 0):.1f}%)")
            
            return TestResult(
                scenario=scenario,
                agent_response=agent_response,
                agent_used=agent_used,
                tools_used=tools_used,
                response_length=len(agent_response),
                execution_time=execution_time,
                llm_evaluation=llm_evaluation,
                success=success
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            print(f"❌ 테스트 실패: {e}")
            
            return TestResult(
                scenario=scenario,
                agent_response="",
                agent_used="error",
                tools_used=[],
                response_length=0,
                execution_time=execution_time,
                llm_evaluation={
                    "total_score": 0,
                    "max_score": 25,
                    "percentage": 0,
                    "success": False,
                    "summary": f"실행 오류: {str(e)}"
                },
                success=False,
                error=str(e)
            )
    
    async def run_all_tests(self) -> List[TestResult]:
        """모든 테스트 시나리오를 실행합니다."""
        
        print("🚀 종합적인 Agent 테스트 시작")
        print(f"📋 총 {len(self.test_scenarios)}개 시나리오 실행")
        print("=" * 60)
        
        results = []
        
        for i, scenario in enumerate(self.test_scenarios, 1):
            print(f"\n[{i}/{len(self.test_scenarios)}]", end="")
            
            result = await self.run_single_test(scenario)
            results.append(result)
            
            # 각 테스트 간 간격
            await asyncio.sleep(2)
        
        self.results = results
        return results
    
    def generate_report(self) -> str:
        """테스트 결과 리포트를 생성합니다."""
        
        if not self.results:
            return "테스트 결과가 없습니다."
        
        # 통계 계산
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        success_rate = (successful_tests / total_tests) * 100
        
        avg_score = sum(r.llm_evaluation.get('percentage', 0) for r in self.results) / total_tests
        avg_execution_time = sum(r.execution_time for r in self.results) / total_tests
        
        # 카테고리별 분석
        categories = {}
        for result in self.results:
            category = result.scenario.category
            if category not in categories:
                categories[category] = {'total': 0, 'success': 0, 'scores': []}
            
            categories[category]['total'] += 1
            if result.success:
                categories[category]['success'] += 1
            categories[category]['scores'].append(result.llm_evaluation.get('percentage', 0))
        
        # 리포트 생성
        report = f"""
📊 Agent 테스트 종합 리포트
{'=' * 50}

📈 전체 통계:
- 총 테스트: {total_tests}개
- 성공: {successful_tests}개
- 실패: {total_tests - successful_tests}개
- 성공률: {success_rate:.1f}%
- 평균 점수: {avg_score:.1f}%
- 평균 실행 시간: {avg_execution_time:.2f}초

📂 카테고리별 결과:
"""
        
        for category, stats in categories.items():
            cat_success_rate = (stats['success'] / stats['total']) * 100
            cat_avg_score = sum(stats['scores']) / len(stats['scores'])
            report += f"  • {category}: {cat_success_rate:.1f}% 성공 (평균 {cat_avg_score:.1f}점)\n"
        
        report += f"\n🔍 상세 결과:\n"
        
        for result in self.results:
            status = "✅ 성공" if result.success else "❌ 실패"
            score = result.llm_evaluation.get('percentage', 0)
            summary = result.llm_evaluation.get('summary', 'N/A')
            
            report += f"""
  📋 {result.scenario.name}
     - 상태: {status} ({score:.1f}%)
     - 에이전트: {result.agent_used}
     - 실행시간: {result.execution_time:.2f}초
     - 평가: {summary}
"""
            
            if result.error:
                report += f"     - 오류: {result.error}\n"
        
        # 개선 권장사항
        all_recommendations = []
        for result in self.results:
            recommendations = result.llm_evaluation.get('recommendations', [])
            all_recommendations.extend(recommendations)
        
        if all_recommendations:
            unique_recommendations = list(set(all_recommendations))
            report += f"\n💡 개선 권장사항:\n"
            for rec in unique_recommendations[:5]:  # 상위 5개만
                report += f"  • {rec}\n"
        
        report += f"\n📅 리포트 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return report
    
    def save_detailed_results(self, filename: str = None) -> str:
        """상세한 테스트 결과를 JSON 파일로 저장합니다."""
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"agent_test_results_{timestamp}.json"
        
        # 결과를 딕셔너리로 변환
        results_data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(self.results),
                'successful_tests': sum(1 for r in self.results if r.success)
            },
            'results': []
        }
        
        for result in self.results:
            result_data = {
                'scenario': {
                    'name': result.scenario.name,
                    'description': result.scenario.description,
                    'user_input': result.scenario.user_input,
                    'expected_agent': result.scenario.expected_agent,
                    'category': result.scenario.category
                },
                'response': {
                    'content': result.agent_response,
                    'agent_used': result.agent_used,
                    'tools_used': result.tools_used,
                    'response_length': result.response_length,
                    'execution_time': result.execution_time
                },
                'evaluation': result.llm_evaluation,
                'success': result.success,
                'error': result.error
            }
            results_data['results'].append(result_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        return filename

async def main():
    """메인 함수"""
    
    tester = ComprehensiveAgentTester()
    
    # 모든 테스트 실행
    results = await tester.run_all_tests()
    
    # 리포트 생성 및 출력
    print("\n" + "=" * 60)
    report = tester.generate_report()
    print(report)
    
    # 상세 결과 저장
    filename = tester.save_detailed_results()
    print(f"\n💾 상세 결과가 {filename}에 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 