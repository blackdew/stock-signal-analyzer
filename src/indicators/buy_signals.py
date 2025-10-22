"""매수 신호 분석 모듈"""
import pandas as pd
import pandas_ta as ta
from typing import Dict, List
from .price_levels import PriceLevelDetector
from src.utils.logger import setup_logger
from src.utils.helpers import safe_divide, is_valid_number

# 로거 설정
logger = setup_logger(__name__)


class BuySignalAnalyzer:
    """매수 신호를 분석하는 클래스"""

    def __init__(
        self,
        knee_threshold: float = 0.15,
        stop_loss_pct: float = 0.07,
        chase_risk_threshold: float = 0.25,
        rsi_period: int = 14,
        rsi_oversold: int = 30
    ):
        """
        Args:
            knee_threshold: 무릎 판단 기준 (바닥 대비 상승률)
            stop_loss_pct: 손절가 비율
            chase_risk_threshold: 추격매수 위험 기준 (바닥 대비 상승률)
            rsi_period: RSI 계산 기간
            rsi_oversold: RSI 과매도 기준
        """
        self.knee_threshold = knee_threshold
        self.stop_loss_pct = stop_loss_pct
        self.chase_risk_threshold = chase_risk_threshold
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.price_detector = PriceLevelDetector()

    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """
        안전한 RSI 계산

        Args:
            df: 주가 데이터 DataFrame

        Returns:
            RSI Series (실패 시 중립값 50.0으로 채움)
        """
        try:
            if df is None or df.empty:
                logger.warning("RSI 계산 불가: 데이터 없음")
                return pd.Series()

            if len(df) < self.rsi_period:
                logger.warning(
                    f"RSI 계산 불가: 데이터 부족 "
                    f"(필요: {self.rsi_period}, 현재: {len(df)})"
                )
                return pd.Series([50.0] * len(df))

            # RSI 계산
            rsi = ta.rsi(df['Close'], length=self.rsi_period)

            # NaN 값 처리
            rsi = rsi.fillna(50.0)  # 중립값으로 채움

            # 범위 검증 (0-100)
            rsi = rsi.clip(0, 100)

            logger.debug(f"RSI 계산 성공: 최근값 {rsi.iloc[-1]:.2f}")
            return rsi

        except Exception as e:
            logger.error(f"RSI 계산 중 오류: {str(e)}")
            return pd.Series([50.0] * len(df)) if df is not None else pd.Series()

    def check_volume_surge(self, df: pd.DataFrame, multiplier: float = 2.0) -> bool:
        """
        거래량 급증 여부를 확인합니다.

        Args:
            df: 주가 데이터 DataFrame
            multiplier: 평균 거래량 대비 배수

        Returns:
            True if 거래량 급증
        """
        try:
            if df is None or len(df) < 20:
                logger.debug("거래량 급증 체크 불가: 데이터 부족")
                return False

            current_volume = df['Volume'].iloc[-1]
            avg_volume = df['Volume'].tail(20).mean()

            # 유효성 검증
            if not is_valid_number(current_volume) or not is_valid_number(avg_volume):
                logger.warning("거래량 급증 체크 불가: 유효하지 않은 값")
                return False

            if avg_volume == 0:
                logger.warning("거래량 급증 체크 불가: 평균 거래량이 0")
                return False

            is_surge = current_volume >= avg_volume * multiplier
            if is_surge:
                logger.info(
                    f"거래량 급증 감지: 현재 {current_volume:,.0f} "
                    f"(평균 {avg_volume:,.0f}의 {current_volume/avg_volume:.1f}배)"
                )

            return is_surge

        except Exception as e:
            logger.error(f"거래량 급증 체크 중 오류: {str(e)}")
            return False

    def check_golden_cross(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        골든크로스 발생 여부를 확인합니다.

        Returns:
            {
                'is_golden_cross': True/False,
                'ma_short': 단기 이동평균,
                'ma_long': 장기 이동평균,
                'days_ago': 골든크로스 발생 일수 (최근 5일 이내)
            }
        """
        if df is None or len(df) < 60:
            return {'is_golden_cross': False}

        # 이동평균선이 이미 계산되어 있는지 확인
        if 'MA20' not in df.columns or 'MA60' not in df.columns:
            df = df.copy()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()

        # 최근 5일 이내 골든크로스 확인
        for i in range(1, min(6, len(df))):
            prev_idx = -i - 1
            curr_idx = -i

            if pd.isna(df['MA20'].iloc[prev_idx]) or pd.isna(df['MA60'].iloc[prev_idx]):
                continue

            # 이전에는 MA20 < MA60, 현재는 MA20 > MA60
            if (df['MA20'].iloc[prev_idx] < df['MA60'].iloc[prev_idx] and
                df['MA20'].iloc[curr_idx] > df['MA60'].iloc[curr_idx]):
                return {
                    'is_golden_cross': True,
                    'ma_short': df['MA20'].iloc[-1],
                    'ma_long': df['MA60'].iloc[-1],
                    'days_ago': i
                }

        # 현재 골든크로스 상태인지 확인
        is_current_gc = (df['MA20'].iloc[-1] > df['MA60'].iloc[-1])

        return {
            'is_golden_cross': False,
            'ma_short': df['MA20'].iloc[-1],
            'ma_long': df['MA60'].iloc[-1],
            'is_currently_above': is_current_gc
        }

    def calculate_stop_loss_price(self, buy_price: float) -> float:
        """
        손절가를 계산합니다.

        Args:
            buy_price: 매수 가격

        Returns:
            손절 가격
        """
        return buy_price * (1 - self.stop_loss_pct)

    def analyze_buy_signals(
        self,
        df: pd.DataFrame,
        market_trend: str = 'UNKNOWN'
    ) -> Dict[str, any]:
        """
        종합적인 매수 신호를 분석합니다.

        Args:
            df: 주가 데이터 DataFrame
            market_trend: 시장 추세 ('BULL', 'BEAR', 'SIDEWAYS', 'UNKNOWN')

        Returns:
            {
                'knee_status': 무릎 위치 정보,
                'rsi': RSI 값,
                'is_rsi_oversold': RSI 과매도 여부,
                'volume_surge': 거래량 급증 여부,
                'golden_cross': 골든크로스 정보,
                'chase_buy_safe': 추격매수 안전 여부,
                'stop_loss_price': 권장 손절가,
                'buy_signals': 매수 신호 목록,
                'buy_score': 매수 점수 (0-100),
                'market_trend': 시장 추세,
                'market_adjusted_score': 시장 필터 적용 후 점수
            }
        """
        if df is None or df.empty:
            return {}

        result = {}

        # 1. 무릎 위치 확인
        knee_status = self.price_detector.is_at_knee(df, self.knee_threshold)
        result['knee_status'] = knee_status

        # 2. RSI 확인
        rsi_series = self.calculate_rsi(df)
        current_rsi = rsi_series.iloc[-1] if not rsi_series.empty else None
        result['rsi'] = current_rsi
        result['is_rsi_oversold'] = current_rsi < self.rsi_oversold if current_rsi else False

        # 3. 거래량 확인
        result['volume_surge'] = self.check_volume_surge(df)

        # 4. 골든크로스 확인
        result['golden_cross'] = self.check_golden_cross(df)

        # 5. 추격매수 안전성 확인
        metrics = self.price_detector.calculate_position_metrics(df)
        from_floor_pct = metrics.get('from_floor_pct', 0)
        result['chase_buy_safe'] = from_floor_pct < self.chase_risk_threshold

        # 6. 손절가 계산
        current_price = df['Close'].iloc[-1]
        result['stop_loss_price'] = self.calculate_stop_loss_price(current_price)

        # 7. 매수 신호 목록
        buy_signals = []
        if knee_status.get('is_at_knee'):
            buy_signals.append("무릎 위치 도달")
        if result['is_rsi_oversold']:
            buy_signals.append("RSI 과매도")
        if result['volume_surge']:
            buy_signals.append("거래량 급증")
        if result['golden_cross'].get('is_golden_cross'):
            days = result['golden_cross'].get('days_ago', 0)
            buy_signals.append(f"골든크로스 ({days}일 전)")

        result['buy_signals'] = buy_signals

        # 8. 매수 점수 계산 (0-100)
        score = 0
        if knee_status.get('is_at_knee'):
            score += 30
        if result['is_rsi_oversold']:
            score += 25
        if result['volume_surge']:
            score += 20
        if result['golden_cross'].get('is_golden_cross'):
            score += 25

        result['buy_score'] = min(score, 100)

        # 9. 시장 필터 적용
        result['market_trend'] = market_trend
        market_adjusted_score = score

        if market_trend == 'BEAR':
            # 하락장에서는 강력 매수 신호(80점 이상)가 아니면 감점
            if score < 80:
                market_adjusted_score = score * 0.5  # 50% 감점
                if "⚠️ 시장 하락장" not in buy_signals:
                    buy_signals.append("⚠️ 시장 하락장")
        elif market_trend == 'BULL':
            # 상승장에서는 가산점
            market_adjusted_score = score * 1.1  # 10% 가산점
            if "📈 시장 상승장" not in buy_signals:
                buy_signals.append("📈 시장 상승장")
        elif market_trend == 'SIDEWAYS':
            # 횡보장은 점수 유지
            if "➡️ 시장 횡보장" not in buy_signals:
                buy_signals.append("➡️ 시장 횡보장")

        result['market_adjusted_score'] = min(market_adjusted_score, 100)
        result['buy_signals'] = buy_signals  # 시장 필터 메시지 반영

        return result

    def get_buy_recommendation(self, analysis: Dict) -> str:
        """
        매수 분석 결과를 바탕으로 추천 메시지를 생성합니다.

        Args:
            analysis: analyze_buy_signals() 결과

        Returns:
            추천 메시지
        """
        if not analysis:
            return "분석 불가"

        # 시장 조정 점수를 우선 사용, 없으면 기본 점수 사용
        score = analysis.get('market_adjusted_score', analysis.get('buy_score', 0))
        signals = analysis.get('buy_signals', [])
        chase_safe = analysis.get('chase_buy_safe', False)

        if score >= 70:
            recommendation = "🟢 강력 매수"
        elif score >= 50:
            recommendation = "🟡 매수 고려"
        elif score >= 30:
            recommendation = "🟠 관망"
        else:
            recommendation = "⚪ 매수 부적합"

        if not chase_safe:
            recommendation += " (⚠️ 추격매수 주의)"

        if signals:
            recommendation += f" - {', '.join(signals)}"

        return recommendation
