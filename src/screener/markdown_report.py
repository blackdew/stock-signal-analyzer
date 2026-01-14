"""마크다운 리포트 생성기

스크리닝 결과를 마크다운 형식의 리포트로 생성합니다.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MarkdownReportGenerator:
    """마크다운 리포트 생성기"""

    def __init__(self, output_dir: str = "reports/screening"):
        """
        Args:
            output_dir: 리포트 저장 디렉토리 (기본: reports/screening)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_strategy_dir(self, strategy: str) -> Path:
        """전략별 디렉토리 경로를 반환하고 생성합니다."""
        strategy_dir = self.output_dir / strategy
        strategy_dir.mkdir(parents=True, exist_ok=True)
        return strategy_dir

    def _get_detailed_dir(self, strategy: str) -> Path:
        """전략별 개별 종목 리포트 디렉토리를 반환하고 생성합니다."""
        detailed_dir = self.output_dir / strategy / "detailed"
        detailed_dir.mkdir(parents=True, exist_ok=True)
        return detailed_dir

    def generate_report(
        self,
        stocks: List[Dict[str, Any]],
        screening_stats: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        strategy: str = "value",
        generate_individual: bool = True,
    ) -> str:
        """
        스크리닝 리포트를 생성합니다.

        Args:
            stocks: 선정된 종목 리스트
            screening_stats: 스크리닝 통계
            start_time: 분석 시작 시간
            end_time: 분석 종료 시간
            strategy: 전략 이름 (디렉토리 분류용)
            generate_individual: 개별 종목 리포트 생성 여부

        Returns:
            생성된 리포트 파일 경로
        """
        report_date = datetime.now().strftime("%Y-%m-%d")
        report_time = datetime.now().strftime("%H:%M:%S")
        elapsed = (end_time - start_time).total_seconds()

        # 리포트 내용 생성
        content = self._build_report_content(
            stocks=stocks,
            stats=screening_stats,
            report_date=report_date,
            report_time=report_time,
            elapsed_seconds=elapsed,
        )

        # 전략별 디렉토리에 저장
        strategy_dir = self._get_strategy_dir(strategy)
        filename = f"screen_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = strategy_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Report saved to: {filepath}")

        # 개별 종목 리포트 생성
        if generate_individual and stocks:
            individual_paths = self.generate_individual_reports(stocks, report_date, strategy)
            logger.info(f"Individual reports generated: {len(individual_paths)} files")

        return str(filepath)

    def generate_individual_reports(
        self,
        stocks: List[Dict[str, Any]],
        report_date: Optional[str] = None,
        strategy: str = "value"
    ) -> List[str]:
        """
        개별 종목 리포트를 생성합니다.
        재료 지속성이 '하'인 종목은 제외합니다.

        Args:
            stocks: 종목 리스트
            report_date: 리포트 날짜 (None이면 오늘)
            strategy: 전략 이름 (디렉토리 분류용)

        Returns:
            생성된 파일 경로 리스트
        """
        if report_date is None:
            report_date = datetime.now().strftime("%Y-%m-%d")

        date_str = report_date.replace("-", "")
        paths = []
        skipped = 0

        # 전략별 detailed 디렉토리
        detailed_dir = self._get_detailed_dir(strategy)

        for stock in stocks:
            code = stock.get('code') or stock.get('Code') or stock.get('종목코드', '')
            name = stock.get('name') or stock.get('Name') or stock.get('종목명', '')

            if not code or not name:
                continue

            # 재료 지속성이 '하'인 종목은 건너뛰기
            news_analysis = stock.get('news_analysis', {})
            durability = news_analysis.get('material_durability', '하')
            if durability == '하':
                skipped += 1
                continue

            # 파일명: 종목명_날짜.md (예: 삼성전자_20260105.md)
            safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
            filename = f"{safe_name}_{date_str}.md"
            filepath = detailed_dir / filename

            # 개별 리포트 내용 생성
            content = self._build_individual_report(stock, report_date)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            paths.append(str(filepath))

        if skipped > 0:
            logger.info(f"Skipped {skipped} stocks with low material durability")

        return paths

    def _build_individual_report(
        self,
        stock: Dict[str, Any],
        report_date: str
    ) -> str:
        """개별 종목 리포트 내용을 생성합니다."""
        lines = []

        code = stock.get('code') or stock.get('Code') or stock.get('종목코드', '')
        name = stock.get('name') or stock.get('Name') or stock.get('종목명', '')

        # 헤더
        lines.append(f"# {name} ({code}) 분석 리포트")
        lines.append("")
        lines.append(f"> 분석일: {report_date}")
        lines.append("")

        # 기본 정보 섹션
        lines.extend(self._build_stock_section(1, stock))

        # 면책 조항
        lines.append("---")
        lines.append("")
        lines.append("## 면책 조항")
        lines.append("")
        lines.append("본 리포트는 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다.")
        lines.append("과거 데이터 기반 분석이므로 미래 수익을 보장하지 않습니다.")
        lines.append("")

        return "\n".join(lines)

    def _build_report_content(
        self,
        stocks: List[Dict[str, Any]],
        stats: Dict[str, Any],
        report_date: str,
        report_time: str,
        elapsed_seconds: float,
    ) -> str:
        """리포트 내용을 구성합니다."""
        lines = []

        # 헤더
        lines.append(f"# 주식 스크리닝 리포트 - {report_date}")
        lines.append("")
        lines.append(f"> 생성 시간: {report_time}")
        lines.append(f"> 분석 소요 시간: {elapsed_seconds:.1f}초")
        lines.append("")

        # 요약
        lines.append("## 요약")
        lines.append("")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 분석 종목 수 | {stats.get('total_analyzed', 0):,}개 |")
        lines.append(f"| Step 1 통과 (펀더멘털) | {stats.get('after_fundamental', 0):,}개 |")
        lines.append(f"| Step 1 통과 (기술적) | {stats.get('after_technical', 0):,}개 |")
        lines.append(f"| Step 1.5 통과 (리스크) | {stats.get('after_risk', 0):,}개 |")
        lines.append(f"| Step 1.5 통과 (수급) | {stats.get('after_investor', 0):,}개 |")
        lines.append(f"| **최종 선정** | **{len(stocks)}개** |")
        lines.append("")

        if not stocks:
            lines.append("## 선정 종목 없음")
            lines.append("")
            lines.append("스크리닝 조건을 만족하는 종목이 없습니다.")
            return "\n".join(lines)

        # 선정 종목 리스트
        lines.append("## 선정 종목 리스트")
        lines.append("")

        for i, stock in enumerate(stocks, 1):
            lines.extend(self._build_stock_section(i, stock))
            lines.append("")
            lines.append("---")
            lines.append("")

        # 면책 조항
        lines.append("## 면책 조항")
        lines.append("")
        lines.append("본 리포트는 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다.")
        lines.append("과거 데이터 기반 분석이므로 미래 수익을 보장하지 않습니다.")
        lines.append("")

        return "\n".join(lines)

    def _build_stock_section(self, index: int, stock: Dict[str, Any]) -> List[str]:
        """개별 종목 섹션을 구성합니다."""
        lines = []

        code = stock.get('code') or stock.get('Code') or stock.get('종목코드', '')
        name = stock.get('name') or stock.get('Name') or stock.get('종목명', '')

        lines.append(f"### {index}. {name} ({code})")
        lines.append("")

        # 기본 정보
        lines.append("#### 기본 정보")
        lines.append("")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 현재가 | {self._format_number(stock.get('current_price', stock.get('현재가', 0)))}원 |")
        lines.append(f"| 시가총액 | {self._format_market_cap(stock.get('market_cap', stock.get('시가총액', 0)))} |")
        lines.append(f"| PER | {stock.get('PER', 0):.1f}배 |")
        lines.append(f"| PBR | {stock.get('PBR', 0):.2f}배 |")

        sector = stock.get('sector', stock.get('Sector', ''))
        if sector:
            lines.append(f"| 섹터 | {sector} |")

        lines.append("")

        # 선정 이유
        lines.append("#### 선정 이유")
        lines.append("")

        reasons = stock.get('selection_reasons', [])
        if reasons:
            for reason in reasons:
                lines.append(f"- {reason}")
        else:
            # 기본 이유 생성
            per = stock.get('PER', 0)
            pbr = stock.get('PBR', 0)
            if per > 0 and per < 15:
                lines.append(f"- 저평가: PER {per:.1f}배 (업종 평균 대비 낮음)")
            if pbr > 0 and pbr < 1.2:
                lines.append(f"- 저평가: PBR {pbr:.2f}배 (자산 대비 저평가)")

            price_vs_ma = stock.get('price_vs_ma20_pct', 0)
            if price_vs_ma > 0:
                lines.append(f"- 기술적: 20일 이동평균선 상회 (+{price_vs_ma:.1f}%)")

            volume_change = stock.get('volume_change_pct', 0)
            if volume_change > 20:
                lines.append(f"- 거래량: 전월 대비 {volume_change:.1f}% 증가")

        lines.append("")

        # 수급 현황
        investor = stock.get('investor_flow', {})
        if investor:
            lines.append("#### 수급 현황")
            lines.append("")
            foreign_days = investor.get('foreign_net_buy_days', 0)
            inst_days = investor.get('institution_net_buy_days', 0)
            lines.append(f"- 외국인: 최근 5일 중 **{foreign_days}일** 순매수")
            lines.append(f"- 기관: 최근 5일 중 **{inst_days}일** 순매수")

            total_foreign = investor.get('total_foreign_net', 0)
            total_inst = investor.get('total_institution_net', 0)
            if total_foreign != 0:
                lines.append(f"- 외국인 5일 누적: {self._format_number(total_foreign)}주")
            if total_inst != 0:
                lines.append(f"- 기관 5일 누적: {self._format_number(total_inst)}주")
            lines.append("")

        # 재무 건전성
        financials = stock.get('financials', {})
        if financials and financials.get('years'):
            lines.append("#### 재무 건전성 (OpenDART)")
            lines.append("")
            lines.append("| 연도 | 매출액 | 영업이익 | 부채비율 |")
            lines.append("|------|--------|---------|---------|")

            for year_data in financials['years']:
                year = year_data.get('year', '')
                revenue = self._format_billion(year_data.get('revenue'))
                op_income = self._format_billion(year_data.get('operating_income'))
                debt_ratio = year_data.get('debt_ratio')
                debt_str = f"{debt_ratio:.1f}%" if debt_ratio is not None else "-"

                lines.append(f"| {year} | {revenue} | {op_income} | {debt_str} |")

            lines.append("")

        # 섹터 분석
        sector_analysis = stock.get('sector_analysis', {})
        if sector_analysis:
            lines.append("#### 섹터 분석")
            lines.append("")
            stock_ret = sector_analysis.get('stock_return', 0)
            sector_ret = sector_analysis.get('sector_avg_return', 0)
            relative = sector_analysis.get('relative_performance', 0)

            lines.append(f"- 섹터 1개월 수익률: {sector_ret:+.1f}%")
            lines.append(f"- 종목 1개월 수익률: {stock_ret:+.1f}%")

            if relative > 0:
                lines.append(f"- 평가: **섹터 대비 아웃퍼폼** (+{relative:.1f}%p)")
            else:
                lines.append(f"- 평가: 섹터 대비 언더퍼폼 ({relative:.1f}%p)")
            lines.append("")

        # 핵심 재료
        news_analysis = stock.get('news_analysis', {})
        if news_analysis:
            lines.append("#### 핵심 재료")
            lines.append("")

            themes = news_analysis.get('key_themes', [])
            if themes:
                lines.append(f"- 장기 성장 동력: {', '.join(themes)}")

            durability = news_analysis.get('material_durability', '하')
            lines.append(f"- 재료 지속성: **{durability}**")

            material_score = news_analysis.get('material_score', 0)
            if material_score > 0:
                lines.append(f"- 재료 점수: +{material_score}점")
            elif material_score < 0:
                lines.append(f"- 재료 점수: {material_score}점")

            lines.append("")

        # 리스크 요인
        risks = stock.get('risks', [])
        overhang = stock.get('overhang_risks', news_analysis.get('overhang_risks', []))

        if risks or overhang:
            lines.append("#### 리스크 요인")
            lines.append("")

            if overhang:
                for risk in overhang[:3]:  # 최대 3개
                    keyword = risk.get('keyword', risk.get('type', ''))
                    title = risk.get('title', '')[:50]
                    lines.append(f"- :warning: **{keyword}**: {title}...")

            if risks:
                for risk in risks[:3]:
                    lines.append(f"- :warning: {risk}")

            if not overhang and not risks:
                lines.append("- 특이사항 없음")

            lines.append("")

        # 종합 의견
        lines.append("#### 종합 의견")
        lines.append("")

        opinion = stock.get('opinion', '')
        if opinion:
            lines.append(opinion)
        else:
            # 기본 의견 생성
            score = stock.get('total_score', 0)
            if score >= 80:
                lines.append("펀더멘털과 기술적 지표 모두 양호하며, 수급 측면에서도 긍정적입니다. ")
                lines.append("중장기 관점에서 분할 매수를 고려해볼 만합니다.")
            elif score >= 60:
                lines.append("저평가 매력이 있으나, 추가적인 모니터링이 필요합니다. ")
                lines.append("진입 시점과 물량 조절에 주의가 필요합니다.")
            else:
                lines.append("스크리닝 기준은 통과했으나, 리스크 요인을 면밀히 검토해야 합니다.")

        lines.append("")

        return lines

    def _format_number(self, num: Any) -> str:
        """숫자를 천 단위 구분 형식으로 변환합니다."""
        try:
            return f"{int(num):,}"
        except (ValueError, TypeError):
            return str(num)

    def _format_market_cap(self, cap: Any) -> str:
        """시가총액을 읽기 쉬운 형식으로 변환합니다."""
        try:
            cap = float(cap)
            if cap >= 1e12:  # 조 단위
                return f"{cap/1e12:.1f}조원"
            elif cap >= 1e8:  # 억 단위
                return f"{cap/1e8:,.0f}억원"
            else:
                return f"{cap:,.0f}원"
        except (ValueError, TypeError):
            return str(cap)

    def _format_billion(self, num: Any) -> str:
        """숫자를 억 단위로 변환합니다."""
        try:
            if num is None:
                return "-"
            num = float(num)
            if abs(num) >= 1e8:
                return f"{num/1e8:,.0f}억"
            elif abs(num) >= 1e4:
                return f"{num/1e4:,.0f}만"
            else:
                return f"{num:,.0f}"
        except (ValueError, TypeError):
            return "-"

    # =====================================================
    # 전고점 돌파 전략 리포트
    # =====================================================

    def generate_breakout_report(
        self,
        stocks: List[Dict[str, Any]],
        screening_stats: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        strategy: str = "breakout",
    ) -> str:
        """
        전고점 돌파 전략 스크리닝 리포트를 생성합니다.

        Args:
            stocks: 선정된 종목 리스트
            screening_stats: 스크리닝 통계
            start_time: 분석 시작 시간
            end_time: 분석 종료 시간
            strategy: 전략 이름 (디렉토리 분류용, 기본: breakout)

        Returns:
            생성된 리포트 파일 경로
        """
        report_date = datetime.now().strftime("%Y-%m-%d")
        report_time = datetime.now().strftime("%H:%M:%S")
        elapsed = (end_time - start_time).total_seconds()

        # 리포트 내용 생성
        content = self._build_breakout_report_content(
            stocks=stocks,
            stats=screening_stats,
            report_date=report_date,
            report_time=report_time,
            elapsed_seconds=elapsed,
        )

        # 전략별 디렉토리에 저장
        strategy_dir = self._get_strategy_dir(strategy)
        filename = f"breakout_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = strategy_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Breakout report saved to: {filepath}")

        return str(filepath)

    def _build_breakout_report_content(
        self,
        stocks: List[Dict[str, Any]],
        stats: Dict[str, Any],
        report_date: str,
        report_time: str,
        elapsed_seconds: float,
    ) -> str:
        """전고점 돌파 리포트 내용을 구성합니다."""
        lines = []

        # 헤더
        lines.append(f"# 전고점 돌파 전략 스크리닝 리포트 - {report_date}")
        lines.append("")
        lines.append(f"> 생성 시간: {report_time}")
        lines.append(f"> 분석 소요 시간: {elapsed_seconds:.1f}초")
        lines.append("")

        # 요약
        lines.append("## 요약")
        lines.append("")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 전체 종목 수 | {stats.get('total_analyzed', 0):,}개 |")
        lines.append(f"| 시가총액 필터 통과 | {stats.get('after_market_cap', 0):,}개 |")
        lines.append(f"| 52주 신고가 근접 | {stats.get('after_breakout', 0):,}개 |")
        lines.append(f"| **최종 선정** | **{len(stocks)}개** |")
        lines.append("")

        if not stocks:
            lines.append("## 선정 종목 없음")
            lines.append("")
            lines.append("전고점 돌파 조건을 만족하는 종목이 없습니다.")
            return "\n".join(lines)

        # 선정 종목 리스트
        lines.append("## 선정 종목 리스트")
        lines.append("")

        for i, stock in enumerate(stocks, 1):
            lines.extend(self._build_breakout_stock_section(i, stock))
            lines.append("")
            lines.append("---")
            lines.append("")

        # 면책 조항
        lines.append("## 면책 조항")
        lines.append("")
        lines.append("본 리포트는 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다.")
        lines.append("과거 데이터 기반 분석이므로 미래 수익을 보장하지 않습니다.")
        lines.append("**전고점 돌파 실패 시 손절가(-5%)를 반드시 준수하세요.**")
        lines.append("")

        return "\n".join(lines)

    def _build_breakout_stock_section(self, index: int, stock: Dict[str, Any]) -> List[str]:
        """전고점 돌파 종목 섹션을 구성합니다."""
        lines = []

        code = stock.get('code', '')
        name = stock.get('name', code)

        lines.append(f"### {index}. {name} ({code})")
        lines.append("")

        # 기본 정보
        lines.append("#### 기본 정보")
        lines.append("")
        lines.append("| 항목 | 값 |")
        lines.append("|------|-----|")
        lines.append(f"| 현재가 | {self._format_number(stock.get('current_price', 0))}원 |")
        lines.append(f"| 52주 최고가 | {self._format_number(stock.get('high_52w', 0))}원 |")

        high_date = stock.get('high_52w_date')
        if high_date:
            if hasattr(high_date, 'strftime'):
                high_date_str = high_date.strftime('%Y-%m-%d')
            else:
                high_date_str = str(high_date)[:10]
            lines.append(f"| 최고가 기록일 | {high_date_str} |")

        pct_from_high = stock.get('pct_from_high', 0)
        lines.append(f"| 고점 대비 | {pct_from_high*100:.1f}% |")
        lines.append(f"| 돌파 확률 점수 | **{stock.get('breakout_score', 0)}점** |")
        lines.append("")

        # 돌파 분석
        lines.append("#### 전고점 돌파 분석")
        lines.append("")

        attempt_count = stock.get('attempt_count', 0)
        avg_trading_value = stock.get('avg_trading_value', 0)

        if stock.get('in_breakout_zone', False):
            lines.append(f"- :dart: **52주 신고가 근접 구간** (90~105%)")
        else:
            lines.append(f"- 고점 대비 {pct_from_high*100:.1f}% 위치")

        lines.append(f"- 최근 60일 돌파 시도: **{attempt_count}회**")
        if attempt_count >= 3:
            lines.append(f"  - :fire: 3회 이상 시도 → 돌파 확률 상승")

        lines.append(f"- 20일 평균 거래대금: **{avg_trading_value:.1f}억원**")
        lines.append("")

        # 매도/손절 전략
        sell_strategy = stock.get('sell_strategy', {})
        if sell_strategy:
            lines.append("#### 매도/손절 전략")
            lines.append("")

            stop_loss = sell_strategy.get('stop_loss_price', 0)
            stop_loss_pct = abs(sell_strategy.get('stop_loss_pct', 5))  # 절대값 사용
            lines.append(f"- :octagonal_sign: **절대 손절가**: {self._format_number(stop_loss)}원 (-{stop_loss_pct:.0f}%)")

            ma20 = stock.get('ma20', 0)
            if ma20 > 0:
                lines.append(f"- :chart_with_downwards_trend: **상대 손절**: MA20({self._format_number(ma20)}원) 이탈 시")

            lines.append("")

            targets = sell_strategy.get('sell_targets', [])
            if targets:
                lines.append("**분할 매도 목표:**")
                lines.append("")
                for target in targets:
                    target_price = target.get('price', 0)
                    ratio = target.get('ratio', 0)
                    reason = target.get('reason', '')
                    lines.append(f"- {reason}: {self._format_number(int(target_price))}원 ({ratio*100:.0f}%)")
                lines.append("")

        # 수급 현황
        investor = stock.get('investor_flow', {})
        if investor:
            lines.append("#### 수급 현황")
            lines.append("")
            foreign_days = investor.get('foreign_net_buy_days', 0)
            inst_days = investor.get('institution_net_buy_days', 0)
            lines.append(f"- 외국인: 최근 5일 중 **{foreign_days}일** 순매수")
            lines.append(f"- 기관: 최근 5일 중 **{inst_days}일** 순매수")
            lines.append("")

        # 뉴스/재료
        news_analysis = stock.get('news_analysis', {})
        if news_analysis:
            lines.append("#### 핵심 재료")
            lines.append("")

            themes = news_analysis.get('key_themes', [])
            if themes:
                lines.append(f"- 테마: {', '.join(themes)}")

            durability = news_analysis.get('material_durability', '하')
            lines.append(f"- 재료 지속성: **{durability}**")
            lines.append("")

        # 리스크
        overhang = stock.get('overhang_risks', [])
        if overhang:
            lines.append("#### 리스크 요인")
            lines.append("")
            for risk in overhang[:3]:
                keyword = risk.get('keyword', risk.get('type', ''))
                title = risk.get('title', '')[:50]
                lines.append(f"- :warning: **{keyword}**: {title}...")
            lines.append("")

        # 종합 의견
        lines.append("#### 종합 의견")
        lines.append("")

        score = stock.get('breakout_score', 0)
        if score >= 70:
            lines.append("돌파 확률이 높은 종목입니다. ")
            lines.append(f"현재가({self._format_number(stock.get('current_price', 0))}원)에서 분할 매수 후, ")
            lines.append(f"손절가({self._format_number(sell_strategy.get('stop_loss_price', 0))}원) 준수하여 리스크 관리하세요.")
        elif score >= 50:
            lines.append("돌파 가능성이 있으나, 추가 모니터링이 필요합니다. ")
            lines.append("거래량 급증과 함께 돌파 시 진입을 고려하세요.")
        else:
            lines.append("현재 돌파 확률이 낮습니다. ")
            lines.append("고점 근접 시 재검토하세요.")

        lines.append("")

        return lines
