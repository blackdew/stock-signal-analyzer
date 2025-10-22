"""
시장 추세 분석 유틸리티

KOSPI 지수를 분석하여 전체 시장 상황을 판단합니다.
"""

import pandas as pd
import FinanceDataReader as fdr
from typing import Dict, Optional
from datetime import datetime, timedelta
from .logger import setup_logger

# 로거 초기화
logger = setup_logger(__name__)


class MarketAnalyzer:
    """
    시장 추세 및 변동성 분석기

    KOSPI 지수의 이동평균을 기반으로 시장 국면을 판단하고,
    변동성을 측정하여 리스크 수준을 평가합니다.
    """

    def __init__(self, market_index: str = 'KS11'):
        """
        Args:
            market_index: 시장 지수 코드 (기본: KS11 - KOSPI)
        """
        self.market_index = market_index
        self.cache: Optional[Dict] = None
        self.cache_time: Optional[datetime] = None
        self.cache_duration = timedelta(hours=1)  # 1시간 캐시

    def _fetch_market_data(self, period_days: int = 180) -> Optional[pd.DataFrame]:
        """
        시장 지수 데이터 가져오기

        Args:
            period_days: 분석 기간 (일, 기본 180일)

        Returns:
            DataFrame 또는 None (실패 시)
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            df = fdr.DataReader(
                self.market_index,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if df is None or df.empty:
                logger.warning(f"시장 데이터 없음: {self.market_index}")
                return None

            logger.info(f"시장 데이터 가져오기 성공: {self.market_index} ({len(df)}일)")
            return df

        except Exception as e:
            logger.error(f"시장 데이터 가져오기 실패: {e}")
            return None

    def analyze_trend(self, force_refresh: bool = False) -> str:
        """
        시장 추세 분석

        MA20과 MA60을 비교하여 시장 국면을 판단합니다.

        Args:
            force_refresh: 캐시를 무시하고 새로 분석할지 여부

        Returns:
            'BULL': 상승장 (MA20 > MA60, 차이 2% 이상)
            'BEAR': 하락장 (MA20 < MA60, 차이 -2% 이하)
            'SIDEWAYS': 횡보장 (차이 ±2% 이내)
            'UNKNOWN': 분석 실패
        """
        # 캐시 확인
        if not force_refresh and self._is_cache_valid():
            return self.cache['trend']

        df = self._fetch_market_data(period_days=180)

        if df is None or len(df) < 60:
            logger.warning("시장 추세 분석 불가: 데이터 부족")
            return 'UNKNOWN'

        try:
            # 이동평균 계산
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            ma60 = df['Close'].rolling(window=60).mean().iloc[-1]

            # 차이 비율 계산
            diff_pct = (ma20 - ma60) / ma60

            # 추세 판단
            if diff_pct > 0.02:
                trend = 'BULL'
            elif diff_pct < -0.02:
                trend = 'BEAR'
            else:
                trend = 'SIDEWAYS'

            # 캐시 업데이트
            self._update_cache(df, trend, diff_pct)

            logger.info(f"시장 추세 분석 완료: {trend} (MA20-MA60 차이: {diff_pct*100:.2f}%)")
            return trend

        except Exception as e:
            logger.error(f"시장 추세 계산 오류: {e}")
            return 'UNKNOWN'

    def calculate_volatility(self, force_refresh: bool = False) -> str:
        """
        시장 변동성 계산

        20일 기준 일간 수익률의 표준편차를 계산하여 변동성을 측정합니다.

        Args:
            force_refresh: 캐시를 무시하고 새로 계산할지 여부

        Returns:
            'LOW': 낮은 변동성 (< 1%)
            'MEDIUM': 보통 변동성 (1% ~ 2%)
            'HIGH': 높은 변동성 (> 2%)
            'UNKNOWN': 계산 실패
        """
        # 캐시 확인
        if not force_refresh and self._is_cache_valid():
            return self.cache['volatility']

        df = self._fetch_market_data(period_days=180)

        if df is None or len(df) < 20:
            logger.warning("시장 변동성 계산 불가: 데이터 부족")
            return 'UNKNOWN'

        try:
            # 일간 수익률 계산
            returns = df['Close'].pct_change()

            # 20일 표준편차
            volatility = returns.rolling(window=20).std().iloc[-1]

            # 변동성 등급 분류
            if volatility < 0.01:
                volatility_level = 'LOW'
            elif volatility > 0.02:
                volatility_level = 'HIGH'
            else:
                volatility_level = 'MEDIUM'

            # 캐시에 변동성 정보 추가
            if self.cache:
                self.cache['volatility'] = volatility_level
                self.cache['volatility_value'] = volatility

            logger.info(f"시장 변동성 계산 완료: {volatility_level} ({volatility*100:.2f}%)")
            return volatility_level

        except Exception as e:
            logger.error(f"시장 변동성 계산 오류: {e}")
            return 'UNKNOWN'

    def get_market_summary(self, force_refresh: bool = False) -> Dict:
        """
        시장 전체 요약 정보

        Args:
            force_refresh: 캐시를 무시하고 새로 분석할지 여부

        Returns:
            {
                'trend': 'BULL' | 'BEAR' | 'SIDEWAYS' | 'UNKNOWN',
                'trend_pct': float,  # MA20-MA60 차이 비율
                'volatility': 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN',
                'volatility_value': float,  # 표준편차 값
                'current_price': float,
                'ma20': float,
                'ma60': float,
                'message': str  # 사용자 친화적 메시지
            }
        """
        trend = self.analyze_trend(force_refresh)
        volatility = self.calculate_volatility(force_refresh)

        if self.cache:
            # 메시지 생성
            message = self._generate_market_message(
                self.cache['trend'],
                self.cache['volatility']
            )

            return {
                'trend': self.cache['trend'],
                'trend_pct': self.cache.get('trend_pct', 0.0),
                'volatility': self.cache['volatility'],
                'volatility_value': self.cache.get('volatility_value', 0.0),
                'current_price': self.cache.get('current_price', 0.0),
                'ma20': self.cache.get('ma20', 0.0),
                'ma60': self.cache.get('ma60', 0.0),
                'message': message
            }
        else:
            return {
                'trend': trend,
                'trend_pct': 0.0,
                'volatility': volatility,
                'volatility_value': 0.0,
                'current_price': 0.0,
                'ma20': 0.0,
                'ma60': 0.0,
                'message': '시장 정보를 가져올 수 없습니다.'
            }

    def _is_cache_valid(self) -> bool:
        """캐시가 유효한지 확인"""
        if self.cache is None or self.cache_time is None:
            return False

        elapsed = datetime.now() - self.cache_time
        return elapsed < self.cache_duration

    def _update_cache(self, df: pd.DataFrame, trend: str, trend_pct: float):
        """캐시 업데이트"""
        try:
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            ma60 = df['Close'].rolling(window=60).mean().iloc[-1]
            current_price = df['Close'].iloc[-1]

            self.cache = {
                'trend': trend,
                'trend_pct': trend_pct,
                'current_price': current_price,
                'ma20': ma20,
                'ma60': ma60,
                'volatility': 'UNKNOWN',  # 별도로 계산
                'volatility_value': 0.0
            }
            self.cache_time = datetime.now()

        except Exception as e:
            logger.error(f"캐시 업데이트 오류: {e}")

    def _generate_market_message(self, trend: str, volatility: str) -> str:
        """사용자 친화적 메시지 생성"""
        trend_msg = {
            'BULL': '📈 상승장',
            'BEAR': '📉 하락장',
            'SIDEWAYS': '➡️ 횡보장',
            'UNKNOWN': '❓ 알 수 없음'
        }

        volatility_msg = {
            'LOW': '낮은 변동성',
            'MEDIUM': '보통 변동성',
            'HIGH': '높은 변동성',
            'UNKNOWN': '변동성 알 수 없음'
        }

        return f"{trend_msg.get(trend, '알 수 없음')} / {volatility_msg.get(volatility, '알 수 없음')}"


# 전역 인스턴스 (싱글톤 패턴)
_market_analyzer_instance = None


def get_market_analyzer() -> MarketAnalyzer:
    """
    MarketAnalyzer 싱글톤 인스턴스 가져오기

    여러 곳에서 호출해도 동일한 인스턴스를 사용하여
    캐시 효과를 극대화합니다.
    """
    global _market_analyzer_instance

    if _market_analyzer_instance is None:
        _market_analyzer_instance = MarketAnalyzer()

    return _market_analyzer_instance
