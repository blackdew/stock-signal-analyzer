"""
Weekly Sector Report Agent

주간 섹터 분석 리포트를 마크다운으로 생성하는 에이전트.
13개 섹터 분석, 섹터별 이슈/동향, 다음 주 시황 전망, 투자 전략을 포함합니다.
"""

import asyncio
import logging
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
DEFAULT_OUTPUT_DIR = Path("output/reports/weekly")


# =============================================================================
# WeeklySectorReportAgent
# =============================================================================


@dataclass
class WeeklySectorReportAgent(BaseAgent):
    """
    주간 섹터 리포트 생성 에이전트

    주요 기능:
    - 13개 섹터 분석 리포트 생성
    - 섹터별 주요 이슈/동향 섹션
    - 다음 주 시황 전망 템플릿
    - 주간 투자 전략 제안 섹션
    - output/reports/weekly/YYYY-WXX_sector_report.md 저장

    사용 예시:
        agent = WeeklySectorReportAgent()
        report_path = await agent.generate_weekly_report(sector_results)
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

    async def generate_weekly_report(
        self,
        sectors: List[SectorAnalysisResult],
        week_str: Optional[str] = None,
    ) -> str:
        """
        주간 섹터 리포트를 생성합니다.

        Args:
            sectors: 섹터 분석 결과 리스트
            week_str: 주차 문자열 (기본값: 현재 ISO 주차, 예: 2026-W03)

        Returns:
            생성된 리포트 파일 경로
        """
        if week_str is None:
            now = datetime.now()
            week_str = now.strftime("%G-W%V")

        self._log_info(f"Generating weekly sector report for {week_str} with {len(sectors)} sectors")

        # 마크다운 생성
        content = self._render_weekly_markdown(sectors, week_str)

        # 파일 저장 (YYYY-WXX_sector_report.md)
        filename = f"{week_str}_sector_report.md"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self._log_info(f"Generated weekly sector report: {filepath}")
        return str(filepath)

    def _render_weekly_markdown(
        self,
        sectors: List[SectorAnalysisResult],
        week_str: str,
    ) -> str:
        """
        주간 섹터 리포트 마크다운을 렌더링합니다.

        Args:
            sectors: 섹터 분석 결과 리스트
            week_str: 주차 문자열

        Returns:
            마크다운 문자열
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 상위 섹터 하이라이트
        top3_highlight = self._render_top_sectors_highlight(sectors[:3] if len(sectors) >= 3 else sectors)

        # 전체 섹터 순위 테이블
        all_sectors_table = self._render_all_sectors_table(sectors)

        # 섹터별 주요 이슈/동향
        sector_issues = self._render_sector_issues(sectors)

        # 다음 주 시황 전망
        weekly_outlook = self._render_weekly_outlook(sectors)

        # 주간 투자 전략 제안
        investment_strategy = self._render_investment_strategy(sectors)

        md = f"""# 주간 섹터 분석 리포트

> 주차: {week_str}
> 생성일시: {now}
> 분석 대상: {len(sectors)}개 섹터

---

## 🏆 상위 섹터 하이라이트

{top3_highlight}

---

## 📊 전체 섹터 순위

{all_sectors_table}

---

## 📰 섹터별 주요 이슈/동향

{sector_issues}

---

## 🔮 다음 주 시황 전망

{weekly_outlook}

---

## 💼 주간 투자 전략 제안

{investment_strategy}

---

## 📋 분석 요약

| 항목 | 내용 |
|------|------|
| 분석 주차 | {week_str} |
| 분석 섹터 수 | {len(sectors)}개 |
| 상위 3개 섹터 | {', '.join(s.sector_name for s in sectors[:3]) if len(sectors) >= 3 else ', '.join(s.sector_name for s in sectors)} |
| 평균 섹터 점수 | {sum(s.weighted_score for s in sectors) / len(sectors):.1f}점 |

---

*이 리포트는 자동 생성되었으며, 투자 판단의 참고 자료로만 활용하시기 바랍니다.*
*실제 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.*
"""
        return md

    def _render_top_sectors_highlight(self, sectors: List[SectorAnalysisResult]) -> str:
        """
        상위 섹터 하이라이트를 렌더링합니다.
        """
        highlights = []

        for i, sector in enumerate(sectors, 1):
            market_cap_str = self._format_market_cap(sector.total_market_cap)

            # 상위 종목 이름 추출
            top_stock_names = [s.name for s in sector.top_stocks[:3]]
            top_stocks_str = ", ".join(top_stock_names) if top_stock_names else "N/A"

            # 강점 분석
            strengths = self._analyze_sector_strengths(sector)

            highlight = f"""### {i}위: {sector.sector_name}

| 항목 | 값 |
|------|-----|
| 시가총액 가중 점수 | **{sector.weighted_score:.1f}점** |
| 단순 평균 점수 | {sector.simple_score:.1f}점 |
| 종목 수 | {sector.stock_count}개 |
| 총 시가총액 | {market_cap_str} |
| 대표 종목 | {top_stocks_str} |

**주요 강점**: {strengths}
"""
            highlights.append(highlight)

        return "\n".join(highlights)

    def _render_all_sectors_table(self, sectors: List[SectorAnalysisResult]) -> str:
        """
        전체 섹터 순위 테이블을 렌더링합니다.
        """
        lines = [
            "| 순위 | 섹터명 | 가중 점수 | 단순 점수 | 종목 수 | 시가총액 | 전망 |",
            "|------|--------|----------|----------|--------|----------|------|",
        ]

        for sector in sectors:
            market_cap_str = self._format_market_cap(sector.total_market_cap)
            outlook_emoji = self._get_outlook_emoji(sector.weighted_score)
            lines.append(
                f"| {sector.rank} | **{sector.sector_name}** | {sector.weighted_score:.1f} | "
                f"{sector.simple_score:.1f} | {sector.stock_count}개 | {market_cap_str} | {outlook_emoji} |"
            )

        return "\n".join(lines)

    def _render_sector_issues(self, sectors: List[SectorAnalysisResult]) -> str:
        """
        섹터별 주요 이슈/동향을 렌더링합니다.

        Note:
            현재 구현은 분석 데이터 기반 템플릿입니다.
            향후 뉴스 데이터 통합 시 실제 이슈 내용으로 대체 가능합니다.
        """
        issues = []

        for sector in sectors:
            # 카테고리별 점수 분석 기반 이슈 생성
            issue_points = self._generate_sector_issue_points(sector)

            issue = f"""### {sector.sector_name}

{issue_points}
"""
            issues.append(issue)

        return "\n".join(issues)

    def _generate_sector_issue_points(self, sector: SectorAnalysisResult) -> str:
        """
        섹터의 분석 데이터를 기반으로 이슈 포인트를 생성합니다.
        """
        points = []

        # 기술적 분석 관련 이슈
        tech_pct = sector.technical_score / 25 * 100
        if tech_pct >= 70:
            points.append(f"- 📈 **기술적 강세**: 섹터 전반 상승 추세 지속 (기술점수 {sector.technical_score:.1f}/25)")
        elif tech_pct <= 40:
            points.append(f"- 📉 **기술적 약세**: 하락 압력 존재 (기술점수 {sector.technical_score:.1f}/25)")
        else:
            points.append(f"- ➡️ **횡보 흐름**: 방향성 탐색 중 (기술점수 {sector.technical_score:.1f}/25)")

        # 수급 관련 이슈
        supply_pct = sector.supply_score / 20 * 100
        if supply_pct >= 70:
            points.append(f"- 🏦 **수급 우호적**: 외국인/기관 매수세 유입 (수급점수 {sector.supply_score:.1f}/20)")
        elif supply_pct <= 40:
            points.append(f"- 💸 **수급 약화**: 외국인/기관 매도세 (수급점수 {sector.supply_score:.1f}/20)")
        else:
            points.append(f"- ⚖️ **수급 균형**: 매수/매도 균형 상태 (수급점수 {sector.supply_score:.1f}/20)")

        # 펀더멘털 관련 이슈
        fund_pct = sector.fundamental_score / 20 * 100
        if fund_pct >= 70:
            points.append(f"- 💰 **실적 양호**: 섹터 내 기업 실적 개선 (펀더멘털 {sector.fundamental_score:.1f}/20)")
        elif fund_pct <= 40:
            points.append(f"- ⚠️ **실적 우려**: 펀더멘털 약화 신호 (펀더멘털 {sector.fundamental_score:.1f}/20)")

        # 상위 종목 정보
        if sector.top_stocks:
            top_names = ", ".join(s.name for s in sector.top_stocks[:3])
            points.append(f"- 🏆 **주목 종목**: {top_names}")

        return "\n".join(points) if points else "- 특이 사항 없음"

    def _render_weekly_outlook(self, sectors: List[SectorAnalysisResult]) -> str:
        """
        다음 주 시황 전망을 렌더링합니다.

        분석 데이터를 기반으로 시황 전망을 자동 생성합니다.
        """
        # 전체 섹터 평균 점수
        avg_score = sum(s.weighted_score for s in sectors) / len(sectors) if sectors else 0

        # 상위/하위 섹터 분석
        top_sectors = sectors[:3] if len(sectors) >= 3 else sectors
        bottom_sectors = sectors[-3:] if len(sectors) >= 3 else []

        # 시장 전반 전망
        if avg_score >= 65:
            market_outlook = "🟢 **긍정적 전망**: 시장 전반적으로 상승 모멘텀이 형성되어 있습니다."
            market_detail = "다수의 섹터에서 기술적/수급 지표가 양호하여 단기 상승 여력이 기대됩니다."
        elif avg_score >= 50:
            market_outlook = "🟡 **중립적 전망**: 시장이 방향성을 모색하고 있습니다."
            market_detail = "섹터별 차별화가 예상되며, 선별적 접근이 필요합니다."
        else:
            market_outlook = "🔴 **신중 필요**: 시장 전반적으로 약세 압력이 존재합니다."
            market_detail = "리스크 관리에 유의하며, 보수적 포지션 유지를 권장합니다."

        # 주목 섹터 전망
        top_sector_outlook = ""
        if top_sectors:
            top_names = ", ".join(s.sector_name for s in top_sectors)
            top_sector_outlook = f"""
### 주목 섹터

**상승 기대 섹터**: {top_names}

상위 섹터들은 기술적 지표와 수급 측면에서 우호적인 환경을 보이고 있습니다.
다음 주에도 상대적 강세가 예상됩니다.
"""

        # 주의 섹터 전망
        bottom_sector_outlook = ""
        if bottom_sectors:
            bottom_names = ", ".join(s.sector_name for s in bottom_sectors)
            bottom_sector_outlook = f"""
### 주의 섹터

**신중 접근 필요**: {bottom_names}

하위 섹터들은 약세 흐름이 지속되고 있어 신중한 접근이 필요합니다.
반등 신호 확인 후 진입을 권장합니다.
"""

        # 하위 섹터 평균 계산
        bottom_avg = (
            f"{sum(s.weighted_score for s in bottom_sectors) / len(bottom_sectors):.1f}점"
            if bottom_sectors else "N/A"
        )

        outlook = f"""{market_outlook}

{market_detail}

| 지표 | 수치 |
|------|------|
| 전체 섹터 평균 점수 | {avg_score:.1f}점 |
| 상위 3개 섹터 평균 | {sum(s.weighted_score for s in top_sectors) / len(top_sectors):.1f}점 |
| 하위 3개 섹터 평균 | {bottom_avg} |
{top_sector_outlook}
{bottom_sector_outlook}
"""
        return outlook

    def _render_investment_strategy(self, sectors: List[SectorAnalysisResult]) -> str:
        """
        주간 투자 전략 제안을 렌더링합니다.
        """
        avg_score = sum(s.weighted_score for s in sectors) / len(sectors) if sectors else 0
        top_sectors = sectors[:3] if len(sectors) >= 3 else sectors

        # 전략 타입 결정
        if avg_score >= 65:
            strategy_type = "공격적"
            strategy_icon = "⚔️"
            position_advice = "비중 확대를 고려할 수 있습니다."
        elif avg_score >= 50:
            strategy_type = "중립적"
            strategy_icon = "⚖️"
            position_advice = "현재 포지션 유지하며 선별적 매수를 권장합니다."
        else:
            strategy_type = "보수적"
            strategy_icon = "🛡️"
            position_advice = "현금 비중을 높이고 리스크 관리에 주력합니다."

        # 섹터별 전략
        sector_strategies = []
        for sector in top_sectors:
            if sector.weighted_score >= 70:
                action = "적극 매수 검토"
            elif sector.weighted_score >= 55:
                action = "선별 매수"
            else:
                action = "관망"

            sector_strategies.append(f"| {sector.sector_name} | {sector.weighted_score:.1f}점 | {action} |")

        sector_strategy_table = "\n".join([
            "| 섹터 | 점수 | 권장 전략 |",
            "|------|------|----------|",
        ] + sector_strategies)

        strategy = f"""### {strategy_icon} 이번 주 전략: {strategy_type} 접근

{position_advice}

### 섹터별 투자 전략

{sector_strategy_table}

### 핵심 포인트

1. **상위 섹터 집중**: {', '.join(s.sector_name for s in top_sectors[:2]) if len(top_sectors) >= 2 else top_sectors[0].sector_name if top_sectors else 'N/A'}에 관심
2. **리스크 관리**: 손절 라인 설정 및 포지션 사이즈 조절
3. **모니터링 포인트**: 외국인/기관 수급 변화, 업종별 실적 발표

### 주의 사항

- 단기 변동성에 대비한 분할 매수 권장
- 예상치 못한 대외 변수에 대한 대응 계획 수립
- 개별 종목 실적 및 뉴스 모니터링 필수
"""
        return strategy

    def _analyze_sector_strengths(self, sector: SectorAnalysisResult) -> str:
        """
        섹터의 강점을 분석합니다.
        """
        strengths = []

        # 카테고리별 강점 분석
        if sector.technical_score / 25 >= 0.7:
            strengths.append("기술적 강세")
        if sector.supply_score / 20 >= 0.7:
            strengths.append("수급 우호적")
        if sector.fundamental_score / 20 >= 0.7:
            strengths.append("실적 양호")
        if sector.market_score / 15 >= 0.7:
            strengths.append("시장 센티먼트 긍정적")

        if not strengths:
            # 상대적 강점 찾기
            scores = {
                "기술적": sector.technical_score / 25,
                "수급": sector.supply_score / 20,
                "펀더멘털": sector.fundamental_score / 20,
                "시장환경": sector.market_score / 15,
            }
            best_category = max(scores.items(), key=lambda x: x[1])
            strengths.append(f"{best_category[0]} 상대 우위")

        return ", ".join(strengths)

    def _get_outlook_emoji(self, score: float) -> str:
        """
        점수 기반 전망 이모지를 반환합니다.
        """
        if score >= 70:
            return "🟢"
        elif score >= 55:
            return "🟡"
        else:
            return "🔴"

    def _format_market_cap(self, market_cap: float) -> str:
        """
        시가총액을 포맷팅합니다. (억원 단위)
        """
        if market_cap >= 10000:
            return f"{market_cap / 10000:.1f}조원"
        else:
            return f"{market_cap:,.0f}억원"
