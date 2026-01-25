"""
Sector Analysis Prompt

섹터 분석을 위한 LLM 프롬프트 템플릿.
섹터별 종합 분석과 전망을 생성합니다.
"""

from typing import Any, Dict, List


SECTOR_ANALYSIS_PROMPT = """당신은 한국 주식 시장의 섹터 전략을 전문으로 하는 애널리스트입니다.
아래 섹터 데이터를 분석하여 섹터 투자 전략과 전망을 JSON 형식으로 작성해주세요.

## 섹터 정보
- 섹터명: {sector_name}
- 섹터 특성: {sector_context}
- 분석 종목 수: {stock_count}개
- 총 시가총액: {total_market_cap:,.0f}억원

## 섹터 점수
- 시가총액 가중 평균 점수: {weighted_score:.1f}점
- 단순 평균 점수: {simple_score:.1f}점
- 기술적 분석: {technical_score:.1f}점
- 수급 분석: {supply_score:.1f}점
- 펀더멘털 분석: {fundamental_score:.1f}점
- 시장 환경: {market_score:.1f}점

## 상위 종목
{top_stocks_info}

## JSON 응답 형식

다음 JSON 스키마에 맞춰 응답하세요:

```json
{{
  "reasoning": "<섹터의 현재 상황과 투자 매력도를 2-3문장으로 분석>",
  "outlook": "<향후 1-3개월 섹터 전망을 2-3문장으로>",
  "key_drivers": ["<핵심 모멘텀 1>", "<핵심 모멘텀 2>", "<핵심 모멘텀 3>"],
  "investment_strategy": "<이 섹터에 대한 투자 전략을 2-3문장으로>"
}}
```

## 분석 가이드라인

1. **섹터 특성 반영**: 해당 섹터의 산업 특성과 사이클을 고려하세요.
2. **매크로 관점**: 금리, 환율, 글로벌 경기 등 거시 환경과의 연관성을 고려하세요.
3. **구체적 근거**: 점수와 상위 종목 데이터를 인용하여 분석하세요.
4. **전문가 어조**: 기관 투자자 대상 섹터 리포트 수준의 어조를 유지하세요.

JSON만 응답하세요. 다른 설명은 불필요합니다."""


def build_sector_analysis_prompt(
    sector_name: str,
    sector_context: str,
    stock_count: int,
    total_market_cap: float,
    weighted_score: float,
    simple_score: float,
    technical_score: float,
    supply_score: float,
    fundamental_score: float,
    market_score: float,
    top_stocks: List[Dict[str, Any]],
) -> str:
    """
    섹터 분석 프롬프트를 생성합니다.

    Args:
        sector_name: 섹터명
        sector_context: 섹터 특성 설명
        stock_count: 분석 종목 수
        total_market_cap: 총 시가총액 (억원)
        weighted_score: 시가총액 가중 평균 점수
        simple_score: 단순 평균 점수
        technical_score: 기술적 분석 점수
        supply_score: 수급 분석 점수
        fundamental_score: 펀더멘털 점수
        market_score: 시장 환경 점수
        top_stocks: 상위 종목 리스트 [{name, symbol, total_score, grade}, ...]

    Returns:
        완성된 프롬프트 문자열
    """
    # 상위 종목 정보 포맷팅
    top_stocks_lines = []
    for i, stock in enumerate(top_stocks[:5], 1):
        line = f"{i}. {stock.get('name', 'N/A')} ({stock.get('symbol', 'N/A')}): {stock.get('total_score', 0):.1f}점 [{stock.get('grade', 'Hold')}]"
        top_stocks_lines.append(line)

    top_stocks_info = "\n".join(top_stocks_lines) if top_stocks_lines else "- 데이터 없음"

    return SECTOR_ANALYSIS_PROMPT.format(
        sector_name=sector_name,
        sector_context=sector_context,
        stock_count=stock_count,
        total_market_cap=total_market_cap,
        weighted_score=weighted_score,
        simple_score=simple_score,
        technical_score=technical_score,
        supply_score=supply_score,
        fundamental_score=fundamental_score,
        market_score=market_score,
        top_stocks_info=top_stocks_info,
    )
