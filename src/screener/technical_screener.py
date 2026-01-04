"""기술적 스크리너

상승 국면 진입 종목을 필터링합니다.

필터링 조건:
    - 현재가 > 20일 이동평균선
    - 최근 20일 거래량 평균 > 전월 대비 20% 증가
"""

import pandas as pd
import FinanceDataReader as fdr
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TechnicalScreener:
    """기술적 분석 기반 종목 스크리너"""

    def __init__(
        self,
        ma_period: int = 20,
        volume_increase_threshold: float = 0.20,  # 20% 증가
        lookback_days: int = 60,  # 분석 기간 (20일 + 전월 20일)
    ):
        """
        Args:
            ma_period: 이동평균 기간 (기본 20일)
            volume_increase_threshold: 거래량 증가 임계값 (기본 20%)
            lookback_days: 분석 기간 (기본 60일)
        """
        self.ma_period = ma_period
        self.volume_increase_threshold = volume_increase_threshold
        self.lookback_days = lookback_days

    def screen(
        self,
        stock_codes: List[str],
        max_workers: int = 5,
        delay: float = 0.1
    ) -> pd.DataFrame:
        """
        기술적 조건으로 종목을 필터링합니다.

        Args:
            stock_codes: 분석할 종목코드 리스트
            max_workers: 병렬 처리 워커 수
            delay: API 호출 간 지연 시간 (초)

        Returns:
            필터링된 종목 DataFrame
        """
        logger.info(f"Technical screening for {len(stock_codes)} stocks...")

        results = []
        passed_count = 0
        failed_count = 0

        # 순차 처리 (API 제한 고려)
        for i, code in enumerate(stock_codes):
            try:
                analysis = self.analyze_stock(code)
                if analysis:
                    if analysis['passed']:
                        results.append(analysis)
                        passed_count += 1
                    else:
                        failed_count += 1

                # 진행 상황 로깅
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i + 1}/{len(stock_codes)} (passed: {passed_count})")

                # API 호출 간격
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error analyzing {code}: {e}")
                failed_count += 1

        logger.info(f"Technical screening result: {passed_count} passed, {failed_count} failed")

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results)

    def analyze_stock(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        개별 종목의 기술적 분석을 수행합니다.

        Args:
            stock_code: 종목코드

        Returns:
            분석 결과 딕셔너리 또는 None
        """
        try:
            # 날짜 범위 설정
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)

            # 주가 데이터 조회
            df = fdr.DataReader(stock_code, start_date, end_date)

            if df is None or len(df) < self.ma_period * 2:
                return None

            # 기술적 지표 계산
            df['MA20'] = df['Close'].rolling(window=self.ma_period).mean()
            df['Volume_MA20'] = df['Volume'].rolling(window=self.ma_period).mean()

            # 최근 데이터
            latest = df.iloc[-1]
            current_price = latest['Close']
            ma20 = latest['MA20']

            # 조건 1: 현재가 > MA20
            above_ma20 = current_price > ma20

            # 조건 2: 거래량 증가 확인
            # 최근 20일 평균 vs 이전 20일 평균
            recent_volume = df['Volume'].tail(self.ma_period).mean()
            prev_volume = df['Volume'].iloc[-(self.ma_period * 2):-self.ma_period].mean()

            volume_change = 0.0
            if prev_volume > 0:
                volume_change = (recent_volume - prev_volume) / prev_volume

            volume_increased = volume_change >= self.volume_increase_threshold

            # 최종 판정
            passed = above_ma20 and volume_increased

            return {
                'Code': stock_code,
                'current_price': current_price,
                'ma20': round(ma20, 2),
                'above_ma20': above_ma20,
                'price_vs_ma20_pct': round((current_price / ma20 - 1) * 100, 2) if ma20 > 0 else 0,
                'recent_volume_avg': int(recent_volume),
                'prev_volume_avg': int(prev_volume),
                'volume_change_pct': round(volume_change * 100, 2),
                'volume_increased': volume_increased,
                'passed': passed,
            }

        except Exception as e:
            logger.debug(f"Error analyzing {stock_code}: {e}")
            return None

    def get_price_momentum(self, stock_code: str, periods: List[int] = [5, 10, 20]) -> Optional[Dict[str, float]]:
        """
        가격 모멘텀을 계산합니다.

        Args:
            stock_code: 종목코드
            periods: 모멘텀 계산 기간 리스트

        Returns:
            모멘텀 딕셔너리 {5d: 5%, 10d: 3%, 20d: 10%}
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=max(periods) + 10)

            df = fdr.DataReader(stock_code, start_date, end_date)

            if df is None or len(df) < max(periods):
                return None

            current_price = df['Close'].iloc[-1]
            momentum = {}

            for period in periods:
                if len(df) > period:
                    past_price = df['Close'].iloc[-period - 1]
                    change = (current_price - past_price) / past_price * 100
                    momentum[f'{period}d'] = round(change, 2)

            return momentum

        except Exception as e:
            logger.debug(f"Error calculating momentum for {stock_code}: {e}")
            return None

    def batch_analyze(
        self,
        fundamental_df: pd.DataFrame,
        code_column: str = 'Code'
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        펀더멘털 스크리닝 결과에 기술적 분석을 추가합니다.

        Args:
            fundamental_df: 펀더멘털 스크리닝 결과 DataFrame
            code_column: 종목코드 컬럼명

        Returns:
            (통과 종목 DataFrame, 실패 종목 DataFrame)
        """
        if fundamental_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # 종목코드 추출
        if code_column in fundamental_df.columns:
            codes = fundamental_df[code_column].tolist()
        elif '종목코드' in fundamental_df.columns:
            codes = fundamental_df['종목코드'].tolist()
        else:
            logger.error(f"Code column not found in DataFrame")
            return pd.DataFrame(), pd.DataFrame()

        # 기술적 분석 수행
        technical_df = self.screen(codes)

        if technical_df.empty:
            return pd.DataFrame(), fundamental_df

        # 통과 종목 필터링
        passed_codes = set(technical_df[technical_df['passed']]['Code'].tolist())

        # 펀더멘털 데이터와 병합
        code_col = code_column if code_column in fundamental_df.columns else '종목코드'
        passed_df = fundamental_df[fundamental_df[code_col].isin(passed_codes)].copy()
        failed_df = fundamental_df[~fundamental_df[code_col].isin(passed_codes)].copy()

        # 기술적 분석 결과 병합
        if not passed_df.empty:
            technical_cols = ['current_price', 'ma20', 'price_vs_ma20_pct',
                           'volume_change_pct', 'above_ma20', 'volume_increased']
            tech_subset = technical_df[technical_df['passed']][['Code'] + technical_cols]
            passed_df = passed_df.merge(tech_subset, left_on=code_col, right_on='Code', how='left')

        logger.info(f"Technical screening: {len(passed_df)} passed, {len(failed_df)} failed")

        return passed_df, failed_df
