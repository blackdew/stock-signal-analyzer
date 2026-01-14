"""전고점 돌파 전략 스크리너

52주 신고가 근접 종목을 필터링하고 돌파 확률을 평가합니다.

스크리닝 조건:
    - 현재가가 52주 고점의 90~105% 범위 내
    - 시가총액 >= 2000억
    - 일평균 거래대금 >= 50억
    - (선택) 전고점 돌파 시도 횟수 >= 3회

실행 방법:
    uv run python -m src.screener.main --strategy breakout
"""

import pandas as pd
import FinanceDataReader as fdr
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import setup_logger
import config

logger = setup_logger(__name__)


class BreakoutScreener:
    """전고점 돌파 전략 스크리너"""

    def __init__(
        self,
        high_range_min: float = None,
        high_range_max: float = None,
        min_market_cap: float = None,
        min_avg_trading_value: float = None,
        attempt_threshold: float = None,
        attempt_lookback_days: int = None,
        week52_lookback_days: int = None,
        stop_loss_pct: float = None,
        trailing_stop_ma: int = None,
    ):
        """
        Args:
            high_range_min: 52주 고점 대비 최소 비율 (기본 0.90)
            high_range_max: 52주 고점 대비 최대 비율 (기본 1.05)
            min_market_cap: 최소 시가총액 (억원, 기본 2000)
            min_avg_trading_value: 최소 일평균 거래대금 (억원, 기본 50)
            attempt_threshold: 돌파 시도로 간주하는 비율 (기본 0.95)
            attempt_lookback_days: 돌파 시도 확인 기간 (기본 60일)
            week52_lookback_days: 52주 = 약 252 거래일
            stop_loss_pct: 절대 손절 비율 (기본 0.05)
            trailing_stop_ma: 상대 손절 MA 기간 (기본 20)
        """
        self.high_range_min = high_range_min or config.BREAKOUT_HIGH_RANGE_MIN
        self.high_range_max = high_range_max or config.BREAKOUT_HIGH_RANGE_MAX
        self.min_market_cap = min_market_cap or config.BREAKOUT_MIN_MARKET_CAP
        self.min_avg_trading_value = min_avg_trading_value or config.BREAKOUT_MIN_AVG_TRADING_VALUE
        self.attempt_threshold = attempt_threshold or config.BREAKOUT_ATTEMPT_THRESHOLD
        self.attempt_lookback_days = attempt_lookback_days or config.BREAKOUT_ATTEMPT_LOOKBACK_DAYS
        self.week52_lookback_days = week52_lookback_days or config.WEEK52_LOOKBACK_DAYS
        self.stop_loss_pct = stop_loss_pct or config.BREAKOUT_STOP_LOSS_PCT
        self.trailing_stop_ma = trailing_stop_ma or config.BREAKOUT_TRAILING_STOP_MA

    def calculate_52week_high(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        52주 신고가 정보를 계산합니다.

        Args:
            df: 주가 데이터 DataFrame (최소 252일)

        Returns:
            {
                'high_52w': 52주 최고가,
                'high_52w_date': 최고가 발생일,
                'current_price': 현재가,
                'pct_from_high': 고점 대비 현재가 비율 (0.95 = 95%)
            }
        """
        if df is None or len(df) < 20:
            return None

        # 52주(252거래일) 또는 가용 데이터 중 작은 값 사용
        lookback = min(self.week52_lookback_days, len(df))
        recent_data = df.tail(lookback)

        high_52w = recent_data['High'].max()
        high_52w_date = recent_data['High'].idxmax()
        current_price = df['Close'].iloc[-1]
        pct_from_high = current_price / high_52w if high_52w > 0 else 0

        return {
            'high_52w': high_52w,
            'high_52w_date': high_52w_date,
            'current_price': current_price,
            'pct_from_high': pct_from_high,
        }

    def count_breakout_attempts(
        self,
        df: pd.DataFrame,
        high_52w: float,
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        최근 N일 내 전고점 돌파 시도 횟수를 계산합니다.

        고점의 threshold% 이상 도달한 날을 "돌파 시도"로 간주합니다.
        연속 시도는 1회로 카운트합니다.

        Args:
            df: 주가 데이터 DataFrame
            high_52w: 52주 최고가
            threshold: 돌파 시도로 간주하는 비율 (기본 0.95)

        Returns:
            {
                'attempt_count': 돌파 시도 횟수,
                'attempt_dates': [시도 날짜 리스트],
                'last_attempt_date': 마지막 시도 날짜
            }
        """
        if threshold is None:
            threshold = self.attempt_threshold

        if df is None or len(df) < 10 or high_52w <= 0:
            return {'attempt_count': 0, 'attempt_dates': [], 'last_attempt_date': None}

        # 최근 N일 데이터
        lookback = min(self.attempt_lookback_days, len(df))
        recent = df.tail(lookback).copy()

        # 고점의 threshold% 이상 도달한 날 마킹
        target_price = high_52w * threshold
        recent['near_high'] = recent['High'] >= target_price

        # 연속된 True를 그룹화하여 시도 횟수 계산
        recent['attempt_group'] = (recent['near_high'] != recent['near_high'].shift()).cumsum()
        attempts = recent[recent['near_high']].groupby('attempt_group').first()

        attempt_dates = attempts.index.tolist()
        last_attempt = attempt_dates[-1] if attempt_dates else None

        return {
            'attempt_count': len(attempts),
            'attempt_dates': attempt_dates,
            'last_attempt_date': last_attempt,
        }

    def calculate_avg_trading_value(
        self,
        df: pd.DataFrame,
        lookback_days: int = 20
    ) -> float:
        """
        일평균 거래대금을 계산합니다.

        거래대금 = 종가 * 거래량

        Args:
            df: 주가 데이터 DataFrame
            lookback_days: 평균 계산 기간 (기본 20일)

        Returns:
            일평균 거래대금 (억원)
        """
        if df is None or len(df) < lookback_days:
            return 0.0

        trading_value = df['Close'] * df['Volume']
        avg_value = trading_value.tail(lookback_days).mean()

        # 억원 단위로 변환
        return avg_value / 100_000_000

    def calculate_ma(self, df: pd.DataFrame, period: int = 20) -> float:
        """이동평균선 계산"""
        if df is None or len(df) < period:
            return 0.0
        return df['Close'].tail(period).mean()

    def analyze_stock(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        개별 종목의 전고점 돌파 분석을 수행합니다.

        Args:
            stock_code: 종목코드

        Returns:
            분석 결과 딕셔너리 또는 None
        """
        try:
            # 충분한 데이터를 위해 52주 + 여유분 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.week52_lookback_days + 30)

            df = fdr.DataReader(stock_code, start_date, end_date)

            if df is None or len(df) < 60:
                return None

            # 52주 신고가 계산
            high_info = self.calculate_52week_high(df)
            if high_info is None:
                return None

            high_52w = high_info['high_52w']
            current_price = high_info['current_price']
            pct_from_high = high_info['pct_from_high']

            # 전고점 근접 여부 (90% ~ 105%)
            in_breakout_zone = self.high_range_min <= pct_from_high <= self.high_range_max

            # 돌파 시도 횟수
            attempt_info = self.count_breakout_attempts(df, high_52w)

            # 거래대금 계산
            avg_trading_value = self.calculate_avg_trading_value(df)

            # MA20 계산 (상대 손절용)
            ma20 = self.calculate_ma(df, self.trailing_stop_ma)

            # 통과 여부 판정
            # 조건: 전고점 근접 + 거래대금 충족
            passed = in_breakout_zone and avg_trading_value >= self.min_avg_trading_value

            # 분석 결과 생성
            analysis = {
                'code': stock_code,
                'current_price': current_price,
                'high_52w': high_52w,
                'high_52w_date': high_info['high_52w_date'],
                'pct_from_high': pct_from_high,
                'in_breakout_zone': in_breakout_zone,
                'attempt_count': attempt_info['attempt_count'],
                'attempt_dates': attempt_info['attempt_dates'],
                'last_attempt_date': attempt_info['last_attempt_date'],
                'avg_trading_value': round(avg_trading_value, 1),
                'ma20': round(ma20, 0),
                'passed': passed,
            }

            # 돌파 확률 점수 계산
            analysis['breakout_score'] = self.calculate_breakout_score(analysis)

            # 매도/손절 전략
            analysis['sell_strategy'] = self.get_sell_strategy(analysis)

            return analysis

        except Exception as e:
            logger.debug(f"Error analyzing {stock_code}: {e}")
            return None

    def calculate_breakout_score(self, analysis: Dict[str, Any]) -> int:
        """
        돌파 확률 점수를 계산합니다.

        점수 구성 (총 100점):
        - 고점 근접도 (최대 40점): 100%에 가까울수록 높음
        - 돌파 시도 횟수 (최대 30점): 3회 이상이면 만점
        - 거래대금 (최대 30점): 100억 이상이면 만점

        Args:
            analysis: 분석 결과 딕셔너리

        Returns:
            돌파 확률 점수 (0-100)
        """
        score = 0

        # 1. 고점 근접도 (40점)
        pct = analysis.get('pct_from_high', 0)
        if pct >= 1.0:  # 신고가 돌파
            score += 40
        elif pct >= 0.98:
            score += 35
        elif pct >= 0.95:
            score += 30
        elif pct >= 0.92:
            score += 25
        elif pct >= 0.90:
            score += 20

        # 2. 돌파 시도 횟수 (30점)
        attempts = analysis.get('attempt_count', 0)
        if attempts >= 4:
            score += 30
        elif attempts >= 3:
            score += 25
        elif attempts >= 2:
            score += 15
        elif attempts >= 1:
            score += 5

        # 3. 거래대금 (30점)
        trading_value = analysis.get('avg_trading_value', 0)
        if trading_value >= 200:
            score += 30
        elif trading_value >= 100:
            score += 25
        elif trading_value >= 50:
            score += 20
        elif trading_value >= 30:
            score += 10

        return min(100, score)

    def get_sell_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        매도/손절 전략을 생성합니다.

        Args:
            analysis: 분석 결과 딕셔너리

        Returns:
            {
                'stop_loss_price': 절대 손절가 (-5%),
                'stop_loss_pct': -5.0,
                'trailing_stop_support': MA20 가격,
                'sell_targets': [목표가 리스트],
                'strategy_message': '매도 전략 설명'
            }
        """
        current_price = analysis.get('current_price', 0)
        high_52w = analysis.get('high_52w', 0)
        ma20 = analysis.get('ma20', 0)

        # 절대 손절가 (-5%)
        stop_loss_price = current_price * (1 - self.stop_loss_pct)

        # 목표가 설정
        sell_targets = []

        # 1차 목표: 전고점 도달
        if current_price < high_52w:
            sell_targets.append({
                'price': high_52w,
                'ratio': 0.3,
                'reason': '전고점 도달'
            })

        # 2차 목표: 신고가 +5%
        sell_targets.append({
            'price': high_52w * 1.05,
            'ratio': 0.5,
            'reason': '신고가 +5%'
        })

        # 3차 목표: 신고가 +10%
        sell_targets.append({
            'price': high_52w * 1.10,
            'ratio': 0.2,
            'reason': '신고가 +10%'
        })

        # 전략 메시지
        pct = analysis.get('pct_from_high', 0)
        attempts = analysis.get('attempt_count', 0)

        if pct >= 0.98:
            if attempts >= 3:
                message = f"전고점 매우 근접({pct*100:.1f}%), {attempts}회 시도로 돌파 확률 높음. 소량 선진입 후 돌파 시 추가 매수 고려."
            else:
                message = f"전고점 매우 근접({pct*100:.1f}%), 돌파 여부 관찰 후 진입 권장."
        elif pct >= 0.95:
            message = f"전고점 근접({pct*100:.1f}%), 거래량 증가와 함께 돌파 시도 시 매수 고려."
        else:
            message = f"전고점 대비 {pct*100:.1f}% 수준, 추가 상승 여력 확인 필요."

        return {
            'stop_loss_price': round(stop_loss_price, 0),
            'stop_loss_pct': -self.stop_loss_pct * 100,
            'trailing_stop_support': round(ma20, 0),
            'sell_targets': sell_targets,
            'strategy_message': message,
        }

    def screen(
        self,
        stock_codes: List[str],
        max_workers: int = 10,
        use_parallel: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        전고점 돌파 조건으로 종목을 필터링합니다.

        Args:
            stock_codes: 분석할 종목코드 리스트
            max_workers: 병렬 처리 시 최대 워커 수 (기본: 10)
            use_parallel: 병렬 처리 사용 여부 (기본: True)

        Returns:
            (통과 종목 DataFrame, 전체 분석 결과 DataFrame)
        """
        logger.info(f"Breakout screening for {len(stock_codes)} stocks (parallel: {use_parallel}, workers: {max_workers})...")

        if use_parallel:
            results = self._screen_parallel(stock_codes, max_workers)
        else:
            results = self._screen_sequential(stock_codes)

        if not results:
            return pd.DataFrame(), pd.DataFrame()

        all_df = pd.DataFrame(results)
        passed_df = all_df[all_df['passed']].copy()

        # 점수순 정렬
        if not passed_df.empty:
            passed_df = passed_df.sort_values('breakout_score', ascending=False)

        passed_count = len(passed_df)
        logger.info(f"Breakout screening result: {passed_count} passed, {len(results) - passed_count} failed")

        return passed_df, all_df

    def _screen_parallel(
        self,
        stock_codes: List[str],
        max_workers: int = 10
    ) -> List[Dict[str, Any]]:
        """병렬 처리로 종목을 분석합니다."""
        results = []
        completed = 0
        total = len(stock_codes)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 작업 제출
            future_to_code = {
                executor.submit(self.analyze_stock, code): code
                for code in stock_codes
            }

            # 완료된 작업 수집
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                completed += 1

                try:
                    analysis = future.result()
                    if analysis:
                        results.append(analysis)
                except Exception as e:
                    logger.debug(f"Error analyzing {code}: {e}")

                # 진행 상황 로깅 (20% 단위)
                if completed % max(1, total // 5) == 0:
                    passed = sum(1 for r in results if r.get('passed', False))
                    logger.info(f"Progress: {completed}/{total} ({completed*100//total}%) - passed: {passed}")

        return results

    def _screen_sequential(
        self,
        stock_codes: List[str],
        delay: float = 0.1
    ) -> List[Dict[str, Any]]:
        """순차적으로 종목을 분석합니다."""
        results = []
        passed_count = 0

        for i, code in enumerate(stock_codes):
            try:
                analysis = self.analyze_stock(code)
                if analysis:
                    results.append(analysis)
                    if analysis['passed']:
                        passed_count += 1

                # 진행 상황 로깅
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i + 1}/{len(stock_codes)} (passed: {passed_count})")

                # API 호출 간격
                time.sleep(delay)

            except Exception as e:
                logger.debug(f"Error analyzing {code}: {e}")

        return results

    def filter_by_market_cap(
        self,
        market_df: pd.DataFrame,
        market_cap_column: str = None
    ) -> pd.DataFrame:
        """
        시가총액 기준으로 필터링합니다.

        Args:
            market_df: 시장 데이터 DataFrame
            market_cap_column: 시가총액 컬럼명 (자동 감지)

        Returns:
            필터링된 DataFrame
        """
        if market_df.empty:
            return market_df

        # 시가총액 컬럼 자동 감지
        if market_cap_column is None:
            for col in ['시가총액', 'Marcap', 'MarketCap']:
                if col in market_df.columns:
                    market_cap_column = col
                    break

        if market_cap_column is None or market_cap_column not in market_df.columns:
            logger.warning(f"Market cap column not found in: {market_df.columns.tolist()[:10]}")
            return market_df

        # 억원 단위 변환이 필요한 경우
        cap_values = market_df[market_cap_column]
        if cap_values.max() > 1e10:  # 원 단위인 경우
            min_cap = self.min_market_cap * 1e8  # 억원 -> 원
        else:
            min_cap = self.min_market_cap

        filtered = market_df[market_df[market_cap_column] >= min_cap]
        logger.info(f"Market cap filter: {len(market_df)} -> {len(filtered)} (>= {self.min_market_cap}억)")

        return filtered
