"""
Summary Agent

종합 리포트를 생성하고 JSON 데이터를 저장하는 에이전트.
최종 18개 종목, Top 3, 섹터 요약을 포함합니다.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.analysis.ranking_agent import RankingResult
from src.agents.analysis.stock_analyzer import StockAnalysisResult
from src.agents.analysis.sector_analyzer import SectorAnalysisResult


# =============================================================================
# 상수 정의
# =============================================================================

# 리포트 출력 디렉토리
DEFAULT_SUMMARY_DIR = Path("output/reports/summary")
DEFAULT_DATA_DIR = Path("output/data")

# 투자 등급별 별점
GRADE_STARS = {
    "Strong Buy": "⭐⭐⭐⭐⭐",
    "Buy": "⭐⭐⭐⭐",
    "Hold": "⭐⭐⭐",
    "Sell": "⭐⭐",
    "Strong Sell": "⭐",
}


# =============================================================================
# SummaryAgent
# =============================================================================


@dataclass
class SummaryAgent(BaseAgent):
    """
    종합 리포트 생성 에이전트

    주요 기능:
    - RankingResult를 기반으로 종합 리포트 생성
    - JSON 데이터 저장
    - 마크다운 종합 리포트 생성
    - Top 3 및 선정 이유 포함

    사용 예시:
        agent = SummaryAgent()
        result = await agent.generate_summary(ranking_result)
    """

    summary_dir: Path = field(default_factory=lambda: DEFAULT_SUMMARY_DIR)
    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)

    def __post_init__(self):
        """출력 디렉토리 생성 및 로거 초기화"""
        super().__post_init__()
        self.summary_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def collect(self, symbols: List[str]) -> Dict[str, Any]:
        """
        BaseAgent 인터페이스 구현.
        """
        return {}

    async def generate_summary(
        self,
        ranking_result: RankingResult,
        date_str: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        종합 리포트를 생성합니다.

        Args:
            ranking_result: RankingAgent의 결과
            date_str: 날짜 문자열 (기본값: 오늘)

        Returns:
            생성된 파일 경로들 (markdown, json)
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")

        self._log_info("Generating summary report")

        result_paths = {}

        # 1. JSON 데이터 저장
        json_path = await self._save_json_data(ranking_result, date_str)
        result_paths["json"] = json_path

        # 2. 마크다운 종합 리포트 생성
        md_path = await self._save_markdown_report(ranking_result, date_str)
        result_paths["markdown"] = md_path

        self._log_info(f"Summary report generated: {result_paths}")
        return result_paths

    async def _save_json_data(
        self,
        ranking_result: RankingResult,
        date_str: str,
    ) -> str:
        """
        JSON 데이터를 저장합니다.
        """
        data = self._build_json_data(ranking_result)

        filepath = self.data_dir / f"analysis_{date_str}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(filepath)

    def _build_json_data(self, ranking_result: RankingResult) -> Dict[str, Any]:
        """
        JSON 데이터 구조를 빌드합니다.
        """
        return {
            "generated_at": datetime.now().isoformat(),

            # 섹터 분석
            "sector_rankings": [s.to_dict() for s in ranking_result.top_sectors],
            "top_sectors": [s.sector_name for s in ranking_result.top_sectors],

            # 그룹별 종목
            "kospi_top10": [s.to_dict() for s in ranking_result.kospi_top10],
            "kospi_11_20": [s.to_dict() for s in ranking_result.kospi_11_20],
            "kosdaq_top10": [s.to_dict() for s in ranking_result.kosdaq_top10],
            "sector_stocks": self._group_by_sector(ranking_result.sector_top),

            # 최종 선정
            "final_top3": [
                self._build_stock_detail(s, i + 1)
                for i, s in enumerate(ranking_result.final_top3)
            ],

            # 전체 18개 요약
            "all_selected": [s.to_dict() for s in ranking_result.final_18],

            # 요약 통계
            "summary": ranking_result.get_summary(),
        }

    def _group_by_sector(
        self,
        stocks: List[StockAnalysisResult]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        종목들을 섹터별로 그룹화합니다.
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for stock in stocks:
            sector = stock.sector or "기타"
            if sector not in grouped:
                grouped[sector] = []
            grouped[sector].append(stock.to_dict())
        return grouped

    def _build_stock_detail(
        self,
        stock: StockAnalysisResult,
        rank: int,
    ) -> Dict[str, Any]:
        """
        Top 3 종목의 상세 정보를 빌드합니다.
        """
        # 선정 이유 생성
        selection_reason = self._generate_selection_reason(stock, rank)

        return {
            "rank": rank,
            "symbol": stock.symbol,
            "name": stock.name,
            "sector": stock.sector,
            "total_score": round(stock.total_score, 2),
            "investment_grade": stock.investment_grade,
            "market_cap": round(stock.market_cap, 2),

            # 카테고리별 점수
            "technical_score": round(stock.technical_score, 2),
            "supply_score": round(stock.supply_score, 2),
            "fundamental_score": round(stock.fundamental_score, 2),
            "market_score": round(stock.market_score, 2),
            "risk_score": round(stock.risk_score, 2),
            "relative_strength_score": round(stock.relative_strength_score, 2),

            # 그룹 정보
            "group": stock.group,
            "rank_in_group": stock.rank_in_group,

            # 선정 이유
            "selection_reason": selection_reason,
        }

    def _generate_selection_reason(
        self,
        stock: StockAnalysisResult,
        rank: int,
    ) -> str:
        """
        Top 3 선정 이유를 생성합니다.
        """
        reasons = []

        # 순위별 기본 멘트
        rank_prefix = {
            1: "최고 점수를 기록하며",
            2: "2위의 높은 점수로",
            3: "3위의 우수한 점수로",
        }
        reasons.append(rank_prefix.get(rank, f"{rank}위로") + f" 선정되었습니다.")

        # 강점 분석
        strengths = []

        # 수급 강점 (20점 만점)
        if stock.supply_score >= 16:
            strengths.append("외국인/기관 수급이 매우 양호")
        elif stock.supply_score >= 12:
            strengths.append("외국인/기관 수급이 양호")

        # 기술적 강점 (25점 만점)
        if stock.technical_score >= 20:
            strengths.append("기술적 지표가 강한 상승세")
        elif stock.technical_score >= 15:
            strengths.append("기술적 지표가 상승 추세")

        # 펀더멘털 강점 (20점 만점)
        if stock.fundamental_score >= 16:
            strengths.append("펀더멘털이 매우 우수")
        elif stock.fundamental_score >= 12:
            strengths.append("펀더멘털이 양호")

        # 시장 환경 강점 (15점 만점)
        if stock.market_score >= 12:
            strengths.append("시장 센티먼트가 긍정적")

        # 리스크 평가 (10점 만점)
        if stock.risk_score >= 8:
            strengths.append("변동성이 낮아 안정적")

        if strengths:
            reasons.append("주요 강점: " + ", ".join(strengths) + ".")

        return " ".join(reasons)

    async def _save_markdown_report(
        self,
        ranking_result: RankingResult,
        date_str: str,
    ) -> str:
        """
        마크다운 종합 리포트를 저장합니다.
        """
        content = self._render_markdown(ranking_result)

        filepath = self.summary_dir / f"종합리포트_{date_str}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def _render_markdown(self, ranking_result: RankingResult) -> str:
        """
        종합 리포트 마크다운을 렌더링합니다.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Top 3 테이블
        top3_table = self._render_top3_table(ranking_result.final_top3)

        # Top 3 상세 분석
        top3_details = self._render_top3_details(ranking_result.final_top3)

        # 상위 섹터 테이블
        top_sectors_table = self._render_sectors_table(ranking_result.top_sectors)

        # 그룹별 종목 테이블
        group_tables = self._render_group_tables(ranking_result)

        # 최종 18개 종목 테이블
        final_18_table = self._render_final_18_table(ranking_result.final_18)

        md = f"""# 투자 종합 분석 리포트

> 생성일시: {now}
> 분석 대상: KOSPI Top 20, KOSDAQ Top 10, 11개 섹터

---

## 🏆 Top 3 추천 종목

{top3_table}

---

## 📊 Top 3 상세 분석

{top3_details}

---

## 🌍 상위 섹터

{top_sectors_table}

---

## 📈 그룹별 선정 종목

{group_tables}

---

## 📋 최종 18개 선정 종목

{final_18_table}

---

## 📊 분석 요약

| 항목 | 값 |
|------|-----|
| 분석 종목 수 | {len(ranking_result.final_18)}개 |
| 상위 섹터 | {', '.join(s.sector_name for s in ranking_result.top_sectors)} |
| KOSPI 시총 상위 10 선정 | {len(ranking_result.kospi_top10)}개 |
| KOSPI 시총 11~20 선정 | {len(ranking_result.kospi_11_20)}개 |
| KOSDAQ 시총 상위 10 선정 | {len(ranking_result.kosdaq_top10)}개 |
| 섹터별 선정 | {len(ranking_result.sector_top)}개 |

---

## 💡 투자 안내

이 리포트는 루브릭 기반 정량 분석을 통해 자동 생성되었습니다.

**평가 기준 (100점 만점)**:
- 기술적 분석 (25점): 추세, RSI, 지지/저항, MACD, ADX
- 수급 분석 (20점): 외국인, 기관, 거래대금
- 펀더멘털 분석 (20점): PER, PBR, ROE, 성장률, 부채비율
- 시장 환경 (15점): 뉴스 센티먼트, 섹터 모멘텀, 애널리스트
- 리스크 평가 (10점): 변동성, 베타, 하방 리스크
- 상대 강도 (10점): 섹터 내 순위, 시장 대비 알파

**투자 등급**:
| 등급 | 점수 범위 | 의미 |
|------|----------|------|
| Strong Buy | 80~100점 | 적극 매수 추천 |
| Buy | 60~79점 | 매수 추천 |
| Hold | 40~59점 | 보유/관망 |
| Sell | 20~39점 | 매도 추천 |
| Strong Sell | 0~19점 | 적극 매도 추천 |

---

*이 리포트는 자동 생성되었으며, 투자 판단의 참고 자료로만 활용하시기 바랍니다.*
*실제 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.*
"""
        return md

    def _render_top3_table(self, stocks: List[StockAnalysisResult]) -> str:
        """
        Top 3 테이블을 렌더링합니다.
        """
        lines = [
            "| 순위 | 종목명 | 종목코드 | 섹터 | 총점 | 등급 |",
            "|------|--------|----------|------|------|------|",
        ]

        for i, stock in enumerate(stocks, 1):
            grade_stars = GRADE_STARS.get(stock.investment_grade, "⭐⭐⭐")
            lines.append(
                f"| {i} | **{stock.name}** | {stock.symbol} | {stock.sector or 'N/A'} | "
                f"**{stock.total_score:.1f}** | {grade_stars} {stock.investment_grade} |"
            )

        return "\n".join(lines)

    def _render_top3_details(self, stocks: List[StockAnalysisResult]) -> str:
        """
        Top 3 상세 분석을 렌더링합니다.
        """
        details = []

        for i, stock in enumerate(stocks, 1):
            market_cap_str = self._format_market_cap(stock.market_cap)
            selection_reason = self._generate_selection_reason(stock, i)

            detail = f"""### {i}위: {stock.name} ({stock.symbol})

| 항목 | 값 |
|------|-----|
| 섹터 | {stock.sector or 'N/A'} |
| 시가총액 | {market_cap_str} |
| 총점 | {stock.total_score:.1f}/100점 |
| 투자 등급 | {stock.investment_grade} |
| 분석 그룹 | {self._translate_group_name(stock.group)} |

**카테고리별 점수**:
- 기술적 분석: {stock.technical_score:.1f}/25점
- 수급 분석: {stock.supply_score:.1f}/20점
- 펀더멘털: {stock.fundamental_score:.1f}/20점
- 시장 환경: {stock.market_score:.1f}/15점
- 리스크: {stock.risk_score:.1f}/10점
- 상대 강도: {stock.relative_strength_score:.1f}/10점

**선정 이유**: {selection_reason}
"""
            details.append(detail)

        return "\n".join(details)

    def _render_sectors_table(self, sectors: List[SectorAnalysisResult]) -> str:
        """
        상위 섹터 테이블을 렌더링합니다.
        """
        lines = [
            "| 순위 | 섹터명 | 점수 | 종목 수 | 총 시가총액 |",
            "|------|--------|------|--------|------------|",
        ]

        for sector in sectors:
            market_cap_str = self._format_market_cap(sector.total_market_cap)
            lines.append(
                f"| {sector.rank} | **{sector.sector_name}** | {sector.weighted_score:.1f} | "
                f"{sector.stock_count}개 | {market_cap_str} |"
            )

        return "\n".join(lines)

    def _render_group_tables(self, ranking_result: RankingResult) -> str:
        """
        그룹별 종목 테이블을 렌더링합니다.
        """
        tables = []

        # KOSPI Top 10
        if ranking_result.kospi_top10:
            tables.append("### KOSPI 시총 상위 10")
            tables.append(self._render_stock_list(ranking_result.kospi_top10))

        # KOSPI 11~20
        if ranking_result.kospi_11_20:
            tables.append("### KOSPI 시총 11~20위")
            tables.append(self._render_stock_list(ranking_result.kospi_11_20))

        # KOSDAQ Top 10
        if ranking_result.kosdaq_top10:
            tables.append("### KOSDAQ 시총 상위 10")
            tables.append(self._render_stock_list(ranking_result.kosdaq_top10))

        # 섹터별
        if ranking_result.sector_top:
            tables.append("### 상위 섹터별 종목")
            tables.append(self._render_stock_list(ranking_result.sector_top))

        return "\n\n".join(tables)

    def _render_stock_list(self, stocks: List[StockAnalysisResult]) -> str:
        """
        종목 리스트 테이블을 렌더링합니다.
        """
        lines = [
            "| 종목명 | 종목코드 | 섹터 | 총점 | 등급 |",
            "|--------|----------|------|------|------|",
        ]

        for stock in stocks:
            lines.append(
                f"| {stock.name} | {stock.symbol} | {stock.sector or 'N/A'} | "
                f"{stock.total_score:.1f} | {stock.investment_grade} |"
            )

        return "\n".join(lines)

    def _render_final_18_table(self, stocks: List[StockAnalysisResult]) -> str:
        """
        최종 18개 종목 테이블을 렌더링합니다.
        """
        lines = [
            "| 순위 | 종목명 | 종목코드 | 섹터 | 총점 | 등급 | 그룹 |",
            "|------|--------|----------|------|------|------|------|",
        ]

        for stock in stocks:
            group_name = self._translate_group_name(stock.group)
            lines.append(
                f"| {stock.final_rank or '-'} | {stock.name} | {stock.symbol} | "
                f"{stock.sector or 'N/A'} | {stock.total_score:.1f} | {stock.investment_grade} | {group_name} |"
            )

        return "\n".join(lines)

    def _translate_group_name(self, group: str) -> str:
        """
        그룹명을 한글로 변환합니다.
        """
        translations = {
            "kospi_top10": "KOSPI Top10",
            "kospi_11_20": "KOSPI 11~20",
            "kosdaq_top10": "KOSDAQ Top10",
            "custom": "커스텀",
        }
        if group.startswith("sector_"):
            sector_name = group.replace("sector_", "")
            return f"섹터: {sector_name}"
        return translations.get(group, group)

    def _format_market_cap(self, market_cap: float) -> str:
        """
        시가총액을 포맷팅합니다. (억원 단위)
        """
        if market_cap >= 10000:
            return f"{market_cap / 10000:.1f}조원"
        else:
            return f"{market_cap:,.0f}억원"
