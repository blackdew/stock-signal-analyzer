"""펀더멘털 스크리너

코스피/코스닥 전 종목에서 저평가 종목을 필터링합니다.

필터링 조건:
    - PER < 15 AND PER > 0
    - PBR < 1.2
"""

import pandas as pd
from typing import Optional, Dict, List, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class FundamentalScreener:
    """펀더멘털 기반 종목 스크리너"""

    def __init__(
        self,
        per_max: float = 15.0,
        per_min: float = 0.0,
        pbr_max: float = 1.2,
    ):
        """
        Args:
            per_max: PER 상한 (기본 15)
            per_min: PER 하한 (기본 0, 적자기업 제외)
            pbr_max: PBR 상한 (기본 1.2)
        """
        self.per_max = per_max
        self.per_min = per_min
        self.pbr_max = pbr_max

    def load_market_data(self, market: str = 'KRX') -> Optional[pd.DataFrame]:
        """
        시장 전체 종목의 펀더멘털 데이터를 로드합니다.

        Args:
            market: 'KOSPI', 'KOSDAQ', 또는 'KRX' (전체)

        Returns:
            종목 데이터 DataFrame
        """
        try:
            from FinanceDataReader.naver.snap import marcap

            logger.info(f"Loading {market} market data...")

            if market == 'KRX':
                # 코스피 + 코스닥
                kospi = marcap('KOSPI', verbose=0)
                kosdaq = marcap('KOSDAQ', verbose=0)
                df = pd.concat([kospi, kosdaq], ignore_index=True)
            else:
                df = marcap(market, verbose=0)

            logger.info(f"Loaded {len(df)} stocks from {market}")
            return df

        except Exception as e:
            logger.error(f"Failed to load market data: {e}")
            return None

    def screen(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        펀더멘털 조건으로 종목을 필터링합니다.

        Args:
            df: 종목 데이터 DataFrame (None이면 자동 로드)

        Returns:
            필터링된 종목 DataFrame
        """
        if df is None:
            df = self.load_market_data('KRX')

        if df is None or df.empty:
            logger.warning("No data to screen")
            return pd.DataFrame()

        original_count = len(df)

        # 컬럼명 정규화 (네이버 marcap 결과에 따라 다를 수 있음)
        df = self._normalize_columns(df)

        # PER 필터링
        per_mask = (df['PER'] > self.per_min) & (df['PER'] < self.per_max)
        per_filtered = df[per_mask]
        logger.info(f"PER filter ({self.per_min} < PER < {self.per_max}): {len(per_filtered)}/{original_count}")

        # PBR 필터링
        pbr_mask = per_filtered['PBR'] < self.pbr_max
        result = per_filtered[pbr_mask]
        logger.info(f"PBR filter (PBR < {self.pbr_max}): {len(result)}/{len(per_filtered)}")

        logger.info(f"Fundamental screening result: {len(result)} stocks passed")

        return result.reset_index(drop=True)

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """컬럼명을 정규화합니다."""
        df = df.copy()

        # 네이버 marcap 컬럼 매핑
        column_mapping = {
            '종목코드': 'Code',
            '종목명': 'Name',
            '현재가': 'Close',
            '시가총액': 'MarketCap',
            '거래량': 'Volume',
        }

        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and new_name not in df.columns:
                df[new_name] = df[old_name]

        # PER, PBR 숫자 변환
        for col in ['PER', 'PBR', 'ROE', 'ROA']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # NaN 처리
        df['PER'] = df['PER'].fillna(0)
        df['PBR'] = df['PBR'].fillna(float('inf'))

        return df

    def get_screening_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        스크리닝 결과 요약을 반환합니다.

        Args:
            df: 필터링된 종목 DataFrame

        Returns:
            요약 정보 딕셔너리
        """
        if df.empty:
            return {
                'total_stocks': 0,
                'avg_per': None,
                'avg_pbr': None,
                'sectors': {},
            }

        # 섹터별 분포 (섹터 정보가 있는 경우)
        sectors = {}
        if 'Sector' in df.columns:
            sectors = df['Sector'].value_counts().to_dict()

        return {
            'total_stocks': len(df),
            'avg_per': round(df['PER'].mean(), 2) if 'PER' in df.columns else None,
            'avg_pbr': round(df['PBR'].mean(), 2) if 'PBR' in df.columns else None,
            'min_per': round(df['PER'].min(), 2) if 'PER' in df.columns else None,
            'max_per': round(df['PER'].max(), 2) if 'PER' in df.columns else None,
            'min_pbr': round(df['PBR'].min(), 2) if 'PBR' in df.columns else None,
            'max_pbr': round(df['PBR'].max(), 2) if 'PBR' in df.columns else None,
            'sectors': sectors,
        }
