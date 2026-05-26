"""
LLM Pipeline Verification Harness

전체 --daily(32분)를 돌리지 않고도 LLM 경로의 정상성을 단계별로 검증한다.

  Phase A — 환경 (.env, OPENAI_API_KEY)
  Phase B — gpt-4o-mini ping (LLMScorer가 사용하는 모델)
  Phase C — gpt-5.2 ping       (LLMAnalyzer가 사용하는 모델)
  Phase D — 통합: StockAnalyzer로 종목 1개 분석 → is_fallback=False 확인
            (C1 수정으로 LLM 경로가 실제 살아났는지 검증)

각 단계의 PASS/FAIL이 명확히 출력되어 회귀 시 어느 층에서 깨졌는지 즉시 식별된다.

실행:
    uv run python scripts/verify_llm_harness.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# src 모듈 import 경로
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

# 진단 출력만 보고 싶으므로 라이브러리 로그를 최소화
logging.basicConfig(level=logging.WARNING)


# =============================================================================
# Phase A — 환경
# =============================================================================

def phase_a_env() -> bool:
    print("=" * 64)
    print("Phase A — 환경 점검")
    print("=" * 64)

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        print("❌ OPENAI_API_KEY 미설정")
        return False

    # 보안: prefix/suffix만 노출
    prefix = key[:7]
    suffix = key[-4:] if len(key) > 11 else ""
    print(f"✅ OPENAI_API_KEY: {prefix}…{suffix}  (총 {len(key)}자)")
    return True


# =============================================================================
# Phase B/C — 모델 ping (최소 토큰 호출)
# =============================================================================

def phase_model_ping(model: str, label: str) -> bool:
    """모델 ping.

    신모델(gpt-5.x 계열)은 'max_tokens' 미지원 → 'max_completion_tokens' 사용.
    src/core/llm.py가 이미 max_completion_tokens를 쓰므로 같은 방식으로 ping.
    """
    print()
    print("=" * 64)
    print(f"Phase {label} — '{model}' 모델 ping")
    print("=" * 64)

    try:
        from openai import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_completion_tokens=16,
        )
        content = (response.choices[0].message.content or "").strip()
        print(f"✅ {model} 응답: {content!r}")
        return True
    except Exception as e:
        err_type = type(e).__name__
        msg = str(e).splitlines()[0][:280]
        print(f"❌ {model} 실패: {err_type}")
        print(f"   {msg}")
        return False


# =============================================================================
# Phase D — 통합 검증 (C1 수정 효과)
# =============================================================================

async def phase_d_integration() -> bool:
    print()
    print("=" * 64)
    print("Phase D — 통합: StockAnalyzer 1종목 (C1 수정 검증)")
    print("=" * 64)

    from src.agents.analysis.stock_analyzer import StockAnalyzer

    try:
        analyzer = StockAnalyzer(use_llm=True)
        # analyze_symbols 반환: Dict[symbol, StockAnalysisResult]
        results = await analyzer.analyze_symbols(["005930"])  # 삼성전자
    except Exception as e:
        err_type = type(e).__name__
        print(f"❌ 분석 호출 예외: {err_type}: {str(e)[:300]}")
        return False

    r = results.get("005930") if results else None
    if r is None:
        print(f"❌ 분석 결과 없음 (반환 키: {list(results.keys()) if results else '[]'})")
        return False
    print(f"종목      : {r.name} ({r.symbol})")
    print(f"총점      : {r.total_score:.1f} / 100")
    print(f"등급      : {r.investment_grade}")
    print(f"is_fallback: {r.is_fallback}")

    if r.is_fallback:
        reason = getattr(r, "fallback_reason", "") or "(사유 미기록)"
        print(f"   → fallback_reason: {reason}")
        print("❌ LLM 경로 실패 → RubricEngine 폴백 (C1이 살아있어도 다른 층에서 막힘)")
        return False

    summary = (getattr(r, "summary", "") or "").strip()
    snippet = summary[:120].replace("\n", " ")
    print(f"summary   : {snippet}{'…' if len(summary) > 120 else ''}")
    print("✅ LLM 경로 정상 (C1 수정 효과 확인)")
    return True


# =============================================================================
# Entry
# =============================================================================

async def main() -> int:
    results: dict[str, bool] = {}

    results["A"] = phase_a_env()
    if not results["A"]:
        print("\n환경 점검 실패 — 후속 단계 중단")
        return 1

    results["B"] = phase_model_ping("gpt-4o-mini", "B")
    results["C"] = phase_model_ping("gpt-5.2", "C")
    results["D"] = await phase_d_integration()

    print()
    print("=" * 64)
    print("종합 결과")
    print("=" * 64)
    for phase, ok in results.items():
        print(f"  Phase {phase}: {'✅ PASS' if ok else '❌ FAIL'}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
