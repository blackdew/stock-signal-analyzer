"""주식 스크리너 메인 실행 모듈

전체 스크리닝 파이프라인을 실행합니다.

실행 방법:
    uv run python -m src.screener.main
    uv run python -m src.screener.main --sector "반도체"
    uv run python -m src.screener.main --skip-news  # 뉴스 분석 건너뛰기
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

from src.utils.logger import setup_logger
from .fundamental_screener import FundamentalScreener
from .technical_screener import TechnicalScreener
from .risk_filter import RiskFilter
from .investor_flow import InvestorFlowAnalyzer
from .sector_analyzer import SectorAnalyzer
from .news_analyzer import NewsAnalyzer
from .opendart_client import get_opendart_client
from .markdown_report import MarkdownReportGenerator

logger = setup_logger(__name__)


class StockScreener:
    """주식 스크리너 메인 클래스"""

    def __init__(
        self,
        per_max: float = 15.0,
        pbr_max: float = 1.2,
        min_market_cap: float = 500.0,
        max_debt_ratio: float = 200.0,
        volume_increase_threshold: float = 0.20,
        min_net_buy_days: int = 3,
    ):
        """
        Args:
            per_max: PER 상한
            pbr_max: PBR 상한
            min_market_cap: 최소 시가총액 (억원)
            max_debt_ratio: 최대 부채비율 (%)
            volume_increase_threshold: 거래량 증가 임계값
            min_net_buy_days: 최소 순매수 일수
        """
        self.fundamental_screener = FundamentalScreener(
            per_max=per_max,
            pbr_max=pbr_max,
        )
        self.technical_screener = TechnicalScreener(
            volume_increase_threshold=volume_increase_threshold,
        )
        self.risk_filter = RiskFilter(
            min_market_cap=min_market_cap,
            max_debt_ratio=max_debt_ratio,
        )
        self.investor_flow = InvestorFlowAnalyzer(
            min_net_buy_days=min_net_buy_days,
        )
        self.sector_analyzer = SectorAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        self.report_generator = MarkdownReportGenerator()

        self.stats: Dict[str, Any] = {}

    def run(
        self,
        sector_filter: Optional[str] = None,
        skip_news: bool = False,
        skip_financial_check: bool = False,
        max_stocks: Optional[int] = None,
    ) -> str:
        """
        전체 스크리닝 파이프라인을 실행합니다.

        Args:
            sector_filter: 특정 섹터만 분석 (None이면 전체)
            skip_news: 뉴스 분석 건너뛰기
            skip_financial_check: 재무 체크 건너뛰기 (테스트용)
            max_stocks: 최대 분석 종목 수 (테스트용)

        Returns:
            생성된 리포트 파일 경로
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("주식 스크리닝 시작")
        logger.info("=" * 60)

        # Step 1: 펀더멘털 스크리닝
        logger.info("\n[Step 1] 펀더멘털 스크리닝 (PER/PBR)")
        market_data = self.fundamental_screener.load_market_data('KRX')
        self.stats['total_analyzed'] = len(market_data) if market_data is not None else 0
        fundamental_df = self.fundamental_screener.screen(market_data)
        self.stats['after_fundamental'] = len(fundamental_df)

        if fundamental_df.empty:
            logger.warning("펀더멘털 조건을 만족하는 종목이 없습니다.")
            return self._generate_empty_report(start_time)

        logger.info(f"펀더멘털 통과: {len(fundamental_df)}개 종목")

        # Step 1: 기술적 스크리닝
        logger.info("\n[Step 1] 기술적 스크리닝 (MA20, 거래량)")

        # 종목코드 추출
        code_col = 'Code' if 'Code' in fundamental_df.columns else '종목코드'
        stock_codes = fundamental_df[code_col].tolist()

        if max_stocks:
            stock_codes = stock_codes[:max_stocks]

        technical_passed, technical_failed = self.technical_screener.batch_analyze(
            fundamental_df, code_column=code_col
        )
        self.stats['after_technical'] = len(technical_passed)

        if technical_passed.empty:
            logger.warning("기술적 조건을 만족하는 종목이 없습니다.")
            return self._generate_empty_report(start_time)

        logger.info(f"기술적 통과: {len(technical_passed)}개 종목")

        # Step 1.5: 리스크 필터링
        logger.info("\n[Step 1.5] 리스크 필터링 (밸류트랩 제외)")
        risk_passed, risk_stats = self.risk_filter.apply_all_filters(
            technical_passed,
            code_column=code_col,
            skip_financial_check=skip_financial_check,
        )
        self.stats['after_risk'] = len(risk_passed)
        self.stats['risk_excluded'] = risk_stats.get('excluded_reasons', {})

        if risk_passed.empty:
            logger.warning("리스크 필터를 통과한 종목이 없습니다.")
            return self._generate_empty_report(start_time)

        logger.info(f"리스크 필터 통과: {len(risk_passed)}개 종목")

        # Step 1.5: 수급 검증
        logger.info("\n[Step 1.5] 수급 검증 (외국인/기관)")
        codes_for_investor = risk_passed[code_col].tolist()
        investor_passed, investor_all = self.investor_flow.screen(codes_for_investor)
        self.stats['after_investor'] = len(investor_passed)

        # 수급 정보를 DataFrame에 병합
        if not investor_passed.empty:
            risk_passed = risk_passed.merge(
                investor_all[['stock_code', 'foreign_net_buy_days', 'institution_net_buy_days',
                             'total_foreign_net', 'total_institution_net', 'has_smart_money_flow']],
                left_on=code_col,
                right_on='stock_code',
                how='left'
            )

        logger.info(f"수급 검증 통과: {len(investor_passed)}개 종목")

        # 수급 조건을 만족하는 종목만 선택 (옵션)
        final_df = risk_passed[risk_passed.get('has_smart_money_flow', True) == True] if 'has_smart_money_flow' in risk_passed.columns else risk_passed

        if final_df.empty:
            final_df = risk_passed  # 수급 조건 실패해도 진행

        # Step 2: 섹터 분석
        logger.info("\n[Step 2] 섹터 분석")
        final_codes = final_df[code_col].tolist()
        sector_results = self.sector_analyzer.batch_analyze(final_codes)

        # Step 2: 뉴스 분석
        news_results = []
        if not skip_news:
            logger.info("\n[Step 2] 뉴스/재료 분석")
            name_col = 'Name' if 'Name' in final_df.columns else '종목명'
            stocks_for_news = [
                {'code': row[code_col], 'name': row.get(name_col, row[code_col])}
                for _, row in final_df.iterrows()
            ]
            news_results = self.news_analyzer.batch_analyze(stocks_for_news)

        # Step 3: 최종 결과 조합
        logger.info("\n[Step 3] 리포트 생성")
        final_stocks = self._combine_results(
            final_df, sector_results, news_results, code_col
        )

        # 리포트 생성
        end_time = datetime.now()
        report_path = self.report_generator.generate_report(
            stocks=final_stocks,
            screening_stats=self.stats,
            start_time=start_time,
            end_time=end_time,
        )

        logger.info("\n" + "=" * 60)
        logger.info(f"스크리닝 완료!")
        logger.info(f"최종 선정: {len(final_stocks)}개 종목")
        logger.info(f"리포트: {report_path}")
        logger.info(f"소요 시간: {(end_time - start_time).total_seconds():.1f}초")
        logger.info("=" * 60)

        return report_path

    def _combine_results(
        self,
        df: pd.DataFrame,
        sector_results: pd.DataFrame,
        news_results: List[Dict],
        code_col: str,
    ) -> List[Dict[str, Any]]:
        """분석 결과를 조합합니다."""
        stocks = []

        # 섹터 결과를 딕셔너리로 변환
        sector_dict = {}
        if not sector_results.empty:
            sector_dict = sector_results.set_index('stock_code').to_dict('index')

        # 뉴스 결과를 딕셔너리로 변환
        news_dict = {n['stock_code']: n for n in news_results}

        name_col = 'Name' if 'Name' in df.columns else '종목명'

        for _, row in df.iterrows():
            code = row[code_col]
            name = row.get(name_col, code)

            stock = {
                'code': code,
                'name': name,
                'current_price': row.get('current_price', row.get('현재가', 0)),
                'market_cap': row.get('시가총액', row.get('MarketCap', 0)),
                'PER': row.get('PER', 0),
                'PBR': row.get('PBR', 0),
                'ROE': row.get('ROE', 0),
                'price_vs_ma20_pct': row.get('price_vs_ma20_pct', 0),
                'volume_change_pct': row.get('volume_change_pct', 0),
            }

            # 수급 정보
            if 'foreign_net_buy_days' in row:
                stock['investor_flow'] = {
                    'foreign_net_buy_days': row.get('foreign_net_buy_days', 0),
                    'institution_net_buy_days': row.get('institution_net_buy_days', 0),
                    'total_foreign_net': row.get('total_foreign_net', 0),
                    'total_institution_net': row.get('total_institution_net', 0),
                }

            # 섹터 분석
            if code in sector_dict:
                stock['sector_analysis'] = sector_dict[code]
                stock['sector'] = sector_dict[code].get('sector', '')

            # 뉴스 분석
            if code in news_dict:
                stock['news_analysis'] = news_dict[code]
                stock['overhang_risks'] = news_dict[code].get('overhang_risks', [])

            # 종합 점수 계산
            stock['total_score'] = self._calculate_total_score(stock)

            stocks.append(stock)

        # 점수순 정렬
        stocks.sort(key=lambda x: x['total_score'], reverse=True)

        return stocks

    def _calculate_total_score(self, stock: Dict[str, Any]) -> int:
        """종합 점수를 계산합니다."""
        score = 50  # 기본 점수

        # PER 점수 (낮을수록 좋음)
        per = stock.get('PER', 15)
        if per > 0:
            score += max(0, (15 - per) * 2)

        # PBR 점수 (낮을수록 좋음)
        pbr = stock.get('PBR', 1.2)
        if pbr > 0:
            score += max(0, (1.2 - pbr) * 20)

        # 기술적 점수
        price_vs_ma = stock.get('price_vs_ma20_pct', 0)
        if price_vs_ma > 0:
            score += min(10, price_vs_ma)

        # 거래량 점수
        volume_change = stock.get('volume_change_pct', 0)
        if volume_change > 20:
            score += min(10, (volume_change - 20) / 2)

        # 수급 점수
        investor = stock.get('investor_flow', {})
        foreign_days = investor.get('foreign_net_buy_days', 0)
        inst_days = investor.get('institution_net_buy_days', 0)
        score += min(20, (foreign_days + inst_days) * 3)

        # 섹터 점수
        sector_analysis = stock.get('sector_analysis', {})
        if sector_analysis.get('outperform'):
            score += 10

        # 뉴스 점수
        news = stock.get('news_analysis', {})
        material_score = news.get('material_score', 0)
        score += material_score * 0.2

        # 리스크 감점
        if stock.get('overhang_risks'):
            score -= len(stock['overhang_risks']) * 5

        return max(0, min(100, int(score)))

    def _generate_empty_report(self, start_time: datetime) -> str:
        """빈 리포트를 생성합니다."""
        end_time = datetime.now()
        return self.report_generator.generate_report(
            stocks=[],
            screening_stats=self.stats,
            start_time=start_time,
            end_time=end_time,
        )


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='주식 스크리너')
    parser.add_argument('--sector', type=str, help='특정 섹터만 분석')
    parser.add_argument('--skip-news', action='store_true', help='뉴스 분석 건너뛰기')
    parser.add_argument('--skip-financial', action='store_true', help='재무 체크 건너뛰기 (테스트용)')
    parser.add_argument('--max-stocks', type=int, help='최대 분석 종목 수 (테스트용)')
    parser.add_argument('--per-max', type=float, default=15.0, help='PER 상한')
    parser.add_argument('--pbr-max', type=float, default=1.2, help='PBR 상한')
    parser.add_argument('--min-market-cap', type=float, default=500.0, help='최소 시가총액 (억원)')

    args = parser.parse_args()

    screener = StockScreener(
        per_max=args.per_max,
        pbr_max=args.pbr_max,
        min_market_cap=args.min_market_cap,
    )

    try:
        report_path = screener.run(
            sector_filter=args.sector,
            skip_news=args.skip_news,
            skip_financial_check=args.skip_financial,
            max_stocks=args.max_stocks,
        )
        print(f"\n리포트가 생성되었습니다: {report_path}")

    except KeyboardInterrupt:
        print("\n스크리닝이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"스크리닝 오류: {e}")
        raise


if __name__ == '__main__':
    main()
