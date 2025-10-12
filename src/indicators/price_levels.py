"""바닥/천장 가격 수준 감지 모듈"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class PriceLevelDetector:
    """주가의 바닥과 천장을 감지하는 클래스"""

    def __init__(self, lookback_period: int = 60):
        """
        Args:
            lookback_period: 바닥/천장 계산을 위한 lookback 기간 (일)
        """
        self.lookback_period = lookback_period

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
        knee_threshold: float = 0.15
    ) -> Dict[str, any]:
        """
        바닥 대비 "무릎" 위치에 도달했는지 확인합니다.

        Args:
            df: 주가 데이터 DataFrame
            knee_threshold: 무릎으로 간주할 바닥 대비 상승률 (기본 15%)

        Returns:
            {
                'is_at_knee': True/False,
                'from_floor_pct': 바닥 대비 상승률,
                'message': 설명 메시지
            }
        """
        metrics = self.calculate_position_metrics(df)

        if not metrics:
            return {'is_at_knee': False, 'message': '데이터 부족'}

        from_floor_pct = metrics['from_floor_pct']

        # 무릎 범위: knee_threshold ± 5%
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
        shoulder_threshold: float = 0.15
    ) -> Dict[str, any]:
        """
        천장 대비 "어깨" 위치에 도달했는지 확인합니다.

        Args:
            df: 주가 데이터 DataFrame
            shoulder_threshold: 어깨로 간주할 천장 대비 하락률 (기본 15%)

        Returns:
            {
                'is_at_shoulder': True/False,
                'from_ceiling_pct': 천장 대비 하락률,
                'message': 설명 메시지
            }
        """
        metrics = self.calculate_position_metrics(df)

        if not metrics:
            return {'is_at_shoulder': False, 'message': '데이터 부족'}

        from_ceiling_pct = metrics['from_ceiling_pct']

        # 어깨 범위: -shoulder_threshold ± 5%
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
