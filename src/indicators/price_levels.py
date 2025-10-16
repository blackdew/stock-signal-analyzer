"""바닥/천장 가격 수준 감지 모듈"""
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Optional


class PriceLevelDetector:
    """주가의 바닥과 천장을 감지하는 클래스"""

    def __init__(self, lookback_period: int = 60, atr_period: int = 14):
        """
        Args:
            lookback_period: 바닥/천장 계산을 위한 lookback 기간 (일)
            atr_period: ATR 계산 기간 (일)
        """
        self.lookback_period = lookback_period
        self.atr_period = atr_period

    def detect_floor_ceiling(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        주가 데이터에서 바닥과 천장을 감지합니다.

        Args:
            df: 주가 데이터 DataFrame (Close 컬럼 필요)

        Returns:
            {
                'floor': 바닥 가격,
                'ceiling': 천장 가격,
                'current': 현재 가격,
                'floor_date': 바닥 발생 날짜,
                'ceiling_date': 천장 발생 날짜
            }
        """
        if df is None or df.empty:
            return {}

        # 최근 lookback_period 일의 데이터 사용
        recent_data = df.tail(self.lookback_period).copy()

        if len(recent_data) < 10:
            return {}

        # 바닥 (최저가)
        floor_idx = recent_data['Close'].idxmin()
        floor_price = recent_data.loc[floor_idx, 'Close']

        # 천장 (최고가)
        ceiling_idx = recent_data['Close'].idxmax()
        ceiling_price = recent_data.loc[ceiling_idx, 'Close']

        # 현재 가격
        current_price = df['Close'].iloc[-1]

        return {
            'floor': floor_price,
            'ceiling': ceiling_price,
            'current': current_price,
            'floor_date': floor_idx,
            'ceiling_date': ceiling_idx
        }

    def calculate_atr(self, df: pd.DataFrame, period: Optional[int] = None) -> pd.Series:
        """
        ATR (Average True Range)를 계산합니다.

        Args:
            df: 주가 데이터 DataFrame (High, Low, Close 컬럼 필요)
            period: ATR 계산 기간 (None이면 self.atr_period 사용)

        Returns:
            ATR Series (NaN 값은 중간값으로 채움)
        """
        if period is None:
            period = self.atr_period

        # 데이터 검증
        if df is None or df.empty:
            return pd.Series([0.0])

        required_columns = ['High', 'Low', 'Close']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            # High, Low 데이터가 없으면 Close 기반으로 간단한 변동성 계산
            if 'Close' in df.columns:
                return df['Close'].rolling(window=period).std().fillna(0)
            return pd.Series([0.0] * len(df))

        # 데이터가 충분한지 확인
        if len(df) < period:
            # 데이터가 부족하면 가능한 만큼만 계산
            actual_period = max(2, len(df))
        else:
            actual_period = period

        try:
            # pandas_ta로 ATR 계산
            atr = ta.atr(
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                length=actual_period
            )

            if atr is None or atr.empty:
                # 계산 실패 시 표준편차로 대체
                return df['Close'].rolling(window=actual_period).std().fillna(0)

            # NaN 값 처리 - 중간값으로 채움
            median_atr = atr.median()
            if pd.isna(median_atr) or median_atr == 0:
                # 중간값도 없으면 표준편차 사용
                return df['Close'].rolling(window=actual_period).std().fillna(0)

            atr = atr.fillna(median_atr)

            # 음수 값 제거
            atr = atr.clip(lower=0)

            return atr

        except Exception as e:
            # 예외 발생 시 표준편차로 대체
            return df['Close'].rolling(window=period).std().fillna(0)

    def calculate_volatility_level(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        변동성 등급을 계산합니다.

        Args:
            df: 주가 데이터 DataFrame

        Returns:
            {
                'level': 'LOW' | 'MEDIUM' | 'HIGH',
                'current_atr': 현재 ATR 값,
                'avg_atr': 평균 ATR 값,
                'adjustment_factor': 임계값 조정 계수
            }
        """
        atr = self.calculate_atr(df)

        if atr is None or atr.empty or len(atr) == 0:
            return {
                'level': 'MEDIUM',
                'current_atr': 0,
                'avg_atr': 0,
                'adjustment_factor': 1.0
            }

        current_atr = atr.iloc[-1]

        # 최근 60일 평균 ATR (또는 가능한 만큼)
        lookback = min(60, len(atr))
        avg_atr = atr.tail(lookback).mean()

        if pd.isna(avg_atr) or avg_atr == 0:
            return {
                'level': 'MEDIUM',
                'current_atr': current_atr,
                'avg_atr': 0,
                'adjustment_factor': 1.0
            }

        # ATR 비율로 변동성 등급 결정
        atr_ratio = current_atr / avg_atr

        if atr_ratio < 0.7:
            level = 'LOW'
            adjustment_factor = 0.8  # 낮은 변동성: 좁은 임계값
        elif atr_ratio > 1.3:
            level = 'HIGH'
            adjustment_factor = 1.3  # 높은 변동성: 넓은 임계값
        else:
            level = 'MEDIUM'
            adjustment_factor = 1.0  # 중간 변동성: 기본값

        return {
            'level': level,
            'current_atr': current_atr,
            'avg_atr': avg_atr,
            'atr_ratio': atr_ratio,
            'adjustment_factor': adjustment_factor
        }

    def calculate_position_metrics(
        self,
        df: pd.DataFrame,
        current_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        현재 가격이 바닥/천장 대비 어느 위치에 있는지 계산합니다.

        Args:
            df: 주가 데이터 DataFrame
            current_price: 현재 가격 (None이면 최근 종가 사용)

        Returns:
            {
                'from_floor_pct': 바닥 대비 상승률 (소수),
                'from_ceiling_pct': 천장 대비 하락률 (소수),
                'position_in_range': 바닥-천장 범위에서의 위치 (0~1)
            }
        """
        levels = self.detect_floor_ceiling(df)

        if not levels:
            return {}

        if current_price is None:
            current_price = levels['current']

        floor = levels['floor']
        ceiling = levels['ceiling']

        # 바닥 대비 상승률
        from_floor_pct = (current_price - floor) / floor if floor > 0 else 0

        # 천장 대비 하락률 (음수)
        from_ceiling_pct = (current_price - ceiling) / ceiling if ceiling > 0 else 0

        # 바닥-천장 범위에서의 상대적 위치 (0=바닥, 1=천장)
        range_size = ceiling - floor
        if range_size > 0:
            position_in_range = (current_price - floor) / range_size
        else:
            position_in_range = 0.5

        return {
            'from_floor_pct': from_floor_pct,
            'from_ceiling_pct': from_ceiling_pct,
            'position_in_range': position_in_range
        }

    def is_at_knee(
        self,
        df: pd.DataFrame,
        knee_threshold: float = 0.15,
        use_dynamic_threshold: bool = True
    ) -> Dict[str, any]:
        """
        바닥 대비 "무릎" 위치에 도달했는지 확인합니다.
        ATR 기반 동적 임계값을 사용합니다.

        Args:
            df: 주가 데이터 DataFrame
            knee_threshold: 기본 무릎 임계값 (기본 15%, 동적 모드에서는 참고용)
            use_dynamic_threshold: ATR 기반 동적 임계값 사용 여부

        Returns:
            {
                'is_at_knee': True/False,
                'from_floor_pct': 바닥 대비 상승률,
                'dynamic_knee_price': 동적 무릎 가격,
                'volatility_level': 변동성 등급,
                'message': 설명 메시지
            }
        """
        metrics = self.calculate_position_metrics(df)

        if not metrics:
            return {'is_at_knee': False, 'message': '데이터 부족'}

        levels = self.detect_floor_ceiling(df)
        if not levels:
            return {'is_at_knee': False, 'message': '데이터 부족'}

        floor_price = levels['floor']
        current_price = levels['current']
        from_floor_pct = metrics['from_floor_pct']

        # 동적 임계값 계산
        if use_dynamic_threshold:
            # ATR 계산
            atr = self.calculate_atr(df)
            current_atr = atr.iloc[-1] if not atr.empty else 0

            # 변동성 등급 계산
            volatility_info = self.calculate_volatility_level(df)
            volatility_level = volatility_info['level']
            adjustment_factor = volatility_info['adjustment_factor']

            # 동적 무릎 가격 = 바닥 가격 + (ATR * 2 * 조정계수)
            dynamic_knee_price = floor_price + (current_atr * 2 * adjustment_factor)

            # 동적 무릎 범위 계산 (무릎 가격 ± ATR)
            lower_bound_price = dynamic_knee_price - current_atr
            upper_bound_price = dynamic_knee_price + current_atr

            is_at_knee = lower_bound_price <= current_price <= upper_bound_price

            if is_at_knee:
                message = f"무릎 위치 (바닥 대비 +{from_floor_pct*100:.1f}%, 변동성: {volatility_level})"
            elif current_price < lower_bound_price:
                message = f"바닥 근처 (바닥 대비 +{from_floor_pct*100:.1f}%, 변동성: {volatility_level})"
            else:
                message = f"무릎 위 (바닥 대비 +{from_floor_pct*100:.1f}%, 변동성: {volatility_level})"

            return {
                'is_at_knee': is_at_knee,
                'from_floor_pct': from_floor_pct,
                'dynamic_knee_price': dynamic_knee_price,
                'volatility_level': volatility_level,
                'current_atr': current_atr,
                'adjustment_factor': adjustment_factor,
                'message': message
            }
        else:
            # 기존 정적 임계값 방식
            lower_bound = knee_threshold - 0.05
            upper_bound = knee_threshold + 0.05

            is_at_knee = lower_bound <= from_floor_pct <= upper_bound

            if is_at_knee:
                message = f"무릎 위치 (바닥 대비 +{from_floor_pct*100:.1f}%)"
            elif from_floor_pct < lower_bound:
                message = f"바닥 근처 (바닥 대비 +{from_floor_pct*100:.1f}%)"
            else:
                message = f"무릎 위 (바닥 대비 +{from_floor_pct*100:.1f}%)"

            return {
                'is_at_knee': is_at_knee,
                'from_floor_pct': from_floor_pct,
                'message': message
            }

    def is_at_shoulder(
        self,
        df: pd.DataFrame,
        shoulder_threshold: float = 0.15,
        use_dynamic_threshold: bool = True
    ) -> Dict[str, any]:
        """
        천장 대비 "어깨" 위치에 도달했는지 확인합니다.
        ATR 기반 동적 임계값을 사용합니다.

        Args:
            df: 주가 데이터 DataFrame
            shoulder_threshold: 기본 어깨 임계값 (기본 15%, 동적 모드에서는 참고용)
            use_dynamic_threshold: ATR 기반 동적 임계값 사용 여부

        Returns:
            {
                'is_at_shoulder': True/False,
                'from_ceiling_pct': 천장 대비 하락률,
                'dynamic_shoulder_price': 동적 어깨 가격,
                'volatility_level': 변동성 등급,
                'message': 설명 메시지
            }
        """
        metrics = self.calculate_position_metrics(df)

        if not metrics:
            return {'is_at_shoulder': False, 'message': '데이터 부족'}

        levels = self.detect_floor_ceiling(df)
        if not levels:
            return {'is_at_shoulder': False, 'message': '데이터 부족'}

        ceiling_price = levels['ceiling']
        current_price = levels['current']
        from_ceiling_pct = metrics['from_ceiling_pct']

        # 동적 임계값 계산
        if use_dynamic_threshold:
            # ATR 계산
            atr = self.calculate_atr(df)
            current_atr = atr.iloc[-1] if not atr.empty else 0

            # 변동성 등급 계산
            volatility_info = self.calculate_volatility_level(df)
            volatility_level = volatility_info['level']
            adjustment_factor = volatility_info['adjustment_factor']

            # 동적 어깨 가격 = 천장 가격 - (ATR * 2 * 조정계수)
            dynamic_shoulder_price = ceiling_price - (current_atr * 2 * adjustment_factor)

            # 동적 어깨 범위 계산 (어깨 가격 ± ATR)
            lower_bound_price = dynamic_shoulder_price - current_atr
            upper_bound_price = dynamic_shoulder_price + current_atr

            is_at_shoulder = lower_bound_price <= current_price <= upper_bound_price

            if is_at_shoulder:
                message = f"어깨 위치 (천장 대비 {from_ceiling_pct*100:.1f}%, 변동성: {volatility_level})"
            elif current_price > upper_bound_price:
                message = f"천장 근처 (천장 대비 {from_ceiling_pct*100:.1f}%, 변동성: {volatility_level})"
            else:
                message = f"어깨 아래 (천장 대비 {from_ceiling_pct*100:.1f}%, 변동성: {volatility_level})"

            return {
                'is_at_shoulder': is_at_shoulder,
                'from_ceiling_pct': from_ceiling_pct,
                'dynamic_shoulder_price': dynamic_shoulder_price,
                'volatility_level': volatility_level,
                'current_atr': current_atr,
                'adjustment_factor': adjustment_factor,
                'message': message
            }
        else:
            # 기존 정적 임계값 방식
            lower_bound = -shoulder_threshold - 0.05
            upper_bound = -shoulder_threshold + 0.05

            is_at_shoulder = lower_bound <= from_ceiling_pct <= upper_bound

            if is_at_shoulder:
                message = f"어깨 위치 (천장 대비 {from_ceiling_pct*100:.1f}%)"
            elif from_ceiling_pct > upper_bound:
                message = f"천장 근처 (천장 대비 {from_ceiling_pct*100:.1f}%)"
            else:
                message = f"어깨 아래 (천장 대비 {from_ceiling_pct*100:.1f}%)"

            return {
                'is_at_shoulder': is_at_shoulder,
                'from_ceiling_pct': from_ceiling_pct,
                'message': message
            }
