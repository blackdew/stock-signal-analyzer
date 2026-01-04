"""섹터 분석기

종목이 속한 섹터의 성과를 분석합니다.

분석 항목:
    - 섹터 1개월 수익률
    - 종목 vs 섹터 비교 (아웃퍼폼/언더퍼폼)
    - 섹터 전체 상승/하락 추세
"""

import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SectorAnalyzer:
    """섹터 분석기"""

    def __init__(self):
        self._sector_info: Optional[pd.DataFrame] = None
        self._sector_performance_cache: Dict[str, Dict[str, Any]] = {}

    def _load_sector_info(self) -> pd.DataFrame:
        """KRX 섹터 정보를 로드합니다."""
        if self._sector_info is not None:
            return self._sector_info

        try:
            logger.info("Loading sector information...")
            df = fdr.StockListing('KRX-DESC')

            if df is not None and not df.empty:
                # 컬럼명 정규화
                if '종목코드' in df.columns:
                    df = df.rename(columns={'종목코드': 'Code'})

                self._sector_info = df
                logger.info(f"Loaded sector info for {len(df)} stocks")

        except Exception as e:
            logger.error(f"Failed to load sector info: {e}")
            self._sector_info = pd.DataFrame()

        return self._sector_info

    def get_stock_sector(self, stock_code: str) -> Optional[Dict[str, str]]:
        """
        종목의 섹터 정보를 조회합니다.

        Args:
            stock_code: 종목코드

        Returns:
            {'sector': '반도체', 'industry': '전자부품'} 또는 None
        """
        sector_df = self._load_sector_info()

        if sector_df.empty:
            return None

        stock = sector_df[sector_df['Code'] == stock_code]

        if stock.empty:
            return None

        row = stock.iloc[0]

        return {
            'sector': row.get('Sector', row.get('업종', '')),
            'industry': row.get('Industry', row.get('산업', '')),
        }

    def get_sector_stocks(self, sector: str) -> List[str]:
        """
        섹터에 속한 종목 리스트를 조회합니다.

        Args:
            sector: 섹터명

        Returns:
            종목코드 리스트
        """
        sector_df = self._load_sector_info()

        if sector_df.empty:
            return []

        sector_col = 'Sector' if 'Sector' in sector_df.columns else '업종'

        if sector_col not in sector_df.columns:
            return []

        stocks = sector_df[sector_df[sector_col] == sector]['Code'].tolist()

        return stocks

    def calculate_sector_performance(
        self,
        sector: str,
        period_days: int = 20  # 약 1개월
    ) -> Optional[Dict[str, Any]]:
        """
        섹터의 성과를 계산합니다.

        Args:
            sector: 섹터명
            period_days: 분석 기간 (거래일 기준)

        Returns:
            섹터 성과 딕셔너리
        """
        # 캐시 확인
        cache_key = f"{sector}_{period_days}"
        if cache_key in self._sector_performance_cache:
            return self._sector_performance_cache[cache_key]

        stocks = self.get_sector_stocks(sector)

        if not stocks:
            return None

        # 샘플링 (종목이 너무 많으면 상위 종목만)
        if len(stocks) > 30:
            stocks = stocks[:30]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days + 20)  # 여유분 추가

        returns = []

        for code in stocks:
            try:
                df = fdr.DataReader(code, start_date, end_date)

                if df is None or len(df) < period_days:
                    continue

                # 수익률 계산
                start_price = df['Close'].iloc[-period_days]
                end_price = df['Close'].iloc[-1]

                if start_price > 0:
                    ret = (end_price - start_price) / start_price * 100
                    returns.append(ret)

            except Exception:
                continue

        if not returns:
            return None

        result = {
            'sector': sector,
            'period_days': period_days,
            'stock_count': len(returns),
            'avg_return': round(sum(returns) / len(returns), 2),
            'max_return': round(max(returns), 2),
            'min_return': round(min(returns), 2),
            'positive_count': sum(1 for r in returns if r > 0),
            'negative_count': sum(1 for r in returns if r <= 0),
            'trend': 'UP' if sum(returns) / len(returns) > 0 else 'DOWN',
        }

        # 캐시 저장
        self._sector_performance_cache[cache_key] = result

        return result

    def analyze_stock_vs_sector(
        self,
        stock_code: str,
        period_days: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        종목과 섹터의 성과를 비교합니다.

        Args:
            stock_code: 종목코드
            period_days: 분석 기간

        Returns:
            비교 분석 결과
        """
        # 종목 섹터 조회
        sector_info = self.get_stock_sector(stock_code)

        if not sector_info or not sector_info.get('sector'):
            return None

        sector = sector_info['sector']

        # 섹터 성과 조회
        sector_perf = self.calculate_sector_performance(sector, period_days)

        if not sector_perf:
            return None

        # 종목 수익률 계산
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days + 20)

            df = fdr.DataReader(stock_code, start_date, end_date)

            if df is None or len(df) < period_days:
                return None

            start_price = df['Close'].iloc[-period_days]
            end_price = df['Close'].iloc[-1]
            stock_return = (end_price - start_price) / start_price * 100 if start_price > 0 else 0

        except Exception as e:
            logger.debug(f"Error calculating stock return for {stock_code}: {e}")
            return None

        # 비교 분석
        sector_avg_return = sector_perf['avg_return']
        relative_performance = stock_return - sector_avg_return

        return {
            'stock_code': stock_code,
            'sector': sector,
            'industry': sector_info.get('industry', ''),
            'stock_return': round(stock_return, 2),
            'sector_avg_return': sector_avg_return,
            'relative_performance': round(relative_performance, 2),
            'outperform': relative_performance > 0,
            'sector_trend': sector_perf['trend'],
            'sector_positive_ratio': round(
                sector_perf['positive_count'] / sector_perf['stock_count'] * 100, 1
            ) if sector_perf['stock_count'] > 0 else 0,
        }

    def batch_analyze(
        self,
        stock_codes: List[str],
        period_days: int = 20
    ) -> pd.DataFrame:
        """
        여러 종목의 섹터 분석을 수행합니다.

        Args:
            stock_codes: 종목코드 리스트
            period_days: 분석 기간

        Returns:
            분석 결과 DataFrame
        """
        logger.info(f"Sector analysis for {len(stock_codes)} stocks...")

        results = []

        for i, code in enumerate(stock_codes):
            try:
                analysis = self.analyze_stock_vs_sector(code, period_days)
                if analysis:
                    results.append(analysis)

                if (i + 1) % 20 == 0:
                    logger.info(f"Sector analysis progress: {i + 1}/{len(stock_codes)}")

            except Exception as e:
                logger.debug(f"Error analyzing sector for {code}: {e}")

        logger.info(f"Sector analysis complete: {len(results)} stocks analyzed")

        return pd.DataFrame(results) if results else pd.DataFrame()

    def get_all_sectors(self) -> List[str]:
        """모든 섹터 목록을 반환합니다."""
        sector_df = self._load_sector_info()

        if sector_df.empty:
            return []

        sector_col = 'Sector' if 'Sector' in sector_df.columns else '업종'

        if sector_col not in sector_df.columns:
            return []

        return sector_df[sector_col].unique().tolist()

    def get_sector_summary(self) -> pd.DataFrame:
        """모든 섹터의 성과 요약을 반환합니다."""
        sectors = self.get_all_sectors()
        summaries = []

        for sector in sectors:
            try:
                perf = self.calculate_sector_performance(sector)
                if perf:
                    summaries.append(perf)
            except Exception:
                continue

        if not summaries:
            return pd.DataFrame()

        df = pd.DataFrame(summaries)
        df = df.sort_values('avg_return', ascending=False)

        return df
