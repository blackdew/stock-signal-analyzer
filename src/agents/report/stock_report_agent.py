"""
Stock Report Agent

개별 종목의 마크다운 리포트를 생성하는 에이전트.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.analysis.stock_analyzer import StockAnalysisResult
from src.core.config import INVESTMENT_GRADES


# =============================================================================
# 상수 정의
# =============================================================================

# 투자 등급별 별점
GRADE_STARS = {
    "Strong Buy": "⭐⭐⭐⭐⭐",
    "Buy": "⭐⭐⭐⭐",
    "Hold": "⭐⭐⭐",
    "Sell": "⭐⭐",
    "Strong Sell": "⭐",
}

# 리포트 출력 디렉토리
DEFAULT_OUTPUT_DIR = Path("output/reports/stocks")


# =============================================================================
# StockReportAgent
# =============================================================================


@dataclass
class StockReportAgent(BaseAgent):
    """
    개별 종목 리포트 생성 에이전트

    주요 기능:
    - StockAnalysisResult를 마크다운 리포트로 변환
    - 병렬 리포트 생성 (asyncio.gather)
    - output/reports/stocks/ 디렉토리에 저장

    사용 예시:
        agent = StockReportAgent()
        reports = await agent.generate_reports(stock_results)
    """

    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)

    def __post_init__(self):
        """출력 디렉토리 생성 및 로거 초기화"""
        super().__post_init__()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def collect(self, symbols: List[str]) -> Dict[str, Any]:
        """
        BaseAgent 인터페이스 구현.
        """
        return {}

    async def generate_reports(
        self,
        stocks: List[StockAnalysisResult],
        date_str: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        여러 종목의 리포트를 병렬로 생성합니다.

        Args:
            stocks: 종목 분석 결과 리스트
            date_str: 날짜 문자열 (미사용, 폴더명에서 날짜 사용)

        Returns:
            종목코드를 키로 하는 리포트 파일 경로 딕셔너리
        """
        self._log_info(f"Generating {len(stocks)} stock reports")

        # 병렬 생성
        tasks = [
            self._generate_single_report(stock)
            for stock in stocks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 집계
        report_paths: Dict[str, str] = {}
        for stock, result in zip(stocks, results):
            if isinstance(result, Exception):
                self._log_error(f"Failed to generate report for {stock.symbol}: {result}")
            else:
                report_paths[stock.symbol] = result

        self._log_info(f"Generated {len(report_paths)}/{len(stocks)} reports")
        return report_paths

    async def _generate_single_report(
        self,
        stock: StockAnalysisResult,
    ) -> str:
        """
        단일 종목 리포트를 생성합니다.

        Args:
            stock: 종목 분석 결과

        Returns:
            생성된 리포트 파일 경로
        """
        # 마크다운 생성
        content = self._render_markdown(stock)

        # 파일 저장 (날짜 없이, 폴더명에 날짜 포함됨)
        filename = f"{stock.symbol}_{stock.name}.md"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def _render_markdown(self, stock: StockAnalysisResult) -> str:
        """
        마크다운 리포트를 렌더링합니다.

        Args:
            stock: 종목 분석 결과

        Returns:
            마크다운 문자열
        """
        # 기본 정보
        grade_stars = GRADE_STARS.get(stock.investment_grade, "⭐⭐⭐")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        market_cap_str = self._format_market_cap(stock.market_cap)

        # 그룹명 한글화
        group_name = self._translate_group_name(stock.group)

        # RubricResult에서 세부 정보 추출
        rubric = stock.rubric_result
        details = self._extract_rubric_details(rubric)

        # 투자 의견 생성
        opinion = self._generate_opinion(stock)

        # 값 포맷팅 헬퍼 함수들
        def fmt_price(val):
            return f"{val:,.0f}원" if val else "N/A"

        def fmt_pct(val):
            return f"{val:.1f}%" if val is not None else "N/A"

        def fmt_num(val, decimals=1):
            return f"{val:.{decimals}f}" if val is not None else "N/A"

        def fmt_days(val):
            return f"{val}일 연속" if val else "0일"

        def fmt_amount(val):
            return f"{val:,.0f}억원" if val else "N/A"

        # 마크다운 템플릿 렌더링
        md = f"""# {stock.name} ({stock.symbol}) 투자 분석 리포트

> 생성일시: {now}
> 분석 그룹: {group_name}

---

## 📊 종합 평가

| 항목 | 값 |
|------|-----|
| **투자 점수** | {stock.total_score:.1f}/100점 |
| **투자 등급** | {grade_stars} {stock.investment_grade} |
| **섹터** | {stock.sector or "N/A"} |
| **시가총액** | {market_cap_str} (순위: {stock.final_rank or stock.rank_in_group}위) |
| **현재가** | {fmt_price(details['current_price'])} |

---

## 📈 기술적 분석 ({stock.technical_score:.1f}/25점)

### 추세 ({details['trend_score']:.1f}/6점)
| 지표 | 값 |
|------|-----|
| MA20 | {fmt_price(details['ma20_value'])} |
| MA60 | {fmt_price(details['ma60_value'])} |
| 판정 | **{details['trend_verdict']}** |

### 모멘텀 ({details['rsi_score']:.1f}/6점)
| 지표 | 값 |
|------|-----|
| RSI(14) | {fmt_num(details['rsi'])} |
| 판정 | **{details['rsi_verdict']}** |

### 지지/저항 ({details['support_score']:.1f}/6점)
| 지표 | 값 |
|------|-----|
| 52주 최저가 | {fmt_price(details['low_52w'])} |
| 52주 최고가 | {fmt_price(details['high_52w'])} |
| 52주 내 위치 | {fmt_pct(details['position_52w'])} |
| 판정 | **{details['support_verdict']}** |

### MACD ({details['macd_score']:.1f}/4점)
| 지표 | 값 |
|------|-----|
| MACD | {fmt_num(details['macd_value'], 2)} |
| Signal | {fmt_num(details['macd_signal_value'], 2)} |
| 판정 | **{details['macd_verdict']}** |

### ADX ({details['adx_score']:.1f}/3점)
| 지표 | 값 |
|------|-----|
| ADX(14) | {fmt_num(details['adx_value'])} |
| 판정 | **{details['adx_verdict']}** |

---

## 💰 수급 분석 ({stock.supply_score:.1f}/20점)

### 외국인 ({details['foreign_score']:.1f}/8점)
| 지표 | 값 |
|------|-----|
| 연속 순매수 | {fmt_days(details['foreign_consecutive_days'])} |
| 판정 | **{details['foreign_verdict']}** |

### 기관 ({details['institution_score']:.1f}/8점)
| 지표 | 값 |
|------|-----|
| 연속 순매수 | {fmt_days(details['institution_consecutive_days'])} |
| 판정 | **{details['institution_verdict']}** |

### 거래대금 ({details['trading_score']:.1f}/4점)
| 지표 | 값 |
|------|-----|
| 당일 거래대금 | {fmt_amount(details['trading_value_amount'])} |
| 판정 | **{details['trading_verdict']}** |

---

## 📑 펀더멘털 분석 ({stock.fundamental_score:.1f}/20점)

### PER ({details['per_score']:.1f}/4점)
| 지표 | 값 |
|------|-----|
| 현재 PER | {fmt_num(details['per_value'], 2)}배 |
| 업종 평균 PER | {fmt_num(details['sector_avg_per'], 2)}배 |
| 판정 | **{details['per_verdict']}** |

### PBR ({details['pbr_score']:.1f}/4점)
| 지표 | 값 |
|------|-----|
| 현재 PBR | {fmt_num(details['pbr_value'], 2)}배 |
| 업종 평균 PBR | {fmt_num(details['sector_avg_pbr'], 2)}배 |
| 판정 | **{details['pbr_verdict']}** |

### ROE ({details['roe_score']:.1f}/4점)
| 지표 | 값 |
|------|-----|
| ROE | {fmt_pct(details['roe_value'])} |
| 판정 | **{details['roe_verdict']}** |

### 성장성 ({details['growth_score']:.1f}/5점)
| 지표 | 값 |
|------|-----|
| 영업이익 성장률 (YoY) | {fmt_pct(details['op_growth_value'])} |
| 판정 | **{details['growth_verdict']}** |

### 재무건전성 ({details['debt_score']:.1f}/3점)
| 지표 | 값 |
|------|-----|
| 부채비율 | {fmt_pct(details['debt_ratio_value'])} |
| 판정 | **{details['debt_verdict']}** |

---

## 🌐 시장 환경 ({stock.market_score:.1f}/15점)

### 뉴스 센티먼트 ({details['news_score']:.1f}/7.5점)
- 판정: **{details['news_verdict']}**

### 섹터 모멘텀 ({details['sector_momentum_score']:.1f}/3.75점)
- 판정: **{details['sector_momentum_verdict']}**

### 애널리스트 전망 ({details['analyst_score']:.1f}/3.75점)
- 판정: **{details['analyst_verdict']}**

---

## ⚠️ 리스크 평가 ({stock.risk_score:.1f}/10점)

### 변동성 ({details['volatility_score']:.1f}/4점)
| 지표 | 값 |
|------|-----|
| ATR(%) | {fmt_pct(details['atr_pct_value'])} |
| 판정 | **{details['volatility_verdict']}** |

### 베타 ({details['beta_score']:.1f}/3점)
| 지표 | 값 |
|------|-----|
| 베타 | {fmt_num(details['beta_value'], 2)} |
| 판정 | **{details['beta_verdict']}** |

### 하방 리스크 ({details['downside_score']:.1f}/3점)
| 지표 | 값 |
|------|-----|
| 최대 낙폭 | {fmt_pct(details['max_drawdown_value'])} |
| 판정 | **{details['downside_verdict']}** |

---

## 📊 상대 강도 ({stock.relative_strength_score:.1f}/10점)

### 섹터 내 순위 ({details['sector_rank_score']:.1f}/5점)
| 지표 | 값 |
|------|-----|
| 섹터 내 순위 | {details['sector_rank_value'] or 'N/A'}위 / {details['sector_total_value'] or 'N/A'}개 |
| 판정 | **{details['sector_rank_verdict']}** |

### 시장 대비 알파 ({details['alpha_score']:.1f}/5점)
| 지표 | 값 |
|------|-----|
| 종목 20일 수익률 | {fmt_pct(details['stock_return_value'])} |
| 시장 20일 수익률 | {fmt_pct(details['market_return_value'])} |
| 알파 | {fmt_pct(details['alpha_value'])} |
| 판정 | **{details['alpha_verdict']}** |

---

## 💡 투자 의견

{opinion}

---

*이 리포트는 자동 생성되었으며, 투자 판단의 참고 자료로만 활용하시기 바랍니다.*
"""
        return md

    def _extract_rubric_details(self, rubric) -> Dict[str, Any]:
        """
        RubricResult에서 세부 정보를 추출합니다.
        """
        defaults = {
            # 기술적 분석
            "trend_score": 3.0, "trend_verdict": "중립",
            "rsi_score": 3.0, "rsi": 50.0, "rsi_verdict": "중립",
            "support_score": 3.0, "support_verdict": "중립",
            "macd_score": 2.0, "macd_verdict": "중립",
            "adx_score": 1.5, "adx_verdict": "중립",
            # 기술적 분석 - 원본 값
            "ma20_value": None, "ma60_value": None,
            "macd_value": None, "macd_signal_value": None,
            "adx_value": None,
            "current_price": None, "low_52w": None, "high_52w": None, "position_52w": None,
            # 수급 분석
            "foreign_score": 4.0, "foreign_verdict": "중립",
            "institution_score": 4.0, "institution_verdict": "중립",
            "trading_score": 2.0, "trading_verdict": "중립",
            # 수급 분석 - 원본 값
            "foreign_consecutive_days": 0, "institution_consecutive_days": 0,
            "trading_value_amount": None,
            # 펀더멘털 분석
            "per_score": 2.0, "per_verdict": "중립",
            "pbr_score": 2.0, "pbr_verdict": "중립",
            "roe_score": 2.0, "roe_verdict": "중립",
            "growth_score": 2.5, "growth_verdict": "중립",
            "debt_score": 1.5, "debt_verdict": "중립",
            # 펀더멘털 분석 - 원본 값
            "per_value": None, "pbr_value": None, "roe_value": None,
            "sector_avg_per": None, "sector_avg_pbr": None,
            "op_growth_value": None, "debt_ratio_value": None,
            # 시장 환경
            "news_score": 3.75, "news_verdict": "중립",
            "sector_momentum_score": 1.875, "sector_momentum_verdict": "중립",
            "analyst_score": 1.875, "analyst_verdict": "중립",
            # 리스크 평가
            "volatility_score": 2.0, "volatility_verdict": "중립",
            "beta_score": 1.5, "beta_verdict": "중립",
            "downside_score": 1.5, "downside_verdict": "중립",
            # 리스크 평가 - 원본 값
            "atr_pct_value": None, "beta_value": None, "max_drawdown_value": None,
            # 상대 강도
            "sector_rank_score": 2.5, "sector_rank_verdict": "중립",
            "alpha_score": 2.5, "alpha_verdict": "중립",
            # 상대 강도 - 원본 값
            "sector_rank_value": None, "sector_total_value": None,
            "stock_return_value": None, "market_return_value": None, "alpha_value": None,
        }

        if rubric is None:
            return defaults

        # 기술적 분석 세부
        if rubric.technical and rubric.technical.details:
            details = rubric.technical.details
            defaults["trend_score"] = details.get("trend", 3.0)
            defaults["trend_verdict"] = self._score_to_verdict(details.get("trend", 3.0), 6)
            defaults["rsi_score"] = details.get("rsi", 3.0)
            defaults["rsi"] = details.get("rsi_value", 50.0)
            defaults["rsi_verdict"] = self._rsi_to_verdict(details.get("rsi_value", 50.0))
            defaults["support_score"] = details.get("support_resistance", 3.0)
            defaults["support_verdict"] = self._score_to_verdict(details.get("support_resistance", 3.0), 6)
            defaults["macd_score"] = details.get("macd", 2.0)
            defaults["macd_verdict"] = self._score_to_verdict(details.get("macd", 2.0), 4)
            defaults["adx_score"] = details.get("adx", 1.5)
            defaults["adx_verdict"] = self._score_to_verdict(details.get("adx", 1.5), 3)
            # 원본 값
            defaults["ma20_value"] = details.get("ma20_value")
            defaults["ma60_value"] = details.get("ma60_value")
            defaults["macd_value"] = details.get("macd_value")
            defaults["macd_signal_value"] = details.get("macd_signal_value")
            defaults["adx_value"] = details.get("adx_value")
            defaults["current_price"] = details.get("current_price")
            defaults["low_52w"] = details.get("low_52w")
            defaults["high_52w"] = details.get("high_52w")
            defaults["position_52w"] = details.get("position_52w")

        # 수급 분석 세부
        if rubric.supply and rubric.supply.details:
            details = rubric.supply.details
            defaults["foreign_score"] = details.get("foreign", 4.0)
            defaults["foreign_verdict"] = self._score_to_verdict(details.get("foreign", 4.0), 8)
            defaults["institution_score"] = details.get("institution", 4.0)
            defaults["institution_verdict"] = self._score_to_verdict(details.get("institution", 4.0), 8)
            defaults["trading_score"] = details.get("trading_value", 2.0)
            defaults["trading_verdict"] = self._score_to_verdict(details.get("trading_value", 2.0), 4)
            # 원본 값
            defaults["foreign_consecutive_days"] = details.get("foreign_consecutive_days", 0)
            defaults["institution_consecutive_days"] = details.get("institution_consecutive_days", 0)
            defaults["trading_value_amount"] = details.get("trading_value_amount")

        # 펀더멘털 분석 세부
        if rubric.fundamental and rubric.fundamental.details:
            details = rubric.fundamental.details
            defaults["per_score"] = details.get("per", 2.0)
            defaults["per_verdict"] = self._score_to_verdict(details.get("per", 2.0), 4)
            defaults["pbr_score"] = details.get("pbr", 2.0)
            defaults["pbr_verdict"] = self._score_to_verdict(details.get("pbr", 2.0), 4)
            defaults["roe_score"] = details.get("roe", 2.0)
            defaults["roe_verdict"] = self._score_to_verdict(details.get("roe", 2.0), 4)
            defaults["growth_score"] = details.get("growth", 2.5)
            defaults["growth_verdict"] = self._score_to_verdict(details.get("growth", 2.5), 5)
            defaults["debt_score"] = details.get("debt", 1.5)
            defaults["debt_verdict"] = self._score_to_verdict(details.get("debt", 1.5), 3)
            # 원본 값
            defaults["per_value"] = details.get("per_value")
            defaults["pbr_value"] = details.get("pbr_value")
            defaults["roe_value"] = details.get("roe_value")
            defaults["sector_avg_per"] = details.get("sector_avg_per")
            defaults["sector_avg_pbr"] = details.get("sector_avg_pbr")
            defaults["op_growth_value"] = details.get("op_growth_value")
            defaults["debt_ratio_value"] = details.get("debt_ratio_value")

        # 시장 환경 세부
        if rubric.market and rubric.market.details:
            details = rubric.market.details
            defaults["news_score"] = details.get("news", 3.75)
            defaults["news_verdict"] = self._score_to_verdict(details.get("news", 3.75), 7.5)
            defaults["sector_momentum_score"] = details.get("sector_momentum", 1.875)
            defaults["sector_momentum_verdict"] = self._score_to_verdict(details.get("sector_momentum", 1.875), 3.75)
            defaults["analyst_score"] = details.get("analyst", 1.875)
            defaults["analyst_verdict"] = self._score_to_verdict(details.get("analyst", 1.875), 3.75)

        # 리스크 평가 세부 (V2)
        if rubric.risk and rubric.risk.details:
            details = rubric.risk.details
            defaults["volatility_score"] = details.get("volatility", 2.0)
            defaults["volatility_verdict"] = self._score_to_verdict(details.get("volatility", 2.0), 4)
            defaults["beta_score"] = details.get("beta", 1.5)
            defaults["beta_verdict"] = self._score_to_verdict(details.get("beta", 1.5), 3)
            defaults["downside_score"] = details.get("downside_risk", 1.5)
            defaults["downside_verdict"] = self._score_to_verdict(details.get("downside_risk", 1.5), 3)
            # 원본 값
            defaults["atr_pct_value"] = details.get("atr_pct_value")
            defaults["beta_value"] = details.get("beta_value")
            defaults["max_drawdown_value"] = details.get("max_drawdown_value")

        # 상대 강도 세부 (V2)
        if rubric.relative_strength and rubric.relative_strength.details:
            details = rubric.relative_strength.details
            defaults["sector_rank_score"] = details.get("sector_rank", 2.5)
            defaults["sector_rank_verdict"] = self._score_to_verdict(details.get("sector_rank", 2.5), 5)
            defaults["alpha_score"] = details.get("alpha", 2.5)
            defaults["alpha_verdict"] = self._score_to_verdict(details.get("alpha", 2.5), 5)
            # 원본 값
            defaults["sector_rank_value"] = details.get("sector_rank_value")
            defaults["sector_total_value"] = details.get("sector_total_value")
            defaults["stock_return_value"] = details.get("stock_return_value")
            defaults["market_return_value"] = details.get("market_return_value")
            defaults["alpha_value"] = details.get("alpha_value")

        return defaults

    def _score_to_verdict(self, score: float, max_score: float) -> str:
        """
        점수를 판정 문자열로 변환합니다.
        """
        ratio = score / max_score if max_score > 0 else 0.5
        if ratio >= 0.8:
            return "매우 우수"
        elif ratio >= 0.6:
            return "우수"
        elif ratio >= 0.4:
            return "중립"
        elif ratio >= 0.2:
            return "부정적"
        else:
            return "매우 부정적"

    def _rsi_to_verdict(self, rsi: float) -> str:
        """
        RSI 값을 판정 문자열로 변환합니다.
        """
        if rsi >= 70:
            return "과매수 - 조정 가능성"
        elif rsi >= 60:
            return "강세"
        elif rsi >= 40:
            return "중립"
        elif rsi >= 30:
            return "약세"
        else:
            return "과매도 - 반등 가능성"

    def _format_market_cap(self, market_cap: float) -> str:
        """
        시가총액을 포맷팅합니다. (억원 단위)
        """
        if market_cap >= 10000:
            return f"{market_cap / 10000:.1f}조원"
        else:
            return f"{market_cap:,.0f}억원"

    def _translate_group_name(self, group: str) -> str:
        """
        그룹명을 한글로 변환합니다.
        """
        translations = {
            "kospi_top10": "KOSPI 시총 상위 10",
            "kospi_11_20": "KOSPI 시총 11~20위",
            "kosdaq_top10": "KOSDAQ 시총 상위 10",
            "custom": "커스텀 분석",
        }
        if group.startswith("sector_"):
            sector_name = group.replace("sector_", "")
            return f"섹터: {sector_name}"
        return translations.get(group, group)

    def _generate_opinion(self, stock: StockAnalysisResult) -> str:
        """
        투자 의견을 자동 생성합니다. (템플릿 기반, LLM 미사용)
        최소 3문장 이상의 상세한 의견을 생성합니다.
        """
        opinions = []
        strengths = []
        weaknesses = []

        # 1. 종합 등급 기반 도입부
        if stock.total_score >= 80:
            opinions.append(f"**{stock.name}**은(는) 종합 점수 {stock.total_score:.1f}점으로 **Strong Buy** 등급을 받았습니다.")
            opinions.append("현재 매우 매력적인 투자 기회로 판단되며, 적극적인 매수를 검토해 볼 수 있습니다.")
        elif stock.total_score >= 60:
            opinions.append(f"**{stock.name}**은(는) 종합 점수 {stock.total_score:.1f}점으로 **Buy** 등급을 받았습니다.")
            opinions.append("긍정적인 투자 전망을 보이고 있어 신규 진입 또는 추가 매수를 고려해 볼 만합니다.")
        elif stock.total_score >= 40:
            opinions.append(f"**{stock.name}**은(는) 종합 점수 {stock.total_score:.1f}점으로 **Hold** 등급을 받았습니다.")
            opinions.append("현재 관망이 적절한 시점이며, 추세 전환 신호를 확인한 후 매매 결정을 내리는 것이 좋습니다.")
        else:
            opinions.append(f"**{stock.name}**은(는) 종합 점수 {stock.total_score:.1f}점으로 **Sell** 등급을 받았습니다.")
            opinions.append("당분간 투자에 신중할 필요가 있으며, 기존 보유자는 손절 또는 비중 축소를 고려해야 합니다.")

        # 2. 강점/약점 분석
        # 기술적 분석 (25점 만점)
        tech_ratio = stock.technical_score / 25 * 100
        if tech_ratio >= 70:
            strengths.append(f"기술적 지표가 상승 추세({stock.technical_score:.1f}/25점)")
        elif tech_ratio <= 40:
            weaknesses.append(f"기술적 지표가 약세({stock.technical_score:.1f}/25점)")

        # 수급 분석 (20점 만점)
        supply_ratio = stock.supply_score / 20 * 100
        if supply_ratio >= 70:
            strengths.append(f"외국인/기관 수급 양호({stock.supply_score:.1f}/20점)")
        elif supply_ratio <= 40:
            weaknesses.append(f"수급 부진({stock.supply_score:.1f}/20점)")

        # 펀더멘털 분석 (20점 만점)
        fund_ratio = stock.fundamental_score / 20 * 100
        if fund_ratio >= 70:
            strengths.append(f"펀더멘털 우수({stock.fundamental_score:.1f}/20점)")
        elif fund_ratio <= 40:
            weaknesses.append(f"펀더멘털 미흡({stock.fundamental_score:.1f}/20점)")

        # 시장 환경 (15점 만점)
        market_ratio = stock.market_score / 15 * 100
        if market_ratio >= 70:
            strengths.append(f"시장 환경 긍정적({stock.market_score:.1f}/15점)")
        elif market_ratio <= 40:
            weaknesses.append(f"시장 환경 부정적({stock.market_score:.1f}/15점)")

        # 리스크 평가 (10점 만점)
        risk_ratio = stock.risk_score / 10 * 100
        if risk_ratio >= 70:
            strengths.append(f"리스크 낮음({stock.risk_score:.1f}/10점)")
        elif risk_ratio <= 40:
            weaknesses.append(f"리스크 높음({stock.risk_score:.1f}/10점)")

        # 상대 강도 (10점 만점)
        rs_ratio = stock.relative_strength_score / 10 * 100
        if rs_ratio >= 70:
            strengths.append(f"상대 강도 우수({stock.relative_strength_score:.1f}/10점)")
        elif rs_ratio <= 40:
            weaknesses.append(f"상대 강도 미흡({stock.relative_strength_score:.1f}/10점)")

        # 3. 강점 서술
        if strengths:
            opinions.append(f"\n\n**주요 강점**: {', '.join(strengths)}.")

        # 4. 약점 서술
        if weaknesses:
            opinions.append(f"\n\n**주의 사항**: {', '.join(weaknesses)}.")

        # 5. 구체적인 권고사항 추가
        if stock.total_score >= 70:
            opinions.append("\n\n**권고사항**: 분할 매수 전략을 활용하여 포지션을 구축하는 것이 좋습니다. 목표가는 52주 최고가 부근으로 설정할 수 있으며, 손절가는 최근 지지선 하단에 설정하는 것을 권장합니다.")
        elif stock.total_score >= 50:
            opinions.append("\n\n**권고사항**: 현재 가격대에서는 관망하며 추세 전환 신호를 기다리는 것이 좋습니다. RSI가 과매도 구간에 진입하거나 거래량이 급증하는 시점에 진입을 고려해 볼 수 있습니다.")
        else:
            opinions.append("\n\n**권고사항**: 추가 하락 가능성이 있으므로 신규 진입은 자제하고, 기존 보유자는 반등 시 비중 축소를 고려해야 합니다. 기술적 지지선과 펀더멘털 개선 신호를 확인한 후 재진입 여부를 결정하시기 바랍니다.")

        return "".join(opinions)
