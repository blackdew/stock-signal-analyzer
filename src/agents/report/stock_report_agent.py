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

---

## 📈 기술적 분석 ({stock.technical_score:.1f}/25점)

### 추세 ({details['trend_score']:.1f}/6점)
- MA20 vs MA60 비교
- 판정: {details['trend_verdict']}

### 모멘텀 ({details['rsi_score']:.1f}/6점)
- RSI: {details['rsi']:.1f}
- 판정: {details['rsi_verdict']}

### 지지/저항 ({details['support_score']:.1f}/6점)
- 52주 내 위치 분석
- 판정: {details['support_verdict']}

### MACD ({details['macd_score']:.1f}/4점)
- 판정: {details['macd_verdict']}

### ADX ({details['adx_score']:.1f}/3점)
- 판정: {details['adx_verdict']}

---

## 💰 수급 분석 ({stock.supply_score:.1f}/20점)

### 외국인 ({details['foreign_score']:.1f}/8점)
- 최근 수급 동향 분석
- 판정: {details['foreign_verdict']}

### 기관 ({details['institution_score']:.1f}/8점)
- 최근 수급 동향 분석
- 판정: {details['institution_verdict']}

### 거래대금 ({details['trading_score']:.1f}/4점)
- 판정: {details['trading_verdict']}

---

## 📑 펀더멘털 분석 ({stock.fundamental_score:.1f}/20점)

### PER ({details['per_score']:.1f}/4점)
- 판정: {details['per_verdict']}

### PBR ({details['pbr_score']:.1f}/4점)
- 판정: {details['pbr_verdict']}

### ROE ({details['roe_score']:.1f}/4점)
- 판정: {details['roe_verdict']}

### 성장성 ({details['growth_score']:.1f}/5점)
- 영업이익 및 매출 성장률 분석
- 판정: {details['growth_verdict']}

### 재무건전성 ({details['debt_score']:.1f}/3점)
- 부채비율 분석
- 판정: {details['debt_verdict']}

---

## 🌐 시장 환경 ({stock.market_score:.1f}/15점)

### 뉴스 센티먼트 ({details['news_score']:.1f}/7.5점)
- 판정: {details['news_verdict']}

### 섹터 모멘텀 ({details['sector_momentum_score']:.1f}/3.75점)
- 판정: {details['sector_momentum_verdict']}

### 애널리스트 전망 ({details['analyst_score']:.1f}/3.75점)
- 판정: {details['analyst_verdict']}

---

## ⚠️ 리스크 평가 ({stock.risk_score:.1f}/10점)

### 변동성 ({details['volatility_score']:.1f}/4점)
- 판정: {details['volatility_verdict']}

### 베타 ({details['beta_score']:.1f}/3점)
- 판정: {details['beta_verdict']}

### 하방 리스크 ({details['downside_score']:.1f}/3점)
- 판정: {details['downside_verdict']}

---

## 📊 상대 강도 ({stock.relative_strength_score:.1f}/10점)

### 섹터 내 순위 ({details['sector_rank_score']:.1f}/5점)
- 판정: {details['sector_rank_verdict']}

### 시장 대비 알파 ({details['alpha_score']:.1f}/5점)
- 판정: {details['alpha_verdict']}

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
            # 수급 분석
            "foreign_score": 4.0, "foreign_verdict": "중립",
            "institution_score": 4.0, "institution_verdict": "중립",
            "trading_score": 2.0, "trading_verdict": "중립",
            # 펀더멘털 분석
            "per_score": 2.0, "per_verdict": "중립",
            "pbr_score": 2.0, "pbr_verdict": "중립",
            "roe_score": 2.0, "roe_verdict": "중립",
            "growth_score": 2.5, "growth_verdict": "중립",
            "debt_score": 1.5, "debt_verdict": "중립",
            # 시장 환경
            "news_score": 3.75, "news_verdict": "중립",
            "sector_momentum_score": 1.875, "sector_momentum_verdict": "중립",
            "analyst_score": 1.875, "analyst_verdict": "중립",
            # 리스크 평가
            "volatility_score": 2.0, "volatility_verdict": "중립",
            "beta_score": 1.5, "beta_verdict": "중립",
            "downside_score": 1.5, "downside_verdict": "중립",
            # 상대 강도
            "sector_rank_score": 2.5, "sector_rank_verdict": "중립",
            "alpha_score": 2.5, "alpha_verdict": "중립",
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

        # 수급 분석 세부
        if rubric.supply and rubric.supply.details:
            details = rubric.supply.details
            defaults["foreign_score"] = details.get("foreign", 4.0)
            defaults["foreign_verdict"] = self._score_to_verdict(details.get("foreign", 4.0), 8)
            defaults["institution_score"] = details.get("institution", 4.0)
            defaults["institution_verdict"] = self._score_to_verdict(details.get("institution", 4.0), 8)
            defaults["trading_score"] = details.get("trading_value", 2.0)
            defaults["trading_verdict"] = self._score_to_verdict(details.get("trading_value", 2.0), 4)

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
            defaults["downside_score"] = details.get("downside", 1.5)
            defaults["downside_verdict"] = self._score_to_verdict(details.get("downside", 1.5), 3)

        # 상대 강도 세부 (V2)
        if rubric.relative_strength and rubric.relative_strength.details:
            details = rubric.relative_strength.details
            defaults["sector_rank_score"] = details.get("sector_rank", 2.5)
            defaults["sector_rank_verdict"] = self._score_to_verdict(details.get("sector_rank", 2.5), 5)
            defaults["alpha_score"] = details.get("alpha", 2.5)
            defaults["alpha_verdict"] = self._score_to_verdict(details.get("alpha", 2.5), 5)

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
        """
        opinions = []

        # 종합 등급 기반
        if stock.total_score >= 80:
            opinions.append(f"{stock.name}은(는) 현재 매우 매력적인 투자 기회로 판단됩니다.")
        elif stock.total_score >= 60:
            opinions.append(f"{stock.name}은(는) 긍정적인 투자 전망을 보이고 있습니다.")
        elif stock.total_score >= 40:
            opinions.append(f"{stock.name}은(는) 현재 관망이 적절한 시점입니다.")
        else:
            opinions.append(f"{stock.name}은(는) 당분간 투자에 신중할 필요가 있습니다.")

        # 수급 분석 강점 (20점 만점 기준)
        if stock.supply_score >= 16:
            opinions.append("외국인/기관의 수급이 양호하여 단기 모멘텀이 기대됩니다.")
        elif stock.supply_score <= 8:
            opinions.append("최근 외국인/기관 수급이 부진하여 주의가 필요합니다.")

        # 펀더멘털 강점 (20점 만점 기준)
        if stock.fundamental_score >= 16:
            opinions.append("실적 성장세가 뚜렷하여 중장기 전망이 밝습니다.")
        elif stock.fundamental_score <= 8:
            opinions.append("펀더멘털 지표가 다소 부진한 상태입니다.")

        # 기술적 분석 강점 (25점 만점 기준)
        if stock.technical_score >= 20:
            opinions.append("기술적 지표가 상승 추세를 나타내고 있습니다.")
        elif stock.technical_score <= 10:
            opinions.append("기술적 지표가 약세를 나타내고 있어 추가 하락에 유의해야 합니다.")

        # 리스크 평가 (10점 만점 기준)
        if stock.risk_score >= 8:
            opinions.append("변동성이 낮고 안정적인 흐름을 보이고 있습니다.")
        elif stock.risk_score <= 4:
            opinions.append("다만, 변동성이 높아 리스크 관리에 유의해야 합니다.")

        return " ".join(opinions)
