"""
Sector Analysis Prompt

섹터 분석을 위한 LLM 프롬프트 템플릿.
섹터별 종합 분석과 전망을 생성합니다.
"""

from typing import Any, Dict, List


SECTOR_ANALYSIS_PROMPT = """당신은 한국 주식 시장의 섹터 전략을 전문으로 하는 시니어 애널리스트입니다.
아래 섹터 데이터를 분석하여 섹터 투자 전략과 전망을 JSON 형식으로 작성해주세요.

---

## 섹터 정보
- **섹터명**: {sector_name}
- **섹터 특성**: {sector_context}
- **분석 종목 수**: {stock_count}개
- **총 시가총액**: {total_market_cap:,.0f}억원

---

## 섹터 점수 (시가총액 가중 평균)
| 항목 | 점수 |
|------|------|
| **종합 점수** | {weighted_score:.1f}점 |
| 단순 평균 점수 | {simple_score:.1f}점 |
| 기술적 분석 | {technical_score:.1f}점 |
| 수급 분석 | {supply_score:.1f}점 |
| 펀더멘털 분석 | {fundamental_score:.1f}점 |
| 시장 환경 | {market_score:.1f}점 |

---

## 섹터 수급 현황
{supply_summary}

---

## 상위 종목 (점수순)
{top_stocks_info}

---

## JSON 응답 형식

다음 JSON 스키마에 맞춰 응답하세요:

```json
{{
  "reasoning": "<섹터의 현재 상황과 투자 매력도를 3-4문장으로 분석. 수급 현황을 반드시 포함>",
  "outlook": "<향후 1-3개월 섹터 전망을 2-3문장으로>",
  "key_drivers": ["<핵심 모멘텀 1>", "<핵심 모멘텀 2>", "<핵심 모멘텀 3>"],
  "investment_strategy": "<이 섹터에 대한 투자 전략을 2-3문장으로. 수급 기반 전략 포함>"
}}
```

---

## 분석 가이드라인

1. **수급 분석 중시**: 외국인/기관 순매수 비율이 높은 섹터는 긍정적으로 평가하세요.
   - 순매수 종목 비율 70% 이상: 강한 매수세
   - 순매수 종목 비율 50% 이상: 양호한 매수세
   - 순매수 종목 비율 30% 미만: 수급 약세

2. **섹터 특성 반영**: 해당 섹터의 산업 특성과 사이클을 고려하세요.

3. **매크로 관점**: 금리, 환율, 글로벌 경기 등 거시 환경과의 연관성을 고려하세요.

4. **구체적 근거**: 점수와 상위 종목 데이터를 인용하여 분석하세요.

5. **전문가 어조**: 기관 투자자 대상 섹터 리포트 수준의 어조를 유지하세요.

**JSON만 응답하세요. 다른 설명은 불필요합니다.**"""


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
    supply_data: Dict[str, Any] = None,
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
        top_stocks: 상위 종목 리스트 [{name, symbol, total_score, grade, supply_score, ...}, ...]
        supply_data: 섹터 수급 집계 데이터

    Returns:
        완성된 프롬프트 문자열
    """
    supply_data = supply_data or {}

    # 수급 요약 생성
    supply_lines = []
    foreign_buy_stocks = supply_data.get("foreign_net_buy_stocks", 0)
    inst_buy_stocks = supply_data.get("institution_net_buy_stocks", 0)
    total = supply_data.get("total_stocks", stock_count)
    foreign_ratio = supply_data.get("foreign_buy_ratio", 0)
    inst_ratio = supply_data.get("institution_buy_ratio", 0)

    supply_lines.append(f"- **외국인 순매수 종목**: {foreign_buy_stocks}개 / {total}개 ({foreign_ratio:.1f}%)")
    supply_lines.append(f"- **기관 순매수 종목**: {inst_buy_stocks}개 / {total}개 ({inst_ratio:.1f}%)")

    # 수급 판단
    if foreign_ratio >= 70:
        supply_lines.append("- **외국인 수급 판단**: 🟢 강한 매수세")
    elif foreign_ratio >= 50:
        supply_lines.append("- **외국인 수급 판단**: 🟡 양호한 매수세")
    elif foreign_ratio >= 30:
        supply_lines.append("- **외국인 수급 판단**: ⚪ 보합")
    else:
        supply_lines.append("- **외국인 수급 판단**: 🔴 매도 우위")

    if inst_ratio >= 70:
        supply_lines.append("- **기관 수급 판단**: 🟢 강한 매수세")
    elif inst_ratio >= 50:
        supply_lines.append("- **기관 수급 판단**: 🟡 양호한 매수세")
    elif inst_ratio >= 30:
        supply_lines.append("- **기관 수급 판단**: ⚪ 보합")
    else:
        supply_lines.append("- **기관 수급 판단**: 🔴 매도 우위")

    supply_summary = "\n".join(supply_lines)

    # 상위 종목 정보 포맷팅 (수급 포함)
    top_stocks_lines = []
    for i, stock in enumerate(top_stocks[:5], 1):
        name = stock.get('name', 'N/A')
        symbol = stock.get('symbol', 'N/A')
        score = stock.get('total_score', 0)
        grade = stock.get('grade', 'Hold')
        supply_score_val = stock.get('supply_score', 0)
        foreign_days = stock.get('foreign_consecutive', 0)
        inst_days = stock.get('institution_consecutive', 0)

        line = f"{i}. **{name}** ({symbol}): {score:.1f}점 [{grade}]"
        line += f" | 수급: {supply_score_val:.1f}점"
        if foreign_days > 0:
            line += f" | 외국인 {foreign_days}일 연속 순매수"
        if inst_days > 0:
            line += f" | 기관 {inst_days}일 연속 순매수"
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
        supply_summary=supply_summary,
        top_stocks_info=top_stocks_info,
    )
