"""
LLM Pipeline 하네스 통합 테스트 (pytest 게이트)

scripts/verify_llm_harness.py의 단계별 진단을 pytest에 통합.
실제 OpenAI 호출을 사용하므로 기본 skip — 실행은 --run-live-llm 플래그로:

    uv run pytest tests/integration/test_llm_pipeline_harness.py --run-live-llm

사용 시점:
- C1 회귀 방지 (LLM 경로 단절 재발 차단)
- 신규 모델 도입 시 빠른 검증
- CI에서 nightly 또는 manual trigger
"""

import os
import pytest
from dotenv import load_dotenv

# 모든 테스트가 live_llm 마커 — 기본 skip
pytestmark = pytest.mark.live_llm

load_dotenv()


# =============================================================================
# Phase A — 환경
# =============================================================================

def test_openai_api_key_is_set():
    """Phase A: OPENAI_API_KEY가 환경에 설정되어 있는가."""
    key = os.environ.get("OPENAI_API_KEY", "")
    assert key, "OPENAI_API_KEY가 설정되지 않음 (.env 또는 환경변수 확인)"
    assert len(key) >= 20, f"키 길이가 비정상적으로 짧음 ({len(key)}자)"


# =============================================================================
# Phase B/C — 두 모델 ping
# =============================================================================

@pytest.mark.parametrize(
    "model,role",
    [
        ("gpt-4o-mini", "LLMScorer가 사용하는 점수 산출 모델"),
        ("gpt-5.2", "LLMAnalyzer가 사용하는 분석 텍스트 모델"),
    ],
)
def test_openai_model_ping(model, role):
    """Phase B/C: 두 LLM 모델 모두 호출 가능한가.

    role은 실패 시 어떤 기능에 영향이 가는지 식별하기 위한 메타데이터.
    신모델은 max_tokens 대신 max_completion_tokens 사용.
    """
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with just: OK"}],
        max_completion_tokens=16,
    )
    content = (response.choices[0].message.content or "").strip()
    assert content, f"{model} ({role}) 응답이 비어 있음"


# =============================================================================
# Phase D — C1 통합 (가장 중요한 회귀 방지)
# =============================================================================

async def test_stock_analyzer_llm_path_not_fallback():
    """Phase D: StockAnalyzer LLM 경로가 살아있고 폴백되지 않는가.

    C1 버그(_llm_result_to_analysis_result 인자 불일치) 회귀 방지.
    LLM 호출 → StockAnalysisResult 변환까지의 전 경로를 1종목으로 검증.
    """
    from src.agents.analysis.stock_analyzer import StockAnalyzer

    analyzer = StockAnalyzer(use_llm=True)
    results = await analyzer.analyze_symbols(["005930"])  # 삼성전자

    assert "005930" in results, (
        f"삼성전자 분석 결과 없음 (반환 키: {list(results.keys())}). "
        "데이터 수집 또는 분석 호출 실패 가능성"
    )

    r = results["005930"]
    assert r.total_score > 0, "총점이 0 — LLM 호출 또는 점수 매핑 실패 의심"
    assert r.investment_grade, "투자 등급이 비어있음"
    assert not r.is_fallback, (
        f"LLM 경로가 폴백됨 — C1 회귀 가능성 — fallback_reason: {r.fallback_reason}"
    )
