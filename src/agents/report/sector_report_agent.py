"""
Sector Report Agent

섹터 분석 리포트를 마크다운으로 생성하는 에이전트.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.analysis.sector_analyzer import SectorAnalysisResult
from src.agents.analysis.stock_analyzer import StockAnalysisResult


# =============================================================================
# 상수 정의
# =============================================================================

# 리포트 출력 디렉토리
DEFAULT_OUTPUT_DIR = Path("output/reports/sectors")


# =============================================================================
# SectorReportAgent
# =============================================================================


@dataclass
class SectorReportAgent(BaseAgent):
    """
    섹터 리포트 생성 에이전트

    주요 기능:
    - SectorAnalysisResult를 마크다운 리포트로 변환
    - 상위 3개 섹터 리포트 생성
    - output/reports/sectors/ 디렉토리에 저장

    사용 예시:
        agent = SectorReportAgent()
        reports = await agent.generate_reports(sector_results)
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
        sectors: List[SectorAnalysisResult],
        date_str: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        섹터 리포트를 생성합니다.

        Args:
            sectors: 섹터 분석 결과 리스트
            date_str: 날짜 문자열 (기본값: 오늘)

        Returns:
            섹터명을 키로 하는 리포트 파일 경로 딕셔너리
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")

        self._log_info(f"Generating {len(sectors)} sector reports")

        # 병렬 생성
        tasks = [
            self._generate_single_report(sector, date_str)
            for sector in sectors
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 집계
        report_paths: Dict[str, str] = {}
        for sector, result in zip(sectors, results):
            if isinstance(result, Exception):
                self._log_error(f"Failed to generate report for {sector.sector_name}: {result}")
            else:
                report_paths[sector.sector_name] = result

        self._log_info(f"Generated {len(report_paths)}/{len(sectors)} sector reports")
        return report_paths

    async def _generate_single_report(
        self,
        sector: SectorAnalysisResult,
        date_str: str,
    ) -> str:
        """
        단일 섹터 리포트를 생성합니다.

        Args:
            sector: 섹터 분석 결과
            date_str: 날짜 문자열

        Returns:
            생성된 리포트 파일 경로
        """
        # 마크다운 생성
        content = self._render_markdown(sector)

        # 파일 저장
        filename = f"{sector.sector_name}_{date_str}.md"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def _render_markdown(self, sector: SectorAnalysisResult) -> str:
        """
        섹터 리포트 마크다운을 렌더링합니다.

        Args:
            sector: 섹터 분석 결과

        Returns:
            마크다운 문자열
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        market_cap_str = self._format_market_cap(sector.total_market_cap)

        # 상위 종목 테이블 생성
        top_stocks_table = self._render_top_stocks_table(sector.top_stocks)

        # 섹터 전망 생성
        outlook = self._generate_outlook(sector)

        md = f"""# {sector.sector_name} 섹터 분석 리포트

> 생성일시: {now}
> 섹터 순위: {sector.rank}위

---

## 📊 섹터 개요

| 항목 | 값 |
|------|-----|
| **섹터명** | {sector.sector_name} |
| **종목 수** | {sector.stock_count}개 |
| **총 시가총액** | {market_cap_str} |
| **섹터 순위** | {sector.rank}위 |

---

## 📈 섹터 점수

### 종합 점수

| 점수 유형 | 값 | 설명 |
|----------|-----|------|
| **시가총액 가중 평균** | {sector.weighted_score:.1f}/100점 | 대형주 영향 반영 |
| **단순 평균** | {sector.simple_score:.1f}/100점 | 전체 종목 평균 |

### 카테고리별 점수 (시가총액 가중)

| 카테고리 | 점수 | 만점 | 비율 |
|----------|------|------|------|
| 기술적 분석 | {sector.technical_score:.1f} | 25점 | {sector.technical_score/25*100:.0f}% |
| 수급 분석 | {sector.supply_score:.1f} | 20점 | {sector.supply_score/20*100:.0f}% |
| 펀더멘털 분석 | {sector.fundamental_score:.1f} | 20점 | {sector.fundamental_score/20*100:.0f}% |
| 시장 환경 | {sector.market_score:.1f} | 15점 | {sector.market_score/15*100:.0f}% |

---

## 🏆 상위 종목

{top_stocks_table}

---

## 📊 카테고리별 강/약점 분석

{self._analyze_category_strengths(sector)}

---

## 💡 섹터 전망

{outlook}

---

*이 리포트는 자동 생성되었으며, 투자 판단의 참고 자료로만 활용하시기 바랍니다.*
"""
        return md

    def _render_top_stocks_table(self, stocks: List[StockAnalysisResult]) -> str:
        """
        상위 종목 테이블을 렌더링합니다.
        """
        if not stocks:
            return "상위 종목 정보가 없습니다."

        lines = [
            "| 순위 | 종목명 | 종목코드 | 총점 | 등급 | 시가총액 |",
            "|------|--------|----------|------|------|----------|",
        ]

        for i, stock in enumerate(stocks, 1):
            market_cap_str = self._format_market_cap(stock.market_cap)
            lines.append(
                f"| {i} | {stock.name} | {stock.symbol} | {stock.total_score:.1f} | {stock.investment_grade} | {market_cap_str} |"
            )

        return "\n".join(lines)

    def _analyze_category_strengths(self, sector: SectorAnalysisResult) -> str:
        """
        카테고리별 강/약점을 분석합니다.
        """
        analysis = []

        # 기술적 분석 (25점 만점)
        tech_pct = sector.technical_score / 25 * 100
        if tech_pct >= 70:
            analysis.append(f"- **기술적 분석 (강점)**: {tech_pct:.0f}% - 섹터 전반적으로 상승 추세를 보이고 있습니다.")
        elif tech_pct <= 40:
            analysis.append(f"- **기술적 분석 (약점)**: {tech_pct:.0f}% - 섹터 전반적으로 약세 흐름입니다.")
        else:
            analysis.append(f"- **기술적 분석 (중립)**: {tech_pct:.0f}% - 섹터가 횡보 또는 방향성 탐색 중입니다.")

        # 수급 분석 (20점 만점)
        supply_pct = sector.supply_score / 20 * 100
        if supply_pct >= 70:
            analysis.append(f"- **수급 분석 (강점)**: {supply_pct:.0f}% - 외국인/기관 매수세가 강합니다.")
        elif supply_pct <= 40:
            analysis.append(f"- **수급 분석 (약점)**: {supply_pct:.0f}% - 외국인/기관 매도세가 우세합니다.")
        else:
            analysis.append(f"- **수급 분석 (중립)**: {supply_pct:.0f}% - 수급이 균형 상태입니다.")

        # 펀더멘털 분석 (20점 만점)
        fund_pct = sector.fundamental_score / 20 * 100
        if fund_pct >= 70:
            analysis.append(f"- **펀더멘털 (강점)**: {fund_pct:.0f}% - 섹터 내 기업들의 실적이 양호합니다.")
        elif fund_pct <= 40:
            analysis.append(f"- **펀더멘털 (약점)**: {fund_pct:.0f}% - 섹터 내 기업들의 실적이 부진합니다.")
        else:
            analysis.append(f"- **펀더멘털 (중립)**: {fund_pct:.0f}% - 섹터 내 실적이 혼조세입니다.")

        # 시장 환경 (15점 만점)
        market_pct = sector.market_score / 15 * 100
        if market_pct >= 70:
            analysis.append(f"- **시장 환경 (강점)**: {market_pct:.0f}% - 뉴스/센티먼트가 긍정적입니다.")
        elif market_pct <= 40:
            analysis.append(f"- **시장 환경 (약점)**: {market_pct:.0f}% - 뉴스/센티먼트가 부정적입니다.")
        else:
            analysis.append(f"- **시장 환경 (중립)**: {market_pct:.0f}% - 시장 환경이 중립적입니다.")

        return "\n".join(analysis)

    def _generate_outlook(self, sector: SectorAnalysisResult) -> str:
        """
        섹터 전망을 자동 생성합니다.
        """
        outlooks = []

        # 종합 점수 기반
        score = sector.weighted_score
        if score >= 70:
            outlooks.append(f"{sector.sector_name} 섹터는 현재 매우 긍정적인 투자 환경을 보이고 있습니다.")
            outlooks.append("주요 종목들의 기술적/펀더멘털 지표가 우수하여 중장기 상승 여력이 기대됩니다.")
        elif score >= 55:
            outlooks.append(f"{sector.sector_name} 섹터는 양호한 투자 전망을 보이고 있습니다.")
            outlooks.append("일부 종목에서 모멘텀이 형성되고 있어 선별적 접근이 유효합니다.")
        elif score >= 40:
            outlooks.append(f"{sector.sector_name} 섹터는 현재 중립적인 상황입니다.")
            outlooks.append("뚜렷한 방향성이 부재하여 시장 상황을 주시할 필요가 있습니다.")
        else:
            outlooks.append(f"{sector.sector_name} 섹터는 현재 부정적인 투자 환경입니다.")
            outlooks.append("전반적인 약세 흐름으로 인해 보수적 접근이 필요합니다.")

        # 강점/약점 기반 추가 코멘트
        tech_pct = sector.technical_score / 25 * 100
        supply_pct = sector.supply_score / 20 * 100

        if supply_pct >= 70:
            outlooks.append("특히 외국인/기관 수급이 양호하여 단기 모멘텀이 기대됩니다.")
        elif supply_pct <= 30:
            outlooks.append("다만, 외국인/기관 수급 약화에 유의할 필요가 있습니다.")

        if tech_pct >= 70:
            outlooks.append("기술적 지표상 상승 추세가 유지되고 있습니다.")
        elif tech_pct <= 30:
            outlooks.append("기술적 지표상 하락 압력이 존재하므로 추가 조정 가능성을 고려해야 합니다.")

        return " ".join(outlooks)

    def _format_market_cap(self, market_cap: float) -> str:
        """
        시가총액을 포맷팅합니다. (억원 단위)
        """
        if market_cap >= 10000:
            return f"{market_cap / 10000:.1f}조원"
        else:
            return f"{market_cap:,.0f}억원"
