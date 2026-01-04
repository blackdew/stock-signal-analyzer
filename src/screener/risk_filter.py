"""리스크 필터

밸류 트랩을 피하기 위한 부정적 스크리닝(Negative Screening)을 수행합니다.

제외 조건:
    - 최근 3년 연속 영업이익 적자
    - 부채비율 > 200%
    - 시가총액 < 500억
    - 관리종목/투자주의 종목
"""

import pandas as pd
import FinanceDataReader as fdr
import time
from typing import Optional, Dict, List, Any, Set, Tuple
from src.utils.logger import setup_logger
from .opendart_client import OpenDartClient, get_opendart_client

logger = setup_logger(__name__)


class RiskFilter:
    """리스크 기반 종목 필터"""

    def __init__(
        self,
        min_market_cap: float = 500.0,  # 최소 시가총액 (억원)
        max_debt_ratio: float = 200.0,  # 최대 부채비율 (%)
        loss_years: int = 3,  # 연속 적자 확인 연수
        opendart_client: Optional[OpenDartClient] = None,
    ):
        """
        Args:
            min_market_cap: 최소 시가총액 (억원)
            max_debt_ratio: 최대 부채비율 (%)
            loss_years: 연속 적자 확인 연수
            opendart_client: OpenDART 클라이언트 (None이면 자동 생성)
        """
        self.min_market_cap = min_market_cap
        self.max_debt_ratio = max_debt_ratio
        self.loss_years = loss_years
        self.opendart_client = opendart_client or get_opendart_client()
        self._administrative_stocks: Optional[Set[str]] = None

    def _load_administrative_stocks(self) -> Set[str]:
        """관리종목/투자주의 종목을 로드합니다."""
        if self._administrative_stocks is not None:
            return self._administrative_stocks

        try:
            logger.info("Loading administrative stocks...")
            admin_df = fdr.StockListing('KRX-ADMINISTRATIVE')

            if admin_df is not None and not admin_df.empty:
                code_col = 'Code' if 'Code' in admin_df.columns else '종목코드'
                self._administrative_stocks = set(admin_df[code_col].tolist())
                logger.info(f"Loaded {len(self._administrative_stocks)} administrative stocks")
            else:
                self._administrative_stocks = set()

        except Exception as e:
            logger.warning(f"Failed to load administrative stocks: {e}")
            self._administrative_stocks = set()

        return self._administrative_stocks

    def filter_by_market_cap(
        self,
        df: pd.DataFrame,
        market_cap_column: str = '시가총액'
    ) -> pd.DataFrame:
        """
        시가총액 기준으로 필터링합니다.

        Args:
            df: 종목 DataFrame
            market_cap_column: 시가총액 컬럼명

        Returns:
            필터링된 DataFrame
        """
        if market_cap_column not in df.columns:
            # 다른 가능한 컬럼명 시도
            for col in ['MarketCap', 'Marcap', 'market_cap']:
                if col in df.columns:
                    market_cap_column = col
                    break
            else:
                logger.warning(f"Market cap column not found in DataFrame")
                return df

        original_count = len(df)

        # 시가총액 단위 확인 (억원 vs 원)
        df = df.copy()
        market_cap = pd.to_numeric(df[market_cap_column], errors='coerce')

        # 값이 매우 크면 원 단위로 추정 → 억원으로 변환
        if market_cap.median() > 1e10:  # 100억 이상이면 원 단위
            market_cap = market_cap / 1e8

        df['_market_cap_억'] = market_cap

        filtered = df[df['_market_cap_억'] >= self.min_market_cap].copy()
        filtered = filtered.drop(columns=['_market_cap_억'])

        excluded = original_count - len(filtered)
        logger.info(f"Market cap filter (>= {self.min_market_cap}억): excluded {excluded} stocks")

        return filtered

    def filter_by_administrative(
        self,
        df: pd.DataFrame,
        code_column: str = 'Code'
    ) -> pd.DataFrame:
        """
        관리종목/투자주의 종목을 제외합니다.

        Args:
            df: 종목 DataFrame
            code_column: 종목코드 컬럼명

        Returns:
            필터링된 DataFrame
        """
        admin_stocks = self._load_administrative_stocks()

        if not admin_stocks:
            return df

        # 코드 컬럼 찾기
        if code_column not in df.columns:
            for col in ['종목코드', 'code', 'Symbol']:
                if col in df.columns:
                    code_column = col
                    break
            else:
                return df

        original_count = len(df)
        filtered = df[~df[code_column].isin(admin_stocks)]

        excluded = original_count - len(filtered)
        logger.info(f"Administrative filter: excluded {excluded} stocks")

        return filtered

    def filter_by_financials(
        self,
        df: pd.DataFrame,
        code_column: str = 'Code',
        delay: float = 0.2
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        재무제표 기준으로 필터링합니다 (OpenDART API 사용).

        Args:
            df: 종목 DataFrame
            code_column: 종목코드 컬럼명
            delay: API 호출 간 지연 시간

        Returns:
            (필터링된 DataFrame, 제외 사유 딕셔너리)
        """
        if df.empty:
            return df, {}

        # 코드 컬럼 찾기
        if code_column not in df.columns:
            for col in ['종목코드', 'code', 'Symbol']:
                if col in df.columns:
                    code_column = col
                    break

        codes = df[code_column].tolist()
        excluded_reasons: Dict[str, str] = {}
        passed_codes: List[str] = []

        logger.info(f"Checking financials for {len(codes)} stocks...")

        for i, code in enumerate(codes):
            try:
                # 재무 정보 조회
                financial_summary = self.opendart_client.get_financial_summary(code, self.loss_years)

                if financial_summary is None:
                    # 데이터 없음 - 통과 (신규 상장 등)
                    passed_codes.append(code)
                    continue

                # 연속 적자 체크
                if financial_summary.get('has_consecutive_losses'):
                    excluded_reasons[code] = f"연속 {self.loss_years}년 영업적자"
                    continue

                # 부채비율 체크
                debt_ratio = financial_summary.get('latest_debt_ratio')
                if debt_ratio is not None and debt_ratio > self.max_debt_ratio:
                    excluded_reasons[code] = f"부채비율 {debt_ratio:.1f}% (>{self.max_debt_ratio}%)"
                    continue

                passed_codes.append(code)

                # 진행 상황
                if (i + 1) % 20 == 0:
                    logger.info(f"Financial check progress: {i + 1}/{len(codes)}")

                time.sleep(delay)

            except Exception as e:
                logger.warning(f"Error checking financials for {code}: {e}")
                # 에러 시 일단 통과
                passed_codes.append(code)

        # 필터링된 DataFrame 생성
        filtered = df[df[code_column].isin(passed_codes)].copy()

        logger.info(f"Financial filter: {len(passed_codes)} passed, {len(excluded_reasons)} excluded")

        return filtered, excluded_reasons

    def apply_all_filters(
        self,
        df: pd.DataFrame,
        code_column: str = 'Code',
        skip_financial_check: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        모든 리스크 필터를 적용합니다.

        Args:
            df: 종목 DataFrame
            code_column: 종목코드 컬럼명
            skip_financial_check: 재무 체크 건너뛰기 (테스트용)

        Returns:
            (필터링된 DataFrame, 필터링 통계)
        """
        stats = {
            'original_count': len(df),
            'after_market_cap': 0,
            'after_administrative': 0,
            'after_financials': 0,
            'excluded_reasons': {},
        }

        # 1. 시가총액 필터
        df = self.filter_by_market_cap(df)
        stats['after_market_cap'] = len(df)

        # 2. 관리종목 필터
        df = self.filter_by_administrative(df, code_column)
        stats['after_administrative'] = len(df)

        # 3. 재무 필터 (OpenDART)
        if not skip_financial_check:
            df, excluded = self.filter_by_financials(df, code_column)
            stats['after_financials'] = len(df)
            stats['excluded_reasons'] = excluded
        else:
            stats['after_financials'] = len(df)

        logger.info(f"Risk filtering complete: {stats['original_count']} -> {len(df)} stocks")

        return df, stats
