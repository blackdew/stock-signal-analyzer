"""매도 신호 분석 모듈"""
import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Optional
from .price_levels import PriceLevelDetector
from src.utils.logger import setup_logger
from src.utils.helpers import safe_divide, safe_percentage, is_valid_number

# 로거 설정
logger = setup_logger(__name__)


class SellSignalAnalyzer:
    """매도 신호를 분석하는 클래스"""

    def __init__(
        self,
        shoulder_threshold: float = 0.15,
        profit_target_full: float = 0.30,
        profit_target_partial: float = 0.15,
        rsi_period: int = 14,
        rsi_overbought: int = 70,
        stop_loss_pct: float = 0.07
    ):
        """
        Args:
            shoulder_threshold: 어깨 판단 기준 (천장 대비 하락률)
            profit_target_full: 전량 매도 권장 수익률
            profit_target_partial: 분할 매도 권장 수익률
            rsi_period: RSI 계산 기간
            rsi_overbought: RSI 과매수 기준
            stop_loss_pct: 손절 기준 (매수가 대비 하락률, 기본 7%)
        """
        self.shoulder_threshold = shoulder_threshold
        self.profit_target_full = profit_target_full
        self.profit_target_partial = profit_target_partial
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.stop_loss_pct = stop_loss_pct
        self.price_detector = PriceLevelDetector()

    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """RSI를 계산합니다."""
        if df is None or df.empty:
            return pd.Series()

        rsi = ta.rsi(df['Close'], length=self.rsi_period)
        return rsi

    def check_volume_decrease(self, df: pd.DataFrame, threshold: float = 0.7) -> bool:
        """
        거래량 감소 여부를 확인합니다.

        Args:
            df: 주가 데이터 DataFrame
            threshold: 평균 대비 비율 (0.7 = 30% 감소)

        Returns:
            True if 거래량 감소
        """
        if df is None or len(df) < 20:
            return False

        current_volume = df['Volume'].iloc[-1]
        avg_volume = df['Volume'].tail(20).mean()

        return current_volume <= avg_volume * threshold

    def check_dead_cross(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        데드크로스 발생 여부를 확인합니다.

        Returns:
            {
                'is_dead_cross': True/False,
                'ma_short': 단기 이동평균,
                'ma_long': 장기 이동평균,
                'days_ago': 데드크로스 발생 일수 (최근 5일 이내)
            }
        """
        if df is None or len(df) < 60:
            return {'is_dead_cross': False}

        # 이동평균선이 이미 계산되어 있는지 확인
        if 'MA20' not in df.columns or 'MA60' not in df.columns:
            df = df.copy()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()

        # 최근 5일 이내 데드크로스 확인
        for i in range(1, min(6, len(df))):
            prev_idx = -i - 1
            curr_idx = -i

            if pd.isna(df['MA20'].iloc[prev_idx]) or pd.isna(df['MA60'].iloc[prev_idx]):
                continue

            # 이전에는 MA20 > MA60, 현재는 MA20 < MA60
            if (df['MA20'].iloc[prev_idx] > df['MA60'].iloc[prev_idx] and
                df['MA20'].iloc[curr_idx] < df['MA60'].iloc[curr_idx]):
                return {
                    'is_dead_cross': True,
                    'ma_short': df['MA20'].iloc[-1],
                    'ma_long': df['MA60'].iloc[-1],
                    'days_ago': i
                }

        # 현재 데드크로스 상태인지 확인
        is_current_dc = (df['MA20'].iloc[-1] < df['MA60'].iloc[-1])

        return {
            'is_dead_cross': False,
            'ma_short': df['MA20'].iloc[-1],
            'ma_long': df['MA60'].iloc[-1],
            'is_currently_below': is_current_dc
        }

    def calculate_profit_rate(
        self,
        current_price: float,
        buy_price: Optional[float]
    ) -> Optional[float]:
        """
        안전한 수익률 계산

        Args:
            current_price: 현재 가격
            buy_price: 매수 가격 (None이면 계산 불가)

        Returns:
            수익률 (소수)
        """
        try:
            if buy_price is None or buy_price <= 0:
                logger.debug("수익률 계산 불가: 매수가 정보 없음")
                return None

            if not is_valid_number(current_price) or not is_valid_number(buy_price):
                logger.warning("수익률 계산 불가: 유효하지 않은 가격 정보")
                return None

            profit_rate = safe_percentage(current_price, buy_price, default=None)
            logger.debug(f"수익률 계산: {profit_rate*100:.2f}% (매수가: {buy_price:,.0f}, 현재가: {current_price:,.0f})")
            return profit_rate

        except Exception as e:
            logger.error(f"수익률 계산 중 오류: {str(e)}")
            return None

    def recommend_sell_strategy(
        self,
        profit_rate: Optional[float],
        volatility: float = 0.0
    ) -> str:
        """
        수익률과 변동성을 기반으로 매도 전략을 추천합니다.

        Args:
            profit_rate: 수익률 (소수)
            volatility: 변동성 (0~1, 높을수록 변동성 높음)

        Returns:
            '전량매도' 또는 '분할매도' 또는 '보유'
        """
        if profit_rate is None:
            return "정보부족"

        # 수익률이 높고 변동성이 높으면 전량 매도
        if profit_rate >= self.profit_target_full:
            return "전량매도"
        elif profit_rate >= self.profit_target_partial:
            # 변동성이 높으면 분할 매도, 낮으면 일부만 매도
            if volatility > 0.5:
                return "분할매도 (1/2)"
            else:
                return "분할매도 (1/3)"
        else:
            return "보유"

    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        최근 기간의 변동성을 계산합니다.

        Args:
            df: 주가 데이터 DataFrame
            period: 계산 기간

        Returns:
            변동성 (0~1, 표준편차 기반 정규화)
        """
        if df is None or len(df) < period:
            return 0.0

        recent_data = df.tail(period)
        returns = recent_data['Close'].pct_change().dropna()

        if len(returns) == 0:
            return 0.0

        # 표준편차 계산
        std_dev = returns.std()

        # 정규화 (일반적으로 0.02~0.05 범위)
        # 0.05 이상이면 1.0으로 간주
        normalized = min(std_dev / 0.05, 1.0)

        return normalized

    def calculate_trailing_stop(
        self,
        buy_price: float,
        current_price: float,
        highest_price: Optional[float] = None,
        trailing_pct: float = 0.10
    ) -> Dict[str, any]:
        """
        추적 손절가를 계산합니다.

        Args:
            buy_price: 매수 가격
            current_price: 현재 가격
            highest_price: 보유 기간 중 최고가 (None이면 현재가 사용)
            trailing_pct: 추적 비율 (기본 10%)

        Returns:
            {
                'trailing_stop_price': 추적 손절가,
                'is_trailing': 추적 손절 활성화 여부,
                'stop_type': 손절 타입 ('TRAILING' 또는 'FIXED'),
                'trailing_triggered': 추적 손절 트리거 여부,
                'trailing_message': 추적 손절 메시지
            }
        """
        if buy_price is None or buy_price <= 0:
            return {
                'trailing_stop_price': None,
                'is_trailing': False,
                'stop_type': 'NONE',
                'trailing_triggered': False,
                'trailing_message': None
            }

        # 최고가가 없으면 현재가를 최고가로 사용
        if highest_price is None:
            highest_price = current_price

        # 수익률 계산
        profit_rate = (highest_price - buy_price) / buy_price

        # 기본 손절가 (매수가 대비 -7%)
        base_stop_loss = buy_price * (1 - self.stop_loss_pct)

        if profit_rate > 0:
            # 수익 중: 최고가 대비 trailing_pct 하락 시 손절
            trailing_stop = highest_price * (1 - trailing_pct)

            # 기본 손절가보다 높으면 추적 손절가 사용
            final_stop = max(trailing_stop, base_stop_loss)

            # 현재가가 추적 손절가 아래로 떨어졌는지 확인
            trailing_triggered = current_price <= trailing_stop

            # 손실률 계산 (최고가 대비)
            loss_from_high = (current_price - highest_price) / highest_price

            return {
                'trailing_stop_price': final_stop,
                'is_trailing': True,
                'stop_type': 'TRAILING',
                'trailing_triggered': trailing_triggered,
                'trailing_message': f"🔻 추적 손절 발동 (최고가 대비 {loss_from_high*100:.1f}%)" if trailing_triggered else None,
                'highest_price': highest_price,
                'loss_from_high': loss_from_high
            }
        else:
            # 손실 중: 기본 손절가만 사용
            return {
                'trailing_stop_price': base_stop_loss,
                'is_trailing': False,
                'stop_type': 'FIXED',
                'trailing_triggered': False,
                'trailing_message': None
            }

    def analyze_sell_signals(
        self,
        df: pd.DataFrame,
        buy_price: Optional[float] = None,
        market_trend: str = 'UNKNOWN',
        highest_price: Optional[float] = None
    ) -> Dict[str, any]:
        """
        종합적인 매도 신호를 분석합니다.

        Args:
            df: 주가 데이터 DataFrame
            buy_price: 매수 가격 (수익률 계산용, 선택사항)
            market_trend: 시장 추세 ('BULL', 'BEAR', 'SIDEWAYS', 'UNKNOWN')
            highest_price: 보유 기간 중 최고가 (추적 손절 계산용, 선택사항)

        Returns:
            {
                'shoulder_status': 어깨 위치 정보,
                'rsi': RSI 값,
                'is_rsi_overbought': RSI 과매수 여부,
                'volume_decrease': 거래량 감소 여부,
                'dead_cross': 데드크로스 정보,
                'profit_rate': 수익률 (buy_price가 있을 경우),
                'loss_rate': 손실률 (buy_price가 있을 경우),
                'volatility': 변동성,
                'sell_strategy': 매도 전략 추천,
                'sell_signals': 매도 신호 목록,
                'sell_score': 매도 점수 (0-100),
                'market_trend': 시장 추세,
                'market_adjusted_score': 시장 필터 적용 후 점수,
                'stop_loss_triggered': 손절 발동 여부,
                'stop_loss_message': 손절 메시지,
                'stop_loss_price': 손절가,
                'trailing_stop': 추적 손절 정보
            }
        """
        if df is None or df.empty:
            return {}

        result = {}
        current_price = df['Close'].iloc[-1]

        # 1. 손절 로직 (최우선 체크)
        result['stop_loss_triggered'] = False
        result['stop_loss_message'] = None
        result['stop_loss_price'] = None
        result['loss_rate'] = None

        # 기본 손절 체크
        if buy_price is not None and buy_price > 0:
            loss_rate = (current_price - buy_price) / buy_price
            result['loss_rate'] = loss_rate
            result['stop_loss_price'] = buy_price * (1 - self.stop_loss_pct)

            # 손절가 도달 (기본 -7%)
            if loss_rate <= -self.stop_loss_pct:
                result['stop_loss_triggered'] = True
                result['stop_loss_message'] = f"🚨 손절 발동 ({loss_rate*100:.1f}%)"

        # 2. 추적 손절 (Trailing Stop) 체크
        trailing_stop_info = self.calculate_trailing_stop(
            buy_price=buy_price,
            current_price=current_price,
            highest_price=highest_price
        )
        result['trailing_stop'] = trailing_stop_info

        # 추적 손절이 트리거되면 손절 발동으로 처리
        if trailing_stop_info.get('trailing_triggered'):
            result['stop_loss_triggered'] = True
            result['stop_loss_message'] = trailing_stop_info.get('trailing_message')

        # 3. 어깨 위치 확인
        shoulder_status = self.price_detector.is_at_shoulder(df, self.shoulder_threshold)
        result['shoulder_status'] = shoulder_status

        # 4. RSI 확인
        rsi_series = self.calculate_rsi(df)
        current_rsi = rsi_series.iloc[-1] if not rsi_series.empty else None
        result['rsi'] = current_rsi
        result['is_rsi_overbought'] = current_rsi > self.rsi_overbought if current_rsi else False

        # 5. 거래량 확인
        result['volume_decrease'] = self.check_volume_decrease(df)

        # 6. 데드크로스 확인
        result['dead_cross'] = self.check_dead_cross(df)

        # 7. 수익률 계산
        profit_rate = self.calculate_profit_rate(current_price, buy_price)
        result['profit_rate'] = profit_rate

        # 8. 변동성 계산
        volatility = self.calculate_volatility(df)
        result['volatility'] = volatility

        # 9. 매도 전략 추천
        result['sell_strategy'] = self.recommend_sell_strategy(profit_rate, volatility)

        # 10. 매도 신호 목록
        sell_signals = []

        # 손절 신호가 있으면 맨 앞에 추가 (기본 손절 또는 추적 손절)
        if result['stop_loss_triggered']:
            sell_signals.append(result['stop_loss_message'])

        if shoulder_status.get('is_at_shoulder'):
            sell_signals.append("어깨 위치 도달")
        if result['is_rsi_overbought']:
            sell_signals.append("RSI 과매수")
        if result['volume_decrease']:
            sell_signals.append("거래량 감소")
        if result['dead_cross'].get('is_dead_cross'):
            days = result['dead_cross'].get('days_ago', 0)
            sell_signals.append(f"데드크로스 ({days}일 전)")

        result['sell_signals'] = sell_signals

        # 11. 매도 점수 계산 (0-100)
        score = 0

        # 손절 발동 시 최고 우선순위 (100점)
        if result['stop_loss_triggered']:
            score = 100
        else:
            if shoulder_status.get('is_at_shoulder'):
                score += 30
            if result['is_rsi_overbought']:
                score += 25
            if result['volume_decrease']:
                score += 20
            if result['dead_cross'].get('is_dead_cross'):
                score += 25

        result['sell_score'] = min(score, 100)

        # 12. 시장 필터 적용
        result['market_trend'] = market_trend
        market_adjusted_score = score

        if market_trend == 'BULL':
            # 상승장에서는 강력 매도 신호(80점 이상)가 아니면 감점
            if score < 80:
                market_adjusted_score = score * 0.7  # 30% 감점
                if "📈 시장 상승장 (보유 유리)" not in sell_signals:
                    sell_signals.append("📈 시장 상승장 (보유 유리)")
        elif market_trend == 'BEAR':
            # 하락장에서는 매도 신호 강화
            market_adjusted_score = score * 1.2  # 20% 가산점
            if "⚠️ 시장 하락장 (매도 고려)" not in sell_signals:
                sell_signals.append("⚠️ 시장 하락장 (매도 고려)")
        elif market_trend == 'SIDEWAYS':
            # 횡보장은 점수 유지
            if "➡️ 시장 횡보장" not in sell_signals:
                sell_signals.append("➡️ 시장 횡보장")

        result['market_adjusted_score'] = min(market_adjusted_score, 100)
        result['sell_signals'] = sell_signals  # 시장 필터 메시지 반영

        return result

    def get_sell_recommendation(self, analysis: Dict) -> str:
        """
        매도 분석 결과를 바탕으로 추천 메시지를 생성합니다.

        Args:
            analysis: analyze_sell_signals() 결과

        Returns:
            추천 메시지
        """
        if not analysis:
            return "분석 불가"

        # 손절 트리거 시 최우선 표시
        if analysis.get('stop_loss_triggered'):
            loss_rate = analysis.get('loss_rate', 0)
            recommendation = f"🚨 즉시 손절 필요 (손실률: {loss_rate*100:.1f}%)"
            return recommendation

        # 시장 조정 점수를 우선 사용, 없으면 기본 점수 사용
        score = analysis.get('market_adjusted_score', analysis.get('sell_score', 0))
        signals = analysis.get('sell_signals', [])
        strategy = analysis.get('sell_strategy', '보유')
        profit_rate = analysis.get('profit_rate')

        if score >= 70:
            recommendation = "🔴 강력 매도"
        elif score >= 50:
            recommendation = "🟠 매도 고려"
        elif score >= 30:
            recommendation = "🟡 관망"
        else:
            recommendation = "🟢 보유"

        recommendation += f" ({strategy})"

        if profit_rate is not None:
            recommendation += f" [수익률: {profit_rate*100:+.1f}%]"

        if signals:
            recommendation += f" - {', '.join(signals)}"

        return recommendation
